#!/usr/bin/env python3
"""
slam_prereq_checker.py
======================
Verifica que todos los topics críticos para EKF + SLAM estén publicando
con timestamps sincronizados al sim_time de Gazebo.

Lógica:
  Para cada topic crítico comprueba:
    |msg.header.stamp - /clock| < MAX_DRIFT_SEC

  Cuando TODOS pasan → imprime resumen verde y sale con exit(0)
  Si alguno falla tras TIMEOUT_SEC → imprime tabla de errores y sale exit(1)

Uso en launch (opcional, antes de EKF y SLAM):
    slam_prereq_checker = Node(
        package='bobert_sim',
        executable='slam_prereq_checker',
        name='slam_prereq_checker',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )
"""

import rclpy
import sys
import time
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile, QoSReliabilityPolicy,
    QoSDurabilityPolicy, QoSHistoryPolicy
)
from builtin_interfaces.msg import Time as TimeMsg
from sensor_msgs.msg import LaserScan, Imu
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from rosgraph_msgs.msg import Clock

# ─────────────────────────────────────────────────────────────
# Configuración — ajusta si cambias topic names
# ─────────────────────────────────────────────────────────────
TOPICS = {
    '/scan':  LaserScan,
    '/imu': Imu,
#    '/bobert_base_controller/odom': Odometry,       # publica diff_drive_controller
    '/odometry/filtered': Odometry,
    '/tf':    TFMessage,
}

MAX_DRIFT_SEC  = 0.5    # desfase máximo permitido entre stamp y sim_time
TIMEOUT_SEC    = 60.0   # tiempo máximo esperando que todos pasen
CHECK_RATE_HZ  = 2.0    # frecuencia del loop de comprobación

# QoS permisivo — acepta tanto RELIABLE/TRANSIENT como BEST_EFFORT/VOLATILE
BEST_EFFORT_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    durability=QoSDurabilityPolicy.VOLATILE,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
)
# ─────────────────────────────────────────────────────────────


def stamp_to_sec(stamp) -> float:
    return stamp.sec + stamp.nanosec * 1e-9


class SlamPrereqChecker(Node):
    def __init__(self):
        super().__init__('slam_prereq_checker')
        
        # 1. Escudo contra el error de parámetro ya declarado
        if not self.has_parameter('use_sim_time'):
            self.declare_parameter('use_sim_time', True)

        self._sim_time_sec: float = 0.0
        self._clock_received: bool = False

        # Estado por topic: None = no recibido, float = último stamp en seg
        self._last_stamp: dict = {t: None for t in TOPICS}
        self._pass:       dict = {t: False for t in TOPICS}

        # Suscripción al reloj de simulación
        self.create_subscription(
            Clock, '/clock', self._cb_clock, BEST_EFFORT_QOS)

        # Suscripciones dinámicas para cada topic crítico
        for topic, msg_type in TOPICS.items():
            self.create_subscription(
                msg_type,
                topic,
                lambda msg, t=topic: self._cb_topic(msg, t),
                BEST_EFFORT_QOS,
            )

        self._start_wall = time.monotonic()
        self._timer = self.create_timer(1.0 / CHECK_RATE_HZ, self._check)

        self.get_logger().info(
            f'[prereq] Esperando {len(TOPICS)} topics críticos para Bobert '
            f'(drift < {MAX_DRIFT_SEC}s, timeout {TIMEOUT_SEC}s)...'
        )

    # ── Callbacks ────────────────────────────────────────────

    def _cb_clock(self, msg: Clock):
        # Actualizamos el tiempo de simulación desde el tópico /clock
        self._sim_time_sec = stamp_to_sec(msg.clock)
        self._clock_received = True

    def _cb_topic(self, msg, topic: str):
        """Extrae el stamp de cualquier tipo de mensaje."""
        if hasattr(msg, 'header'):
            self._last_stamp[topic] = stamp_to_sec(msg.header.stamp)
        elif topic == '/tf' and hasattr(msg, 'transforms') and msg.transforms:
            # En TF, usamos el stamp de la primera transformación de la lista
            self._last_stamp[topic] = stamp_to_sec(
                msg.transforms[0].header.stamp)

    # ── Loop de verificación ─────────────────────────────────

    def _check(self):
        # 2. Usamos el reloj oficial del nodo (sincronizado con use_sim_time)
        # Esto es más preciso que leer solo el mensaje de /clock
        current_ros_time = self.get_clock().now().nanoseconds / 1e9

        if not self._clock_received:
            self.get_logger().warn('[prereq] /clock aún no recibido...')
            return

        elapsed = time.monotonic() - self._start_wall
        all_ok  = True

        for topic in TOPICS:
            stamp = self._last_stamp[topic]
            if stamp is None:
                all_ok = False
                continue

            # 3. Comparamos el stamp del sensor contra el tiempo actual del sistema ROS
            drift = abs(stamp - current_ros_time)
            
            if drift <= MAX_DRIFT_SEC:
                if not self._pass[topic]:
                    self.get_logger().info(
                        f'[prereq] ✓  {topic:30s}  '
                        f'stamp={stamp:.2f}s  drift={drift*1000:.1f}ms'
                    )
                self._pass[topic] = True
            else:
                all_ok = False
                self.get_logger().warn(
                    f'[prereq] ✗  {topic:30s}  '
                    f'stamp={stamp:.2f}s  sim_now={current_ros_time:.2f}s  '
                    f'drift={drift:.2f}s  > {MAX_DRIFT_SEC}s  ← DESFASE'
                )

        if all_ok:
            self._success()
        elif elapsed > TIMEOUT_SEC:
            self._fail()
    # ── Salida ───────────────────────────────────────────────

    def _success(self):
        self.get_logger().info(
            '\n'
            '══════════════════════════════════════════════════\n'
            '  ✓  TODOS LOS TOPICS SINCRONIZADOS CON SIM_TIME\n'
            '     EKF + SLAM pueden arrancar de forma segura.\n'
            '══════════════════════════════════════════════════'
        )
        self._print_table()
        rclpy.shutdown()
        sys.exit(0)

    def _fail(self):
        self.get_logger().error(
            '\n'
            '══════════════════════════════════════════════════\n'
            '  ✗  TIMEOUT: algún topic no está sincronizado.\n'
            '     Revisa los plugins de Gazebo / use_sim_time.\n'
            '══════════════════════════════════════════════════'
        )
        self._print_table()
        rclpy.shutdown()
        sys.exit(1)

    def _print_table(self):
        self.get_logger().info(
            '[prereq] Resumen final:\n'
            f"  {'Topic':<35} {'Stamp (s)':>12}  {'sim_time (s)':>12}  {'Estado'}\n"
            + '  ' + '─' * 70
        )
        for topic in TOPICS:
            stamp  = self._last_stamp[topic]
            status = '✓ OK' if self._pass[topic] else '✗ FALLO'
            stamp_str = f'{stamp:.3f}' if stamp is not None else 'no recibido'
            self.get_logger().info(
                f'  {topic:<35} {stamp_str:>12}  '
                f'{self._sim_time_sec:>12.3f}  {status}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = SlamPrereqChecker()
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        node.get_logger().info('[prereq] Interrumpido por usuario.')


if __name__ == '__main__':
    main()
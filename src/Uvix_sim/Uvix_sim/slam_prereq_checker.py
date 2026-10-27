#!/usr/bin/env python3
"""
Sale con 0 cuando /scan, /imu, /odometry/filtered y /tf publican sincronizados
con el sim_time; con 1 tras timeout.
"""

import rclpy
import sys
import time
from rclpy.clock import Clock as RosClock, ClockType
from rclpy.executors import ExternalShutdownException
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

TOPICS = {
    '/scan':  LaserScan,
    '/imu': Imu,
    '/odometry/filtered': Odometry,
    '/tf':    TFMessage,
}

MAX_DRIFT_SEC  = 0.5
TIMEOUT_SEC    = 60.0
CHECK_RATE_HZ  = 2.0

BEST_EFFORT_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    durability=QoSDurabilityPolicy.VOLATILE,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
)


def stamp_to_sec(stamp) -> float:
    return stamp.sec + stamp.nanosec * 1e-9


class SlamPrereqChecker(Node):
    def __init__(self):
        super().__init__('slam_prereq_checker')

        if not self.has_parameter('use_sim_time'):
            self.declare_parameter('use_sim_time', True)
        self._timeout = self.declare_parameter('timeout', TIMEOUT_SEC).value

        self._sim_time_sec: float = 0.0
        self._clock_received: bool = False

        self._last_stamp: dict = {t: None for t in TOPICS}
        self._pass:       dict = {t: False for t in TOPICS}

        self.create_subscription(
            Clock, '/clock', self._cb_clock, BEST_EFFORT_QOS)

        for topic, msg_type in TOPICS.items():
            self.create_subscription(
                msg_type,
                topic,
                lambda msg, t=topic: self._cb_topic(msg, t),
                BEST_EFFORT_QOS,
            )

        self._start_wall = time.monotonic()
        self._timer = self.create_timer(1.0 / CHECK_RATE_HZ, self._check,
                                        clock=RosClock(clock_type=ClockType.STEADY_TIME))

        self.get_logger().info(
            f'[prereq] Esperando {len(TOPICS)} topics críticos '
            f'(drift < {MAX_DRIFT_SEC}s, timeout {self._timeout}s)...'
        )


    def _cb_clock(self, msg: Clock):
        self._sim_time_sec = stamp_to_sec(msg.clock)
        self._clock_received = True

    def _cb_topic(self, msg, topic: str):
        """Extrae el stamp de cualquier tipo de mensaje."""
        if hasattr(msg, 'header'):
            self._last_stamp[topic] = stamp_to_sec(msg.header.stamp)
        elif topic == '/tf' and hasattr(msg, 'transforms') and msg.transforms:
            self._last_stamp[topic] = stamp_to_sec(
                msg.transforms[0].header.stamp)


    def _check(self):
        current_ros_time = self.get_clock().now().nanoseconds / 1e9

        elapsed = time.monotonic() - self._start_wall

        if not self._clock_received:
            if elapsed > self._timeout:
                self._fail()
            self.get_logger().warn('[prereq] /clock aún no recibido...',
                                   throttle_duration_sec=5.0)
            return
        all_ok  = True

        for topic in TOPICS:
            stamp = self._last_stamp[topic]
            if stamp is None:
                all_ok = False
                continue

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
        elif elapsed > self._timeout:
            self._fail()

    def _success(self):
        self.get_logger().info(
            '\n'
            '══════════════════════════════════════════════════\n'
            '  ✓  TODOS LOS TOPICS SINCRONIZADOS CON SIM_TIME\n'
            '     EKF + SLAM pueden arrancar de forma segura.\n'
            '══════════════════════════════════════════════════'
        )
        self._print_table()
        raise SystemExit(0)

    def _fail(self):
        self.get_logger().error(
            '\n'
            '══════════════════════════════════════════════════\n'
            '  ✗  TIMEOUT: algún topic no está sincronizado.\n'
            '     Revisa los plugins de Gazebo / use_sim_time.\n'
            '══════════════════════════════════════════════════'
        )
        self._print_table()
        raise SystemExit(1)

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
    code = 1
    try:
        rclpy.spin(node)
    except SystemExit as e:
        code = e.code
    except (KeyboardInterrupt, ExternalShutdownException):
        node.get_logger().info('[prereq] Interrumpido.')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(code)


if __name__ == '__main__':
    main()

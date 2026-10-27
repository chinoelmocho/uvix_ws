#!/usr/bin/env python3
"""
Sale con 0 cuando Gazebo publica /clock (QoS BEST_EFFORT), con 1 tras timeout.
"""

import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from rosgraph_msgs.msg import Clock


GAZEBO_CLOCK_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class GazeboReadyWatcher(Node):
    """
    Detecta que Gazebo está corriendo y el tiempo simulado es válido.

    Condición de éxito:
      - /clock publica mensajes con QoS BEST_EFFORT  (Gazebo arrancó)
      - sim_time.sec > min_sim_time_sec              (mundo terminó de cargar)

    Termina con exit(0) → OnProcessExit dispara el spawn.
    Termina con exit(1) → timeout, Gazebo no levantó.
    """

    def __init__(self):
        super().__init__('gazebo_ready_watcher')

        self.declare_parameter('timeout', 300.0)
        self.declare_parameter('min_sim_time_sec', 0)

        self._timeout     = self.get_parameter('timeout').value
        self._min_sim_sec = self.get_parameter('min_sim_time_sec').value
        self._ready       = False
        self._wall_start  = time.time()
        self._clock_count = 0

        self._sub = self.create_subscription(
            Clock,
            '/clock',
            self._clock_cb,
            qos_profile=GAZEBO_CLOCK_QOS,
        )

        self._guard = self.create_timer(2.0, self._check_timeout)

        self.get_logger().info(
            f'Watcher v2 activo (QoS=BEST_EFFORT). '
            f'Esperando /clock con sim_time > {self._min_sim_sec}s '
            f'(timeout={self._timeout}s)...'
        )


    def _clock_cb(self, msg: Clock):
        if self._ready:
            return

        self._clock_count += 1
        sim_sec = msg.clock.sec

        if self._clock_count % 30 == 1:
            elapsed = time.time() - self._wall_start
            self.get_logger().info(
                f'  /clock OK ({self._clock_count} msgs) — '
                f'sim_time={sim_sec}s — wall={elapsed:.1f}s'
            )

        if sim_sec > self._min_sim_sec:
            self._ready = True
            elapsed = time.time() - self._wall_start
            self.get_logger().info(
                f'Gazebo listo en {elapsed:.1f}s '
                f'(sim_time={sim_sec}s). Disparando spawn...'
            )
            sys.exit(0)


    def _check_timeout(self):
        if self._ready:
            return
        elapsed = time.time() - self._wall_start
        if elapsed > self._timeout:
            self.get_logger().error(
                f'TIMEOUT ({self._timeout}s): Gazebo no publicó /clock. '
                f'Mensajes recibidos: {self._clock_count}. '
                f'Revisa que gzserver levantó correctamente.'
            )
            sys.exit(1)


def main(args=None):
    rclpy.init(args=args)
    node = GazeboReadyWatcher()
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()

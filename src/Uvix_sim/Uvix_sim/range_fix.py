#!/usr/bin/env python3
"""
Corrige los ultrasonidos para Nav2: /ultrasonic/<s> → /ultrasonic_nav/<s>.

Gazebo publica FLT_MAX cuando no detecta nada; rclpy no puede deserializarlo,
así que el mensaje se lee en crudo (CDR) y la lectura se acota a [min_range, max_range].
"""

import math
import struct

import rclpy
from builtin_interfaces.msg import Time
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Range


def parse_range_cdr(raw):
    """Decodifica un sensor_msgs/Range serializado (CDR) sin pasar por rclpy.

    Devuelve (sec, nanosec, frame_id, radiation_type, fov, min_range, max_range, range).
    """
    e = '<' if raw[1] & 0x01 else '>'
    b = memoryview(raw)[4:]
    sec, nsec, slen = struct.unpack_from(e + 'iII', b, 0)
    off = 12
    frame_id = bytes(b[off:off + max(0, slen - 1)]).decode('utf-8', 'replace')
    off += slen
    radiation = b[off]
    off = (off + 1 + 3) & ~3
    fov, rmin, rmax, rng = struct.unpack_from(e + 'ffff', b, off)
    return sec, nsec, frame_id, radiation, fov, rmin, rmax, rng


def fix_range(rng, rmin, rmax):
    if math.isnan(rng) or rng > rmax:
        return rmax
    if rng < rmin:
        return rmin
    return rng


class RangeFix(Node):

    def __init__(self):
        super().__init__('range_fix')
        self.declare_parameter('sensors', ['front_left', 'front_right', 'rear_left', 'rear_right'])
        self.declare_parameter('input_prefix', '/ultrasonic/')
        self.declare_parameter('output_prefix', '/ultrasonic_nav/')

        sensors = self.get_parameter('sensors').value
        inp = self.get_parameter('input_prefix').value
        out = self.get_parameter('output_prefix').value

        self._bad = 0
        self._subs = []
        for s in sensors:
            pub = self.create_publisher(Range, out + s, qos_profile_sensor_data)
            self._subs.append(self.create_subscription(
                Range, inp + s, lambda raw, pub=pub: self._on_raw(raw, pub),
                qos_profile_sensor_data, raw=True))
        self.get_logger().info(
            f'Corrigiendo {len(sensors)} ultrasonidos: {inp}* → {out}*')

    def _on_raw(self, raw, pub):
        try:
            sec, nsec, frame_id, radiation, fov, rmin, rmax, rng = parse_range_cdr(raw)
        except (struct.error, IndexError):
            self._bad += 1
            if self._bad in (1, 100, 1000):
                self.get_logger().warn(f'{self._bad} mensaje(s) Range ilegibles descartados')
            return
        msg = Range()
        msg.header.stamp = Time(sec=sec, nanosec=nsec)
        msg.header.frame_id = frame_id
        msg.radiation_type = radiation
        msg.field_of_view = fov
        msg.min_range = rmin
        msg.max_range = rmax
        msg.range = fix_range(rng, rmin, rmax)
        pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = RangeFix()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

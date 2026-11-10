#!/usr/bin/env python3
"""
Amplía un mapa de slam_toolbox punto por punto.

Para cada punto del CSV (punto,x_m,y_m,yaw_rad en frame map):
  teletransporta el robot en Gazebo → carga el grafo en esa pose
  (START_AT_GIVEN_POSE) → gira una vuelta completa → guarda el grafo y el mapa.

El mapa base nunca se escribe: todo se guarda en output_map.
Lo lanza slam_extend_launch.py.
"""

import csv
import math
import subprocess
import threading
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
from slam_toolbox.srv import DeserializePoseGraph, SaveMap, SerializePoseGraph
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


class SlamPointsNode(Node):

    def __init__(self):
        super().__init__('slam_points_node')
        self.declare_parameter('points_file', '')
        self.declare_parameter('only', '')
        self.declare_parameter('base_map', '')
        self.declare_parameter('output_map', '')
        self.declare_parameter('entity', 'uvix')
        self.declare_parameter('map_to_world', [0.0, 0.5, 0.0])
        self.declare_parameter('spawn_z', 0.05)
        self.declare_parameter('settle_time', 2.0)
        self.declare_parameter('spin_speed', 0.8)
        self.declare_parameter('spin_turns', 1.0)
        self.declare_parameter('spin_timeout', 40.0)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('robot_frame', 'base_footprint')

        gp = lambda n: self.get_parameter(n).value  # noqa: E731
        self.base_map = gp('base_map')
        self.output_map = gp('output_map')
        self.entity = gp('entity')
        self.map_to_world = [float(v) for v in gp('map_to_world')]
        self.spawn_z = float(gp('spawn_z'))
        self.settle_time = float(gp('settle_time'))
        self.spin_speed = float(gp('spin_speed'))
        self.spin_turns = float(gp('spin_turns'))
        self.spin_timeout = float(gp('spin_timeout'))
        self.odom_frame = gp('odom_frame')
        self.robot_frame = gp('robot_frame')
        self.points = self._load_points(gp('points_file'), gp('only'))

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.deserialize = self.create_client(DeserializePoseGraph, '/slam_toolbox/deserialize_map')
        self.serialize = self.create_client(SerializePoseGraph, '/slam_toolbox/serialize_map')
        self.save_map = self.create_client(SaveMap, '/slam_toolbox/save_map')
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

    def _load_points(self, path, only):
        wanted = {s.strip() for s in only.split(',') if s.strip()}
        with open(path, newline='') as f:
            rows = [r for r in csv.DictReader(f) if not wanted or r['punto'] in wanted]
        return [(r['punto'], float(r['x_m']), float(r['y_m']), float(r['yaw_rad'])) for r in rows]

    def _call(self, client, req, timeout=60.0):
        if not client.wait_for_service(timeout_sec=timeout):
            raise RuntimeError(f'servicio {client.srv_name} no disponible')
        fut = client.call_async(req)
        end = time.monotonic() + timeout
        while not fut.done():
            if time.monotonic() > end:
                raise RuntimeError(f'{client.srv_name} no respondió')
            time.sleep(0.05)
        return fut.result()

    def _odom_yaw(self):
        try:
            t = self.tf_buffer.lookup_transform(self.odom_frame, self.robot_frame, Time())
            return yaw_of(t.transform.rotation)
        except Exception:
            return None

    def _stop(self):
        for _ in range(5):
            self.cmd_pub.publish(Twist())
            time.sleep(0.05)

    def _teleport(self, x, y, yaw):
        tx, ty, tyaw = self.map_to_world
        c, s = math.cos(tyaw), math.sin(tyaw)
        wx, wy, wyaw = tx + c * x - s * y, ty + s * x + c * y, wrap(yaw + tyaw)
        cmd = ['gz', 'model', '-m', self.entity,
               '-x', f'{wx:.3f}', '-y', f'{wy:.3f}', '-z', f'{self.spawn_z:.3f}',
               '-R', '0', '-P', '0', '-Y', f'{wyaw:.4f}']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            raise RuntimeError(f'gz model falló: {r.stderr.strip()}')

    def _load_graph(self, filename, x, y, yaw):
        req = DeserializePoseGraph.Request()
        req.filename = filename
        req.match_type = DeserializePoseGraph.Request.START_AT_GIVEN_POSE
        req.initial_pose.x, req.initial_pose.y, req.initial_pose.theta = x, y, yaw
        self._call(self.deserialize, req)

    def _spin(self):
        last = self._odom_yaw()
        if last is None:
            raise RuntimeError(f'sin TF {self.odom_frame} → {self.robot_frame}')
        goal = 2.0 * math.pi * self.spin_turns
        turned = 0.0
        twist = Twist()
        twist.angular.z = self.spin_speed
        end = time.monotonic() + self.spin_timeout
        while turned < goal and time.monotonic() < end:
            self.cmd_pub.publish(twist)
            time.sleep(0.05)
            yaw = self._odom_yaw()
            if yaw is not None:
                turned += abs(wrap(yaw - last))
                last = yaw
        self._stop()
        return math.degrees(turned)

    def _save(self):
        res = self._call(self.serialize, SerializePoseGraph.Request(filename=self.output_map))
        if res.result != SerializePoseGraph.Response.RESULT_SUCCESS:
            raise RuntimeError(f'no se pudo guardar {self.output_map}.posegraph')
        self._call(self.save_map, SaveMap.Request(name=String(data=self.output_map)))

    def run(self):
        log = self.get_logger()
        log.info(f'{len(self.points)} puntos | base {self.base_map} → salida {self.output_map}')
        source = self.base_map
        for k, (name, x, y, yaw) in enumerate(self.points, 1):
            log.info(f'[{k}/{len(self.points)}] {name} → ({x:.2f}, {y:.2f}, {math.degrees(yaw):.0f}°)')
            self._stop()
            self._teleport(x, y, yaw)
            time.sleep(self.settle_time)
            self._load_graph(source, x, y, yaw)
            time.sleep(1.0)
            deg = self._spin()
            time.sleep(1.0)
            self._save()
            source = self.output_map
            log.info(f'[{k}/{len(self.points)}] {name} listo (giro {deg:.0f}°), guardado')
        log.info(f'Terminado. Mapa ampliado en {self.output_map}.posegraph / .pgm / .yaml')


def main(args=None):
    rclpy.init(args=args)
    node = SlamPointsNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    threading.Thread(target=executor.spin, daemon=True).start()
    code = 0
    try:
        node.run()
    except KeyboardInterrupt:
        node._stop()
    except Exception as e:
        node.get_logger().error(str(e))
        node._stop()
        code = 1
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(code)


if __name__ == '__main__':
    main()

"""Publish M1-03 fixture cases; no message is presented as model output."""

import uuid

import rclpy
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile,
                       QoSReliabilityPolicy)
from uvix_interfaces.msg import GestureEvent

from .scenario_fixtures import SCENARIOS, GestureEventGate, build_fixture


class SyntheticPerceptionProvider(Node):
    def __init__(self):
        super().__init__('synthetic_perception_provider')
        self.declare_parameter('scenario', 'all')
        self.declare_parameter('publish_rate_hz', 2.0)
        self.declare_parameter('scenario_duration_s', 3.0)
        self.declare_parameter('minimum_gesture_persistence_s', 0.5)
        self.scenario = str(self.get_parameter('scenario').value)
        self.rate = float(self.get_parameter('publish_rate_hz').value)
        self.scenario_duration = float(self.get_parameter('scenario_duration_s').value)
        if self.scenario not in ('all', *SCENARIOS):
            raise ValueError(f'scenario must be all or one of {SCENARIOS}')
        if self.rate <= 0.0 or self.scenario_duration <= 0.0:
            raise ValueError('publish_rate_hz and scenario_duration_s must be positive')
        # These are low-rate result messages, so reliable delivery helps fixture consumers.
        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST, depth=10,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE)
        self.people_pub = self.create_publisher(
            type(build_fixture('empty', self.get_clock().now().to_msg())[0]),
            '/perception/people', qos)
        self.pose_pub = self.create_publisher(
            type(build_fixture('empty', self.get_clock().now().to_msg())[1]),
            '/perception/body_poses', qos)
        self.face_pub = self.create_publisher(
            type(build_fixture('empty', self.get_clock().now().to_msg())[2]),
            '/perception/face_matches', qos)
        gesture_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST, depth=10,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.gesture_pub = self.create_publisher(
            GestureEvent, '/perception/gestures', gesture_qos)
        self.session_id = str(uuid.uuid4())
        self.gesture_gate = GestureEventGate(float(
            self.get_parameter('minimum_gesture_persistence_s').value))
        self.started_at = self.get_clock().now().nanoseconds / 1e9
        self.last_scenario = None
        self.timer = self.create_timer(1.0 / self.rate, self.publish_observations)
        self.get_logger().info(
            f'Publicador sintético listo; scenario={self.scenario}, rate={self.rate:g} Hz')

    def _scenario_now(self, now_s):
        if self.scenario != 'all':
            return self.scenario
        index = int((now_s - self.started_at) / self.scenario_duration) % len(SCENARIOS)
        return SCENARIOS[index]

    def publish_observations(self):
        now = self.get_clock().now()
        now_s = now.nanoseconds / 1e9
        scenario = self._scenario_now(now_s)
        if scenario != self.last_scenario:
            if self.last_scenario == 'gesture':
                self.gesture_gate.observe(
                    self.session_id, 'track-04', GestureEvent.HAND_RAISED,
                    False, now_s)
            self.last_scenario = scenario
            self.get_logger().info(f'Fixture M1-03: {scenario}')
        people, poses, faces, gesture = build_fixture(
            scenario, now.to_msg(), self.session_id)
        self.people_pub.publish(people)
        self.pose_pub.publish(poses)
        self.face_pub.publish(faces)
        if gesture and self.gesture_gate.observe(
                gesture.tracker_session_id, gesture.track_id,
                gesture.gesture, True, now_s):
            self.gesture_pub.publish(gesture)


def main(args=None):
    rclpy.init(args=args)
    node = SyntheticPerceptionProvider()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

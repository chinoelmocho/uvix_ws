import rclpy
from rclpy.node import Node
import socket
import json
from sensor_msgs.msg import Joy

class JoyUDPNode(Node):

    def __init__(self):
        super().__init__('joy_udp_node')

        self.publisher_ = self.create_publisher(Joy, '/joy', 10)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 5005))

        self.get_logger().info("Publicando /joy desde UDP...")

        self.timer = self.create_timer(0.05, self.read_udp)

    def read_udp(self):
        try:
            self.sock.setblocking(False)
            data, _ = self.sock.recvfrom(4096)

            msg = json.loads(data.decode())

            joy_msg = Joy()
            joy_msg.axes = msg["axes"]
            joy_msg.buttons = msg["buttons"]

            self.publisher_.publish(joy_msg)

        except BlockingIOError:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = JoyUDPNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
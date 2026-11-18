#!/usr/bin/python3
import os

import django
import rclpy
from rclpy.node import Node


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uvix_data_project.settings")
    django.setup()

    from people.ros_services import get_person
    from uvix_interfaces.srv import GetPerson

    rclpy.init()
    node = Node("uvix_data")
    try:
        node.create_service(GetPerson, "/uvix/get_person", get_person)
        node.get_logger().info("Servicio /uvix/get_person listo")
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()

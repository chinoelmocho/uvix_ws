#!/usr/bin/python3
"""Proveedor de identidad FICTICIO: sirve /uvix/get_request_identity.

Sustituye al componente de identificación en M1 (sin cámara ni voz). Lee un
JSON con las verificaciones por request_id:

    {"req-0001": {"person_id": "prueba_staff_juan", "status": 2, "ttl_s": 60}, ...}

``status``: 0 UNKNOWN, 1 CANDIDATE, 2 VERIFIED. ``ttl_s`` negativo = vencida.
valid_until se calcula al arrancar. Uso:

    python3 identidad_ficticia.py verificaciones.json
"""
import json
import sys

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from uvix_interfaces.msg import IdentityVerification
from uvix_interfaces.srv import GetRequestIdentity


def main():
    with open(sys.argv[1]) as f:
        datos = json.load(f)
    rclpy.init()
    node = Node("identidad_ficticia")
    ahora = node.get_clock().now().nanoseconds
    verif = {}
    for rid, d in datos.items():
        v = IdentityVerification()
        v.header.stamp = node.get_clock().now().to_msg()
        v.request_id = rid
        v.person_id = d.get("person_id", "")
        v.identity_status = d.get("status", IdentityVerification.IDENTITY_VERIFIED)
        v.method = IdentityVerification.METHOD_FACE
        v.confidence = 0.97 if v.identity_status == 2 else 0.6
        v.verifier = "identidad_ficticia"
        fin = ahora + int(d.get("ttl_s", 60) * 1e9)
        v.valid_until.sec, v.valid_until.nanosec = fin // 10**9, fin % 10**9
        verif[rid] = v

    def cb(req, resp):
        if req.request_id in verif:
            resp.found = True
            resp.identity = verif[req.request_id]
        return resp

    node.create_service(GetRequestIdentity, "/uvix/get_request_identity", cb)
    node.get_logger().info(f"Identidad ficticia lista ({len(verif)} verificaciones)")
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()

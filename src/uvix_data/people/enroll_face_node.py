#!/usr/bin/python3
"""Servidor SIMULADO de /uvix/enroll_face (uvix_interfaces/action/EnrollFace).

Sin cámara: la calidad de cada muestra sale del archivo JSON indicado en
``sim_muestras_file`` (``{"person_id": [0.95, 0.9, null, ...]}``; ``null`` =
rostro perdido). Personas sin entrada reciben muestras buenas. Autoriza cada
alta con /uvix/check_permission (operación ``enroll_face``).

    ros2 run uvix_data uvix_enroll_face_sim --ros-args -p sim_periodo_s:=0.2 \
        -p sim_muestras_file:=/tmp/muestras.json
"""
import json
import os
import sys
import threading
import time

import django
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uvix_data_project.settings")
    django.setup()
    from people.enrolamiento import EnrolamientoSimulado
    from people.ros_node import comprobar_base
    from uvix_interfaces.action import EnrollFace
    from uvix_interfaces.srv import CheckPermission

    rclpy.init()
    node = Node("uvix_enroll_face_sim")
    log = node.get_logger()
    periodo = node.declare_parameter("sim_periodo_s", 0.2).value
    archivo = node.declare_parameter("sim_muestras_file", "").value
    muestras = {}
    if archivo:
        with open(archivo) as f:
            muestras = json.load(f)
    timeout = node.declare_parameter("check_permission_timeout_s", 3.0).value
    cli = node.create_client(CheckPermission, "/uvix/check_permission",
                             callback_group=MutuallyExclusiveCallbackGroup())

    def autorizar(request_id):
        if not cli.wait_for_service(timeout_sec=timeout):
            return None
        fut = cli.call_async(CheckPermission.Request(request_id=request_id, operation="enroll_face"))
        listo = threading.Event()
        fut.add_done_callback(lambda _f: listo.set())
        if not listo.wait(timeout):
            cli.remove_pending_request(fut)
            return None
        return fut.result()

    nucleo = EnrolamientoSimulado(autorizar)

    def fuente(person_id, requeridas):
        for q in muestras.get(person_id, [0.95] * requeridas):
            time.sleep(periodo)
            yield q

    def ejecutar(goal_handle):
        g = goal_handle.request
        res = nucleo.ejecutar(
            g, fuente(g.person_id, g.samples_required or nucleo.muestras_por_defecto),
            cancelado=lambda: goal_handle.is_cancel_requested,
            feedback=goal_handle.publish_feedback)
        log.info(f"enroll_face person={g.person_id} request_id={g.request_id} "
                 f"result={res.result_code} enrolled={res.enrolled} {res.detail}")
        if res.result_code == EnrollFace.Result.RESULT_CANCELED:
            goal_handle.canceled()
        elif res.enrolled:
            goal_handle.succeed()
        else:
            goal_handle.abort()
        return res

    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    codigo = 0
    try:
        if not comprobar_base(log):
            return 1
        ActionServer(node, EnrollFace, "/uvix/enroll_face", ejecutar,
                     goal_callback=lambda _g: GoalResponse.ACCEPT,
                     cancel_callback=lambda _g: CancelResponse.ACCEPT,
                     callback_group=ReentrantCallbackGroup())
        log.info("Acción /uvix/enroll_face lista (SIMULADA, sin cámara)")
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown(timeout_sec=1.0)
        node.destroy_node()
        rclpy.try_shutdown()
    return codigo


if __name__ == "__main__":
    sys.exit(main())

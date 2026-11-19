#!/usr/bin/python3
import os
import sys

import django
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

MIGRAR = "Ejecute 'python3 -m django migrate --settings=uvix_data_project.settings'."


def comprobar_base(logger):
    """Devuelve True si la base existe y no tiene migraciones pendientes.

    Se comprueba antes de ofrecer el servicio para no anunciar
    /uvix/get_person con un almacenamiento inutilizable.
    """
    from django.conf import settings
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.db.utils import DatabaseError

    ruta = settings.DATABASES["default"]["NAME"]
    logger.info(f"Base de datos: {ruta}")
    # Sin esta comprobación sqlite crearía un archivo vacío.
    if not os.path.isfile(ruta):
        logger.error(f"No existe la base {ruta}. {MIGRAR}")
        return False
    try:
        executor = MigrationExecutor(connection)
        pendientes = executor.migration_plan(executor.loader.graph.leaf_nodes())
    except DatabaseError as exc:
        logger.error(f"No se puede leer la base {ruta}: {exc}")
        return False
    finally:
        connection.close()
    if pendientes:
        logger.error(f"Faltan {len(pendientes)} migraciones en {ruta}. {MIGRAR}")
        return False
    return True


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uvix_data_project.settings")
    django.setup()

    from django.db.utils import DatabaseError
    from people.permisos import ProveedorRos, evaluar
    from people.ros_services import get_person
    from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
    from rclpy.executors import MultiThreadedExecutor
    from uvix_interfaces.srv import CheckPermission, GetPerson

    rclpy.init()
    node = Node("uvix_data")
    log = node.get_logger()
    servicio_identidad = node.declare_parameter(
        "identity_service", "/uvix/get_request_identity").value
    timeout_identidad = node.declare_parameter("identity_timeout_s", 2.0).value
    fallo_bd = []

    def get_person_cb(request, response):
        try:
            return get_person(request, response)
        except DatabaseError as exc:
            # Sin respuesta y el nodo se detiene: el cliente lo ve como
            # servicio no disponible, nunca como found=False.
            fallo_bd.append(exc)
            raise

    # CheckPermission llama a GetRequestIdentity dentro de su callback: el
    # cliente va en otro callback group y el ejecutor es multihilo.
    proveedor = ProveedorRos(node, servicio_identidad, timeout_identidad,
                             MutuallyExclusiveCallbackGroup())

    def check_permission_cb(request, response):
        r = evaluar(request.request_id, request.operation, proveedor,
                    node.get_clock().now().nanoseconds, response)
        log.info(f"check_permission request_id={request.request_id} op={request.operation} "
                 f"persona={r.evaluated_person_id or '-'} code={r.code} allowed={r.allowed}")
        return r

    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    codigo = 0
    try:
        if not comprobar_base(log):
            return 1
        node.create_service(GetPerson, "/uvix/get_person", get_person_cb,
                            callback_group=MutuallyExclusiveCallbackGroup())
        node.create_service(CheckPermission, "/uvix/check_permission", check_permission_cb,
                            callback_group=ReentrantCallbackGroup())
        log.info(f"Servicios /uvix/get_person y /uvix/check_permission listos "
                 f"(identidad: {servicio_identidad}, timeout {timeout_identidad} s)")
        while rclpy.ok() and not fallo_bd:
            executor.spin_once(timeout_sec=0.2)
    except (KeyboardInterrupt, ExternalShutdownException):
        # Ctrl+C o SIGTERM (rclpy cierra el contexto): cierre normal.
        pass
    finally:
        if fallo_bd:
            log.fatal(f"Error de base de datos; el nodo se detiene: {fallo_bd[0]}")
            codigo = 1
        executor.shutdown(timeout_sec=1.0)
        node.destroy_node()
        rclpy.try_shutdown()
    return codigo


if __name__ == "__main__":
    sys.exit(main())

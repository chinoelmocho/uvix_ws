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
    from people.ros_services import get_person
    from uvix_interfaces.srv import GetPerson

    rclpy.init()
    node = Node("uvix_data")
    codigo = 0
    try:
        if not comprobar_base(node.get_logger()):
            return 1
        node.create_service(GetPerson, "/uvix/get_person", get_person)
        node.get_logger().info("Servicio /uvix/get_person listo")
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        # Ctrl+C o SIGTERM (rclpy cierra el contexto): cierre normal.
        pass
    except DatabaseError as exc:
        # El nodo termina sin responder: el cliente lo ve como servicio no
        # disponible, nunca como found=False.
        node.get_logger().fatal(f"Error de base de datos; el nodo se detiene: {exc}")
        codigo = 1
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return codigo


if __name__ == "__main__":
    sys.exit(main())

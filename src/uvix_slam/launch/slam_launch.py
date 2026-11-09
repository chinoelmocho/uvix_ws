#!/usr/bin/env python3
"""
slam_toolbox (mapeo o localización) sobre una simulación ya abierta.

  ros2 launch Uvix_sim slam_launch.py                                  # mapa nuevo
  ros2 launch Uvix_sim slam_launch.py map:=PASILLO                     # ampliar mapa
  ros2 launch Uvix_sim slam_launch.py mode:=localization map:=PASILLO  # solo localizar
  ros2 launch Uvix_sim slam_launch.py mode:=localization map:=PASILLO start_pose:="x y yaw"

Guardar el mapa:
  ros2 run nav2_map_server map_saver_cli -f ~/uvix_ws/src/Uvix_sim/maps/<nombre>
  ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
      "{filename: '/home/chino/uvix_ws/src/Uvix_sim/maps/<nombre>'}"
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, LogInfo, OpaqueFunction,
                            RegisterEventHandler)
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

MAPS_DIR = os.path.expanduser('~/uvix_ws/src/Uvix_sim/maps')


def resolve_map(name):
    """'PASILLO' → MAPS_DIR/PASILLO; ruta absoluta se deja igual; quita extensión."""
    if not name:
        return ''
    path = name if os.path.isabs(name) else os.path.join(MAPS_DIR, name)
    root, ext = os.path.splitext(path)
    return root if ext in ('.posegraph', '.data', '.yaml', '.pgm') else path


def launch_setup(context):
    mode = LaunchConfiguration('mode').perform(context).strip().lower()
    map_file = resolve_map(LaunchConfiguration('map').perform(context).strip())
    start_pose = LaunchConfiguration('start_pose').perform(context).strip()

    if mode not in ('mapping', 'localization'):
        return [LogInfo(msg=f"[slam_launch] ERROR: mode:={mode} no válido "
                            "(usa mapping o localization)")]
    if mode == 'localization' and not map_file:
        return [LogInfo(msg='[slam_launch] ERROR: mode:=localization necesita map:=<nombre>')]
    if map_file and not os.path.isfile(map_file + '.posegraph'):
        return [LogInfo(msg=f'[slam_launch] ERROR: no existe {map_file}.posegraph')]

    overrides = {'use_sim_time': True, 'mode': mode}
    if map_file:
        overrides['map_file_name'] = map_file
        if start_pose:
            overrides['map_start_pose'] = [float(v) for v in start_pose.replace(',', ' ').split()]
            overrides['map_start_at_dock'] = False
        else:
            overrides['map_start_at_dock'] = True

    prereq_checker = Node(
        package='Uvix_sim',
        executable='slam_prereq_checker',
        name='slam_prereq_checker',
        output='screen',
        parameters=[{'use_sim_time': True,
                     'timeout': LaunchConfiguration('prereq_timeout')}],
    )

    slam_toolbox = Node(
        package='slam_toolbox',
        executable=('localization_slam_toolbox_node' if mode == 'localization'
                    else 'async_slam_toolbox_node'),
        name='slam_toolbox',
        output='screen',
        parameters=[LaunchConfiguration('slam_params'), overrides],
    )

    desc = f'{mode}, ' + (f'mapa {map_file}' if map_file else 'mapa nuevo')

    def on_checker_exit(event, context):
        if event.returncode == 0:
            return [LogInfo(msg=f'[slam_launch] Sensores + EKF listos → slam_toolbox ({desc})'),
                    slam_toolbox]
        return [LogInfo(msg='[slam_launch] ERROR: sensores/EKF no listos. '
                            '¿Está corriendo sim_launch.py? Revisa la tabla del checker.')]

    start_slam = RegisterEventHandler(OnProcessExit(
        target_action=prereq_checker,
        on_exit=on_checker_exit,
    ))

    return [prereq_checker, start_slam]


def generate_launch_description():

    pkg_share = get_package_share_directory('Uvix_sim')
    default_slam_params = os.path.join(pkg_share, 'config', 'slam_params.yaml')

    declare_slam_params = DeclareLaunchArgument(
        'slam_params', default_value=default_slam_params,
        description='Parámetros de slam_toolbox',
    )
    declare_mode = DeclareLaunchArgument(
        'mode', default_value='mapping',
        description='mapping (crear/ampliar mapa) o localization (solo localizarse)',
    )
    declare_map = DeclareLaunchArgument(
        'map', default_value='',
        description='Mapa serializado: nombre en maps/ o ruta absoluta, sin extensión. '
                    'Vacío = mapa nuevo (solo en mapping)',
    )
    declare_start_pose = DeclareLaunchArgument(
        'start_pose', default_value='',
        description='"x y yaw" inicial en el mapa cargado. Vacío = pose del dock del mapa',
    )
    declare_prereq_timeout = DeclareLaunchArgument(
        'prereq_timeout', default_value='120.0',
        description='Segundos máximos esperando sensores + EKF antes de abortar SLAM',
    )

    return LaunchDescription([
        declare_slam_params,
        declare_mode,
        declare_map,
        declare_start_pose,
        declare_prereq_timeout,
        OpaqueFunction(function=launch_setup),
    ])

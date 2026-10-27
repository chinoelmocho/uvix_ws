#!/usr/bin/env python3
"""
Amplía un mapa guardado visitando los puntos de config/puntos_slam.csv.

  ros2 launch Uvix_sim sim_launch.py
  ros2 launch Uvix_sim slam_extend_launch.py                       # PASILLO → PASILLO_ext
  ros2 launch Uvix_sim slam_extend_launch.py only:=P03,P07         # solo algunos puntos
  ros2 launch Uvix_sim slam_extend_launch.py base_map:=PASILLO_ext output:=PASILLO_ext2

base_map no se modifica nunca. Sin cierre de bucles, para que el grafo
existente no se reoptimice: lo nuevo se pega a lo ya mapeado.
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, LogInfo, OpaqueFunction,
                            RegisterEventHandler, TimerAction)
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

MAPS_DIR = os.path.expanduser('~/uvix_ws/src/Uvix_sim/maps')


def map_path(name):
    path = name if os.path.isabs(name) else os.path.join(MAPS_DIR, name)
    root, ext = os.path.splitext(path)
    return root if ext in ('.posegraph', '.data', '.yaml', '.pgm') else path


def launch_setup(context):
    cfg = lambda n: LaunchConfiguration(n).perform(context).strip()  # noqa: E731
    base = map_path(cfg('base_map'))
    output = map_path(cfg('output') or cfg('base_map') + '_ext')
    points_file = cfg('points')

    if not os.path.isfile(base + '.posegraph'):
        return [LogInfo(msg=f'[slam_extend] ERROR: no existe {base}.posegraph')]
    if output == base:
        return [LogInfo(msg='[slam_extend] ERROR: output no puede ser el mismo base_map')]
    if not os.path.isfile(points_file):
        return [LogInfo(msg=f'[slam_extend] ERROR: no existe {points_file}')]

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
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[LaunchConfiguration('slam_params'), {
            'use_sim_time': True,
            'mode': 'mapping',
            'map_file_name': base,
            'map_start_at_dock': True,
            'do_loop_closing': False,
        }],
    )

    points_node = Node(
        package='Uvix_sim',
        executable='slam_points_node',
        name='slam_points_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'points_file': points_file,
            'only': cfg('only'),
            'base_map': base,
            'output_map': output,
            'spin_speed': float(cfg('spin_speed')),
            'map_to_world': [float(v) for v in cfg('map_to_world').replace(',', ' ').split()],
        }],
    )

    def on_checker_exit(event, context):
        if event.returncode == 0:
            return [LogInfo(msg=f'[slam_extend] {base} → {output}'),
                    slam_toolbox,
                    TimerAction(period=5.0, actions=[points_node])]
        return [LogInfo(msg='[slam_extend] ERROR: sensores/EKF no listos. '
                            '¿Está corriendo sim_launch.py?')]

    return [prereq_checker,
            RegisterEventHandler(OnProcessExit(target_action=prereq_checker,
                                               on_exit=on_checker_exit))]


def generate_launch_description():
    pkg_share = get_package_share_directory('Uvix_sim')

    return LaunchDescription([
        DeclareLaunchArgument(
            'base_map', default_value='PASILLO',
            description='Mapa serializado de partida (no se modifica)'),
        DeclareLaunchArgument(
            'output', default_value='',
            description='Mapa de salida. Vacío = <base_map>_ext'),
        DeclareLaunchArgument(
            'points', default_value=os.path.join(pkg_share, 'config', 'puntos_slam.csv'),
            description='CSV punto,x_m,y_m,yaw_rad en frame map'),
        DeclareLaunchArgument(
            'only', default_value='',
            description='Puntos a visitar separados por coma (P01,P05). Vacío = todos'),
        DeclareLaunchArgument(
            'spin_speed', default_value='0.8',
            description='rad/s del giro en cada punto'),
        DeclareLaunchArgument(
            'map_to_world', default_value='0.0 0.5 0.0',
            description='"x y yaw" del origen del mapa en el mundo de Gazebo (spawn del robot)'),
        DeclareLaunchArgument(
            'slam_params', default_value=os.path.join(pkg_share, 'config', 'slam_params.yaml'),
            description='Parámetros de slam_toolbox'),
        DeclareLaunchArgument(
            'prereq_timeout', default_value='120.0',
            description='Segundos máximos esperando sensores + EKF'),
        OpaqueFunction(function=launch_setup),
    ])

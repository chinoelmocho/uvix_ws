#!/usr/bin/env python3
"""
sim_launch.py — v3  (Gazebo + robot + EKF + SLAM en un solo launch)
=====================================================================
Orden de arranque garantizado:
  1. Gazebo + robot_state_publisher        (inmediato)
  2. gazebo_ready_watcher                  (espera /clock con BEST_EFFORT)
  3. spawn_entity                          (cuando Gazebo está listo)
  4. joint_state_broadcaster               (+3s tras spawn)
  5. bobert_base_controller + relay        (+5s tras spawn)
  6. robot_localization EKF               (+8s tras spawn)
  7. slam_toolbox                          (+12s tras spawn)
     ↑ en este punto el LIDAR lleva varios segundos publicando
       con sim_time correcto y el TF odom→base_footprint ya existe
"""

import os
import xacro

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
    RegisterEventHandler,
    LogInfo,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():

    package_name = 'bobert_sim'
    pkg_share    = get_package_share_directory(package_name)

    world_file  = os.path.join(pkg_share, 'worlds', 'hospital.world')
    models_path = os.path.join(pkg_share, 'models')
    xacro_file  = os.path.join(pkg_share, 'urdf', 'bobert.xacro')
    ekf_config  = os.path.join(pkg_share, 'config', 'ekf.yaml')
    slam_config = os.path.join(pkg_share, 'config', 'mapper_params_online_async.yaml')

    # ── Variables de entorno ───────────────────────────────────────────────────
    set_gazebo_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=(
            models_path + ':' +
            os.path.join(pkg_share, '..') + ':' +
            os.environ.get('GAZEBO_MODEL_PATH', '')
        )
    )

    
    set_gazebo_resource_path = SetEnvironmentVariable(
        name='GAZEBO_RESOURCE_PATH',
        value=pkg_share + ':' + os.environ.get('GAZEBO_RESOURCE_PATH', '')
    )

    # ── use_sim_time en TODOS los nodos — esto es lo que sincroniza el LIDAR ──
    sim_params = {'use_sim_time': True}

    robot_description_xml = xacro.process_file(xacro_file).toxml()

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 1 — arranque inmediato
    # ══════════════════════════════════════════════════════════════════════════


    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('gazebo_ros'),
                'launch', 'gazebo.launch.py'
            )
        ]),
        launch_arguments={'world': world_file}.items(),
    )

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 2 — watcher: espera /clock con QoS BEST_EFFORT (Gazebo Classic)
    # ══════════════════════════════════════════════════════════════════════════

    gazebo_ready_watcher = Node(
        package='bobert_sim',
        executable='gazebo_ready_watcher',
        name='gazebo_ready_watcher',
        output='screen',
        parameters=[sim_params, {'timeout': 300.0, 'min_sim_time_sec': 0}],
    )

    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_xml,
            'use_sim_time': True,
        }],
    )

    
    # ══════════════════════════════════════════════════════════════════════════
    # FASE 3 — spawn (cuando watcher sale con exit 0)
    # ══════════════════════════════════════════════════════════════════════════

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_bobert',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'bobert',
            '-y', '0.5',
            '-z', '0.1',
        ],
        output='screen',
        parameters=[sim_params],
    )

    # ══════════════════════════════════════════════════════════════════════════
    # FASE 4 — todo lo demás en cascada tras el spawn
    #
    # +3s  → joint_state_broadcaster  (controller_manager ya activo)
    # +5s  → diff_drive + relay       (joint_state_broadcaster ya activo)
    # +8s  → EKF                      (/odom e /imu ya publicando)
    # +12s → SLAM                     (TF odom→base_footprint existe,
    #                                  LIDAR lleva ~8s con sim_time correcto)
    # ══════════════════════════════════════════════════════════════════════════

    joint_broad_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        parameters=[sim_params],
        output='screen',
    )

    diff_drive_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['bobert_base_controller'],
        remappings=[('/bobert_base_controller/cmd_vel_unstamped', '/cmd_vel')],
        parameters=[sim_params],
        output='screen',
    )

    cmd_vel_relay = Node(
        package='topic_tools',
        executable='relay',
        arguments=['/cmd_vel', '/bobert_base_controller/cmd_vel_unstamped'],
        output='screen',
        parameters=[sim_params],
    )

    robot_localization_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config, sim_params],
    )

    # SLAM arranca último: así el LIDAR ya lleva ~8s publicando con
    # sim_time correcto y el TF odom→base_footprint del EKF ya existe.
    # Sin esta espera SLAM descarta todos los scans con el error
    # "timestamp anterior al cache de TF".


    # ══════════════════════════════════════════════════════════════════════════
    # CADENA DE EVENTOS
    # ══════════════════════════════════════════════════════════════════════════

    on_watcher_exit = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=gazebo_ready_watcher,
            on_exit=[
                LogInfo(msg='[sim_launch] /clock activo → esperando 2s antes de RSP...'),

                TimerAction(period=2.0, actions=[   # ← dar tiempo al reloj
                    LogInfo(msg='[sim_launch] Lanzando RSP + spawn'),
                    node_robot_state_publisher,
                    spawn_entity,
                ]),
            ]
        )
    )

    on_spawn_exit = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity,
            on_exit=[
                LogInfo(msg='[sim_launch] Robot en mundo → arrancando sistema...'),

                TimerAction(period=3.0, actions=[
                    LogInfo(msg='[sim_launch] +3s  → joint_state_broadcaster'),
                    joint_broad_spawner,
                ]),

                TimerAction(period=5.0, actions=[
                    LogInfo(msg='[sim_launch] +5s  → diff_drive + relay'),
                    diff_drive_spawner,
                    cmd_vel_relay,
                ]),

                TimerAction(period=8.0, actions=[
                    LogInfo(msg='[sim_launch] +8s  → robot_localization EKF'),
                    robot_localization_node,
                ]),
            ]
        )
    )

    # ══════════════════════════════════════════════════════════════════════════
    return LaunchDescription([
        set_gazebo_model_path,
        set_gazebo_resource_path,

        gazebo,
        gazebo_ready_watcher,

        on_watcher_exit,
        on_spawn_exit,
    ])
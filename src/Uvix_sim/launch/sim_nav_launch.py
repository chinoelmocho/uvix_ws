#!/usr/bin/env python3
"""
Simulación + Nav2.

  ros2 launch Uvix_sim sim_nav_launch.py                       # solo simulación
  ros2 launch Uvix_sim sim_nav_launch.py nav:=true             # + Nav2 (AMCL) con PASILLO
  ros2 launch Uvix_sim sim_nav_launch.py nav:=true map:=/ruta/mapa.yaml nav_delay:=30.0
  ros2 launch Uvix_sim sim_nav_launch.py nav:=true slam:=true  # SLAM + Nav2, sin AMCL
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    LogInfo,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():

    pkg_share  = get_package_share_directory('Uvix_sim')
    nav2_share = get_package_share_directory('nav2_bringup')

    default_map    = os.path.join(pkg_share, 'maps', 'PASILLO.yaml')
    default_params = os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    nav_rviz       = os.path.join(pkg_share, 'config', 'nav.rviz')
    sim_rviz      = os.path.join(pkg_share, 'config', 'basic.rviz')
    slam_params    = os.path.join(pkg_share, 'config', 'slam_params.yaml')

    declare_nav = DeclareLaunchArgument(
        'nav', default_value='false', choices=['true', 'false'],
        description='Lanzar Nav2 (AMCL + navegación) además de la simulación',
    )
    declare_slam = DeclareLaunchArgument(
        'slam', default_value='false', choices=['true', 'false'],
        description='Con nav:=true: SLAM (slam_toolbox) en vez de map_server + AMCL',
    )
    declare_slam_params = DeclareLaunchArgument(
        'slam_params', default_value=slam_params,
        description='Parámetros de slam_toolbox para slam:=true',
    )
    declare_map = DeclareLaunchArgument(
        'map', default_value=default_map,
        description='Mapa (.yaml) para map_server/AMCL',
    )
    declare_params = DeclareLaunchArgument(
        'nav_params', default_value=default_params,
        description='Archivo de parámetros de Nav2',
    )
    declare_delay = DeclareLaunchArgument(
        'nav_delay', default_value='20.0',
        description='Segundos de espera antes de lanzar Nav2 (Gazebo + spawn + EKF)',
    )
    declare_render = DeclareLaunchArgument(
        'render', default_value='gpu', choices=['gpu', 'cpu'],
        description='Renderizado de Gazebo/RViz: gpu (NVIDIA en WSL) o cpu (software)',
    )
    declare_rviz = DeclareLaunchArgument(
        'rviz', default_value='true', choices=['true', 'false'],
        description='Abrir RViz (basic.rviz; con nav:=true usa nav.rviz)',
    )
    declare_rviz_delay = DeclareLaunchArgument(
        'rviz_delay', default_value='5.0',
        description='Segundos tras arrancar el EKF (fin de la cadena) antes de abrir RViz',
    )

    nav  = LaunchConfiguration('nav')
    slam = LaunchConfiguration('slam')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'sim_launch.py')
        ),
        launch_arguments={
            'rviz_config': PythonExpression(
                ["'", nav_rviz, "' if '", nav, "' == 'true' else '", sim_rviz, "'"]),
        }.items(),
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_share, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'params_file': LaunchConfiguration('nav_params'),
            'use_sim_time': 'true',
            'autostart': 'true',
        }.items(),
        condition=UnlessCondition(slam),
    )

    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        parameters=[LaunchConfiguration('slam_params'), {'use_sim_time': True}],
        output='screen',
        condition=IfCondition(slam),
    )
    nav2_slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_share, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'params_file': LaunchConfiguration('nav_params'),
            'use_sim_time': 'true',
            'autostart': 'true',
        }.items(),
        condition=IfCondition(slam),
    )

    voxel_cloud = Node(
        package='nav2_costmap_2d',
        executable='nav2_costmap_2d_cloud',
        name='local_voxel_cloud',
        namespace='local_costmap',
        parameters=[{'use_sim_time': True}],
        output='log',
    )


    nav_group = GroupAction(
        condition=IfCondition(LaunchConfiguration('nav')),
        actions=[
            LogInfo(msg=['[sim_nav_launch] Nav2 arrancará en ',
                         LaunchConfiguration('nav_delay'), ' s']),
            TimerAction(
                period=LaunchConfiguration('nav_delay'),
                actions=[
                    LogInfo(msg='[sim_nav_launch] Lanzando Nav2 (AMCL + navegación)',
                            condition=UnlessCondition(slam)),
                    LogInfo(msg='[sim_nav_launch] Lanzando SLAM + Nav2 (sin AMCL)',
                            condition=IfCondition(slam)),
                    nav2,
                    slam_node,
                    nav2_slam,
                    voxel_cloud,
                ],
            ),
        ],
    )

    return LaunchDescription([
        declare_nav,
        declare_slam,
        declare_slam_params,
        declare_map,
        declare_params,
        declare_delay,
        declare_render,
        declare_rviz,
        declare_rviz_delay,
        sim,
        nav_group,
    ])

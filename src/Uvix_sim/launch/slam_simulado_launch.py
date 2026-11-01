import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
# ARCHIVO SOLO DE SLAM

def generate_launch_description():

    ruta_slam_params = os.path.join(
        get_package_share_directory('Uvix_sim'),
        'config',
        'slam_params.yaml'
    )
    ruta_nav_params = os.path.join(
        get_package_share_directory('Uvix_sim'),
        'config',
        'nav2_params.yaml'
    )

    pkg_nav2 = get_package_share_directory('nav2_bringup')


    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        parameters=[
            ruta_slam_params,
            {'use_sim_time': True}
        ],
        output='screen'
    )
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2, 'launch', 'navigation_launch.py')),
        launch_arguments={
            'use_sim_time': 'True',
            'params_file': ruta_nav_params,
            'autostart': 'True',
        }.items(),
    )

    return LaunchDescription([
        slam_node,
        nav2
    ])
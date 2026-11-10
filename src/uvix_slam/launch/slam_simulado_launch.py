import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
# SLAM + NAV2

def generate_launch_description():

    pkg_uvix_slam = get_package_share_directory('uvix_slam')
    pkg_uvix_nav = get_package_share_directory('uvix_nav')

    ruta_slam_params = os.path.join(pkg_uvix_slam, 'config', 'slam_params.yaml')
    ruta_nav_params  = os.path.join(pkg_uvix_nav, 'config', 'nav2_params.yaml')

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
            os.path.join(pkg_uvix_nav, 'launch', 'uvix_navigation_launch.py')),   # ← tu copia
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

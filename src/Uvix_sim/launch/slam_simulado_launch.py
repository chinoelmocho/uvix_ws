import os

from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


# ARCHIVO SOLO DE SLAM

def generate_launch_description():

    ruta_slam_params = os.path.join(
        get_package_share_directory('Uvix_sim'),
        'config',
        'slam_params.yaml'
    )

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

    return LaunchDescription([
        slam_node
    ])
"""Launch the M1-03 contract fixtures without a camera or vision model."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('scenario', default_value='all'),
        DeclareLaunchArgument('publish_rate_hz', default_value='2.0'),
        DeclareLaunchArgument('minimum_gesture_persistence_s', default_value='0.5'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        Node(
            package='uvix_perception', executable='synthetic_perception_provider',
            name='synthetic_perception_provider', output='screen',
            parameters=[{
                'use_sim_time': ParameterValue(
                    LaunchConfiguration('use_sim_time'), value_type=bool),
                'scenario': LaunchConfiguration('scenario'),
                'publish_rate_hz': LaunchConfiguration('publish_rate_hz'),
                'minimum_gesture_persistence_s': LaunchConfiguration(
                    'minimum_gesture_persistence_s'),
            }],
        ),
    ])

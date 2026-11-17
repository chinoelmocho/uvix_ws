from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('listen_scenario', default_value='recognized'),
        DeclareLaunchArgument('phrase_text', default_value='Buenos días, ¿cómo está?'),
        DeclareLaunchArgument('speak_duration_s', default_value='1.0'),
        Node(
            package='uvix_audio', executable='fake_voice_provider',
            name='fake_voice_provider', output='screen',
            parameters=[{
                'listen_scenario': LaunchConfiguration('listen_scenario'),
                'phrase_text': LaunchConfiguration('phrase_text'),
                'speak_duration_s': ParameterValue(
                    LaunchConfiguration('speak_duration_s'), value_type=float),
            }],
        ),
    ])

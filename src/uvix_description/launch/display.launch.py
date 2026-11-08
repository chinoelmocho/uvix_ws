import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.substitutions import (
    Command,    
    PathJoinSubstitution,
)

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    package_dir = get_package_share_directory("uvix_description")

    # El nombre del Xacro se indicará al ejecutar el launch.
    xacro_file = os.path.join(
        package_dir,
        "urdf",
        "uvix.xacro",
    )


    robot_description = ParameterValue(
        Command(["xacro ", xacro_file]),
        value_type=str,
    )

    controllers_yaml = os.path.join(
        package_dir,
        "config",
        "Uvix_controllers.yaml",
    )

    return LaunchDescription([

        # Publica la descripción del robot y sus transformaciones.
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{
                "robot_description": robot_description,
                "use_sim_time": False,
            }],
            output="screen",
        ),

        # Carga tu plugin y ejecuta el ciclo de control.
        Node(
            package="controller_manager",
            executable="ros2_control_node",
            parameters=[
                controllers_yaml,
                {"use_sim_time": False},
            ],
            remappings=[
                ("~/robot_description", "/robot_description"),
            ],
            output="screen",
        ),

        # Un spawner puede cargar y activar los dos controladores.
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=[
                "joint_state_broadcaster",
                "uvix_base_controller",
                "--controller-manager", "/controller_manager",
                "--controller-manager-timeout", "60",
            ],
            output="screen",
        ),

        # Visualización.
        Node(
            package="rviz2",
            executable="rviz2",
            arguments=["-f", "odom"],
            parameters=[{"use_sim_time": False}],
            output="screen",
        ),
    ])
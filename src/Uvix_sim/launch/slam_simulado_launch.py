from launch import LaunchDescription                    # Contenedor de todo lo que se va a lanzar
from launch.actions import DeclareLaunchArgument        # Declara argumentos que se pasan desde la terminal
from launch.substitutions import LaunchConfiguration     # Lee el valor de un argumento
from launch_ros.actions import Node                      # Representa un nodo de ROS 2
from ament_index_python.packages import get_package_share_directory
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os

#ARCHIVO SOLODE SIMULACION

def generate_launch_description(): 

    ruta_sim_launch = os.path.join(get_package_share_directory('Uvix_sim'),'launch','sim_launch.py')
    sim_launch = IncludeLaunchDescription(PythonLaunchDescriptionSource(ruta_sim_launch))




    return LaunchDescription([
        sim_launch
    ])
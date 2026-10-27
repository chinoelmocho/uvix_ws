import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    pkg_name = 'bobert_sim'
    
    # 1. Obtenemos las rutas de instalación de tu paquete y de Gazebo
    pkg_share = get_package_share_directory(pkg_name)
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')
    
    # 2. Definimos dónde quedaron instalados los modelos y el mundo
    # Asegúrate de que 'hospital.world' sea el nombre exacto de tu archivo dentro de la carpeta worlds
    models_path = os.path.join(pkg_share, 'models')
    world_file = os.path.join(pkg_share, 'worlds', 'hospital.world') 

    # 3. Le decimos a Gazebo que busque los modelos DENTRO de tu paquete
    set_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=models_path
    )

    # 4. Configuramos el nodo principal para arrancar Gazebo con tu mundo
    start_gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={'world': world_file}.items()
    )

    return LaunchDescription([
        set_model_path,
        start_gazebo
    ])
#!/usr/bin/env python3
"""
Simulación de Uvix en Gazebo + RViz.

  ros2 launch Uvix_sim sim_launch.py [render:=gpu|cpu] [gui:=true|false] [muebles:=true|false]
                                     [rviz:=true|false] [rviz_delay:=5.0] [rviz_render:=gpu|cpu]

Orden de arranque: limpieza → Gazebo → spawn → joint_state_broadcaster → diff drive
→ relay /cmd_vel + EKF + range_fix → RViz.
"""

import os
import subprocess
import time
import xacro

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition, LaunchConfigurationEquals
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


PROCESOS_SIM = [
    'gzserver',
    'gzclient',
    'rviz2',
    'robot_state_publisher',
    'spawn_entity.py',
    'controller_manager/spawner',
    'topic_tools/relay',
    'robot_localization/ekf_node',
    'lib/Uvix_sim/',
    'lib/nav2_',
    'slam_toolbox',
]


def pids_de_la_sim():
    """PIDs de procesos de la simulación vivos ahora, sin contar este launch."""
    propios = {os.getpid(), os.getppid()}
    pids = set()
    for patron in ['ros2 launch Uvix_sim', *PROCESOS_SIM]:
        r = subprocess.run(['pgrep', '-f', patron], capture_output=True, text=True)
        pids.update(int(p) for p in r.stdout.split())
    return sorted(pids - propios)


def limpiar_al_iniciar(context):
    """Antes de abrir Gazebo: mata lo que haya sobrado de una simulación anterior
    (terminal cerrada, Ctrl+C a medias, Gazebo colgado...)."""
    pids = pids_de_la_sim()
    if not pids:
        return [LogInfo(msg='[sim_launch] Limpieza: no había restos de otra simulación')]
    subprocess.run(['kill', '-9', *map(str, pids)], capture_output=True)
    time.sleep(1.0)
    return [LogInfo(msg=f'[sim_launch] Limpieza: eliminados {len(pids)} procesos '
                        'de una simulación anterior')]


def limpiar_al_cerrar(event, context):
    """Al cerrar el launch (Ctrl+C, fallo, etc.): ROS 2 primero pide a cada nodo
    que termine (SIGINT → SIGTERM); 8 s después un proceso aparte mata con -9
    los que sigan vivos (típico: gzserver colgado). Solo toca los PIDs que
    existían al cerrar, así no afecta a una simulación nueva."""
    pids = pids_de_la_sim()
    if pids:
        subprocess.Popen(
            ['bash', '-c', f'sleep 8; kill -9 {" ".join(map(str, pids))} 2>/dev/null'],
            start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    return [LogInfo(msg='[sim_launch] Cerrando: limpieza final programada en 8 s')]


def al_terminar_bien(proceso, mensaje, acciones):
    """Cuando `proceso` termina: si salió bien (exit 0) lanza `acciones`;
    si falló, avisa y cierra todo el launch en vez de seguir la cadena a ciegas."""
    def _callback(event, context):
        if event.returncode == 0:
            return [LogInfo(msg=mensaje), *acciones]
        motivo = f'{event.process_name} falló (exit {event.returncode})'
        return [
            LogInfo(msg=f'[sim_launch] ERROR: {motivo}. Se cierra el launch.'),
            EmitEvent(event=Shutdown(reason=motivo)),
        ]
    return RegisterEventHandler(OnProcessExit(target_action=proceso, on_exit=_callback))


def generate_launch_description():
    pkg_share = get_package_share_directory('Uvix_sim')

    world_file  = PythonExpression([
        "'", os.path.join(pkg_share, 'worlds', 'hospital.world'), "' if '",
        LaunchConfiguration('muebles'), "' == 'true' else '",
        os.path.join(pkg_share, 'worlds', 'hospital_empty.world'), "'",
    ])
    models_path = os.path.join(pkg_share, 'models')
    xacro_file  = os.path.join(pkg_share, 'urdf', 'uvix.xacro')
    ekf_config  = os.path.join(pkg_share, 'config', 'ekf.yaml')
    rviz_config = os.path.join(pkg_share, 'config', 'basic.rviz')

    sim_params = {'use_sim_time': True}

    robot_description_xml = xacro.process_file(xacro_file).toxml()

    declare_render = DeclareLaunchArgument(
        'render', default_value='gpu', choices=['gpu', 'cpu'],
        description='Renderizado de Gazebo/RViz: gpu (NVIDIA en WSL) o cpu (software)',
    )
    declare_gui = DeclareLaunchArgument(
        'gui', default_value='true', choices=['true', 'false'],
        description='Abrir gzclient (ventana de Gazebo)',
    )
    declare_muebles = DeclareLaunchArgument(
        'muebles', default_value='true', choices=['true', 'false'],
        description='Cargar el hospital con muebles (true) o solo la estructura (false)',
    )
    declare_rviz = DeclareLaunchArgument(
        'rviz', default_value='true', choices=['true', 'false'],
        description='Abrir RViz',
    )
    declare_rviz_config = DeclareLaunchArgument(
        'rviz_config', default_value=rviz_config,
        description='Archivo .rviz a abrir (sim_nav_launch.py pasa nav.rviz)',
    )
    declare_rviz_delay = DeclareLaunchArgument(
        'rviz_delay', default_value='5.0',
        description='Segundos tras arrancar el EKF (fin de la cadena) antes de abrir RViz',
    )
    declare_rviz_render = DeclareLaunchArgument(
        'rviz_render', default_value='gpu', choices=['gpu', 'cpu'],
        description='Renderizado de RViz: gpu (NVIDIA en WSL, por defecto) o cpu (software)',
    )

    limpieza_inicial = OpaqueFunction(function=limpiar_al_iniciar)
    limpieza_final = RegisterEventHandler(OnShutdown(on_shutdown=limpiar_al_cerrar))

    set_gazebo_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=(
            models_path + ':' +
            os.path.join(pkg_share, '..') + ':' +
            os.environ.get('GAZEBO_MODEL_PATH', '')
        ),
    )
    set_gazebo_resource_path = SetEnvironmentVariable(
        name='GAZEBO_RESOURCE_PATH',
        value=pkg_share + ':' + os.environ.get('GAZEBO_RESOURCE_PATH', ''),
    )

    is_gpu = LaunchConfigurationEquals('render', 'gpu')
    is_cpu = LaunchConfigurationEquals('render', 'cpu')
    render_env = [
        SetEnvironmentVariable('GALLIUM_DRIVER', 'd3d12', condition=is_gpu),
        SetEnvironmentVariable('MESA_D3D12_DEFAULT_ADAPTER_NAME', 'NVIDIA', condition=is_gpu),
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '0', condition=is_gpu),
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1', condition=is_cpu),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe', condition=is_cpu),
        LogInfo(msg=['[sim_launch] Render: ', LaunchConfiguration('render')]),
    ]

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'),
                         'launch', 'gazebo.launch.py')
        ),
        launch_arguments={'world': world_file, 'gui': LaunchConfiguration('gui')}.items(),
    )

    gazebo_ready_watcher = Node(
        package='Uvix_sim',
        executable='gazebo_ready_watcher',
        name='gazebo_ready_watcher',
        output='screen',
        parameters=[sim_params, {'timeout': 300.0, 'min_sim_time_sec': 0}],
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_xml}, sim_params],
    )

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_uvix',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'uvix',
            '-y', '0.5',
            '-z', '0.1',
        ],
        output='screen',
        parameters=[sim_params],
    )


    joint_state_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        parameters=[sim_params],
        output='screen',
    )

    diff_drive_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['uvix_base_controller'],
        parameters=[sim_params],
        output='screen',
    )

    cmd_vel_relay = Node(
        package='topic_tools',
        executable='relay',
        name='cmd_vel_relay',
        arguments=['/cmd_vel', '/uvix_base_controller/cmd_vel_unstamped'],
        parameters=[sim_params],
        output='screen',
    )

    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        parameters=[ekf_config, sim_params],
        output='screen',
    )

    range_fix = Node(
        package='Uvix_sim',
        executable='range_fix',
        name='range_fix',
        parameters=[sim_params],
        output='screen',
    )

    rviz_gpu = PythonExpression(["'", LaunchConfiguration('rviz_render'), "' == 'gpu'"])
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', LaunchConfiguration('rviz_config')],
        parameters=[sim_params],
        output='screen',
        additional_env={
            'GALLIUM_DRIVER': PythonExpression(["'d3d12' if ", rviz_gpu, " else 'llvmpipe'"]),
            'LIBGL_ALWAYS_SOFTWARE': PythonExpression(["'0' if ", rviz_gpu, " else '1'"]),
            'MESA_D3D12_DEFAULT_ADAPTER_NAME': 'NVIDIA',
        },
        condition=IfCondition(LaunchConfiguration('rviz')),
    )


    on_gazebo_ready = al_terminar_bien(
        gazebo_ready_watcher,
        '[sim_launch] /clock activo → RSP + spawn en 2 s',
        [TimerAction(period=2.0, actions=[robot_state_publisher, spawn_entity])],
    )

    on_robot_spawned = al_terminar_bien(
        spawn_entity,
        '[sim_launch] Robot en el mundo → joint_state_broadcaster',
        [joint_state_spawner],
    )

    on_joint_state_ready = al_terminar_bien(
        joint_state_spawner,
        '[sim_launch] joint_state_broadcaster activo → diff drive',
        [diff_drive_spawner],
    )

    on_diff_drive_ready = al_terminar_bien(
        diff_drive_spawner,
        '[sim_launch] Diff drive activo → relay, EKF y range_fix',
        [
            cmd_vel_relay,
            ekf_node,
            range_fix,
            LogInfo(msg=['[sim_launch] RViz abrirá en ', LaunchConfiguration('rviz_delay'), ' s'],
                    condition=IfCondition(LaunchConfiguration('rviz'))),
            TimerAction(period=LaunchConfiguration('rviz_delay'), actions=[
                LogInfo(msg='[sim_launch] Abriendo RViz',
                        condition=IfCondition(LaunchConfiguration('rviz'))),
                rviz_node,
            ]),
        ],
    )

    return LaunchDescription([
        declare_render,
        declare_gui,
        declare_muebles,
        declare_rviz,
        declare_rviz_config,
        declare_rviz_delay,
        declare_rviz_render,
        limpieza_inicial,
        limpieza_final,
        *render_env,
        set_gazebo_model_path,
        set_gazebo_resource_path,
        gazebo,
        gazebo_ready_watcher,
        on_gazebo_ready,
        on_robot_spawned,
        on_joint_state_ready,
        on_diff_drive_ready,
    ])

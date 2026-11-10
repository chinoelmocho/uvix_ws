# uvix_sim

Simulación de UVIX en **Gazebo Classic 11**. Levanta el mundo del hospital, mete el robot, activa
los controladores de `ros2_control`, fusiona odometría + IMU con un EKF y abre RViz. También trae
nodos auxiliares que usan los demás paquetes (patrulla, verificadores de arranque, corrección de
ultrasonidos).

## Lanzar

```bash
ros2 launch uvix_sim sim_launch.py
```

| Argumento | Valores | Defecto | Qué hace |
|---|---|---|---|
| `muebles` | `true` / `false` | `true` | `hospital2.world` (con muebles) o `hospital_empty.world` (solo paredes) |
| `gui` | `true` / `false` | `true` | Abrir la ventana de Gazebo (`gzclient`) |
| `render` | `gpu` / `cpu` | `gpu` | Render de Gazebo. `gpu` usa la NVIDIA en WSL (`d3d12`); `cpu` usa `llvmpipe` |
| `rviz` | `true` / `false` | `true` | Abrir RViz |
| `rviz_config` | ruta `.rviz` | `config/basic.rviz` | Configuración de RViz a cargar |
| `rviz_delay` | segundos | `5.0` | Espera tras arrancar el EKF antes de abrir RViz |
| `rviz_render` | `gpu` / `cpu` | `gpu` | Render de RViz |

## Cómo arranca (`sim_launch.py`)

El launch no lanza todo a la vez: cada paso espera a que el anterior **termine bien** (exit 0).
Si uno falla, se cierra todo el launch en vez de seguir a ciegas.

1. **Limpieza inicial** — mata restos de una simulación anterior (`gzserver` colgado, spawners, etc.).
2. **Gazebo** con el mundo elegido + `gazebo_ready_watcher`.
3. Cuando `/clock` está vivo → `robot_state_publisher` + `spawn_entity` (el robot aparece en `x=0, y=0.5`).
4. Robot en el mundo → `joint_state_broadcaster`.
5. Broadcaster activo → `uvix_base_controller` (diff drive).
6. Diff drive activo → `twist_mux`, EKF y `range_fix`.
7. Tras `rviz_delay` segundos → RViz.
8. **Limpieza al cerrar** — 8 s después de `Ctrl+C` mata con `-9` lo que siga vivo.

## Cadena de velocidades

```
Nav2 ──► cmd_vel_nav_out ─┐ (prioridad 10)
                          ├─► twist_mux ──► /uvix_base_controller/cmd_vel_unstamped
App  ──► cmd_vel ─────────┘ (prioridad 100, manda sobre Nav2)
```

Si ninguna fuente publica durante 0.5 s, `twist_mux` deja de mandar velocidad y el robot se para.

## Sensores simulados (`urdf/uvix.gazebo`)

| Sensor | Topic | Frecuencia | Frame |
|---|---|---|---|
| Lidar 2D | `/scan` | 10 Hz | `lidar_link` |
| IMU | `/imu` | 200 Hz | `imu_link` |
| Ultrasonidos (4) | `/ultrasonic/{front_left,front_right,rear_left,rear_right}` | 10 Hz | `us_*_link` |
| Cámara de profundidad inferior | `/camera_lower/...` (incluye `points`) | 15 Hz | `camera_lower_optical_link` |
| Cámara superior | `/camera_upper/...` | 30 Hz | `camera_upper_optical_link` |
| Cámara auxiliar frontal | `/camera_aux_front/...` | 30 Hz | `camera_aux_front_optical_link` |
| Cámara auxiliar derecha | `/camera_aux_right/...` | 30 Hz | `camera_aux_right_optical_link` |

## Controladores (`config/Uvix_controllers.yaml`)

| Controlador | Tipo | Notas |
|---|---|---|
| `joint_state_broadcaster` | `JointStateBroadcaster` | Publica `/joint_states` de ruedas y casters |
| `uvix_base_controller` | `DiffDriveController` | Separación 0.473 m, radio 0.085 m, 100 Hz. Publica `/uvix_base_controller/odom` **sin TF** (`enable_odom_tf: false`): el TF `odom → base_footprint` lo publica el EKF |

## EKF (`config/ekf.yaml`)

`robot_localization/ekf_node` en modo 2D a 50 Hz. Fusiona:

- `/uvix_base_controller/odom` → velocidad lineal `vx, vy` y angular `vyaw`.
- `/imu` → solo velocidad angular `vyaw`.

Publica `/odometry/filtered` y el TF `odom → base_footprint`.

---

## Nodos

### `gazebo_ready_watcher`

Espera a que Gazebo publique `/clock` (QoS `BEST_EFFORT`) con un tiempo simulado mayor a
`min_sim_time_sec`. Sale con **0** cuando está listo y con **1** si pasa el `timeout`. El launch
usa ese código de salida para decidir si hace el spawn del robot.

| Parámetro | Defecto | Descripción |
|---|---|---|
| `timeout` | `300.0` | Segundos máximos esperando a Gazebo |
| `min_sim_time_sec` | `0` | Tiempo simulado mínimo para considerar el mundo cargado |

Suscribe: `/clock` (`rosgraph_msgs/Clock`).

### `range_fix`

Gazebo publica `FLT_MAX` en los ultrasonidos cuando no detectan nada y `rclpy` no puede
deserializar ese valor. Este nodo lee el mensaje **en crudo (CDR)**, acota la lectura a
`[min_range, max_range]` y la vuelve a publicar para que el `RangeSensorLayer` de Nav2 la use.

| Parámetro | Defecto | Descripción |
|---|---|---|
| `sensors` | `[front_left, front_right, rear_left, rear_right]` | Ultrasonidos a corregir |
| `input_prefix` | `/ultrasonic/` | Prefijo de entrada |
| `output_prefix` | `/ultrasonic_nav/` | Prefijo de salida |

Suscribe: `/ultrasonic/<s>` · Publica: `/ultrasonic_nav/<s>` (`sensor_msgs/Range`).

### `slam_prereq_checker`

Lo usa `uvix_slam/slam_launch.py` antes de arrancar `slam_toolbox`. Comprueba que `/scan`, `/imu`,
`/odometry/filtered` y `/tf` publican con un *stamp* a menos de 0.5 s del tiempo simulado. Sale con
**0** si todo está sincronizado o con **1** tras el `timeout`, y al final imprime una tabla con el
estado de cada topic.

| Parámetro | Defecto | Descripción |
|---|---|---|
| `timeout` | `60.0` | Segundos máximos esperando |

### `patrol_node`

Patrulla autónoma **por cobertura** sobre el mapa de Nav2.

1. Divide `/map` en celdas de `cell_size` y descarta las que tienen poco espacio libre o caen en
   zonas excluidas.
2. Pide a Nav2 la ruta (`compute_path_to_pose`) a las `candidates_per_try` celdas no visitadas más
   cercanas y va a la de **ruta más corta** (`navigate_to_pose`).
3. Al llegar espera `dwell_time` y repite. Cuando visita todas, empieza una ronda nueva.
4. **Anti-atasco**: si no avanza `stuck_radius` en `stuck_time` segundos, retrocede (`backup`) y
   busca un punto de escape libre; tras `max_escapes` intentos salta la zona.
5. Omite goals cercanos que no se pueden alcanzar (bloqueados, Nav2 en recuperación o rodeo muy largo).

Publica `/patrol/markers` (`MarkerArray`) para RViz: verde = visitadas, naranja = pendientes,
gris = saltadas, rojo = zonas excluidas.

```bash
ros2 run uvix_sim patrol_node --ros-args -p cell_size:=1.5 -p dwell_time:=3.0
```

| Parámetro | Defecto | Descripción |
|---|---|---|
| `cell_size` | `1.0` | Tamaño de celda (m) |
| `visit_radius` | `1.5` | Radio para marcar una celda como visitada (m) |
| `dwell_time` | `5.0` | Espera en cada punto (s) |
| `goal_timeout` | `180.0` | Tiempo máximo por goal (s) |
| `exclusion_zones` | `[0.0]` | Lista plana `[xmin, ymin, xmax, ymax, ...]` de zonas prohibidas |
| `exclusion_names` | `['']` | Nombre de cada zona |
| `stuck_time` / `stuck_radius` | `5.0` / `0.15` | Criterio de atasco |
| `max_escapes` | `3` | Escapes antes de saltar la zona |

Suscribe: `/map`, `/global_costmap/costmap` · Acciones: `navigate_to_pose`,
`compute_path_to_pose`, `backup` · TF: `map → base_footprint`.

### `slam_points_node`

Amplía un mapa de `slam_toolbox` **punto por punto** a partir de un CSV
(`punto,x_m,y_m,yaw_rad` en el frame `map`). En cada punto: teletransporta el robot en Gazebo
(`gz model`), carga el grafo en esa pose, gira una vuelta completa y guarda el grafo y el mapa en
`output_map`. El mapa base nunca se sobrescribe.

| Parámetro | Defecto | Descripción |
|---|---|---|
| `points_file` | — | CSV con los puntos |
| `only` | `''` | Lista de puntos a usar, separados por coma (vacío = todos) |
| `base_map` / `output_map` | — | Mapa de entrada y de salida (sin extensión) |
| `map_to_world` | `[0.0, 0.5, 0.0]` | Transformación `map → world` de Gazebo (x, y, yaw) |
| `spin_speed` / `spin_turns` | `0.8` / `1.0` | Velocidad (rad/s) y vueltas de giro |

## Pendientes conocidos

- `patrol_node` menciona `config/patrol_params.yaml` en su docstring, pero ese archivo no existe:
  por ahora pasa los parámetros con `-p`.
- `slam_points_node` menciona `slam_extend_launch.py`, que tampoco existe: se lanza con `ros2 run`.

# uvix_nav

Navegación autónoma de UVIX con **Nav2**. El launch es una versión adaptada de
`nav2_bringup/navigation_launch.py`: arranca los servidores de navegación pero **no** el
`map_server` ni AMCL, porque el mapa y la localización (`map → odom`) los da `uvix_slam`.

## Lanzar

Lo normal es lanzarlo junto con SLAM:

```bash
ros2 launch uvix_slam slam_simulado_launch.py
```

O por separado (con SLAM ya corriendo):

```bash
ros2 launch uvix_nav uvix_navigation_launch.py \
    use_sim_time:=true \
    params_file:=$HOME/uvix_ws/install/uvix_nav/share/uvix_nav/config/nav2_params.yaml
```

| Argumento | Defecto | Descripción |
|---|---|---|
| `params_file` | params de `nav2_bringup` | **Pásale siempre** `config/nav2_params.yaml` de este paquete |
| `use_sim_time` | `false` | `true` en simulación |
| `autostart` | `true` | Activar los nodos lifecycle automáticamente |
| `namespace` | `''` | Namespace (para multi-robot) |
| `use_composition` | `False` | Cargar todo en un solo proceso contenedor |
| `use_respawn` | `False` | Reiniciar nodos que se caigan |
| `log_level` | `info` | Nivel de log |

## Nodos que arranca

| Nodo | Qué hace |
|---|---|
| `bt_navigator` | Árbol de comportamiento que coordina todo al recibir un goal (`navigate_to_pose`, `navigate_through_poses`) |
| `planner_server` | Ruta global con **NavFn** sobre el `global_costmap` |
| `smoother_server` | Suaviza la ruta global (`SimpleSmoother`) |
| `controller_server` | Sigue la ruta con **DWB** a 20 Hz y publica `cmd_vel_nav` |
| `velocity_smoother` | Limita aceleraciones: `cmd_vel_nav` → `cmd_vel_nav_out` |
| `behavior_server` | Recuperaciones: `spin`, `backup`, `drive_on_heading`, `wait`, `assisted_teleop` (publican en `cmd_vel_nav_out`) |
| `waypoint_follower` | Recorre una lista de puntos (`wait_at_waypoint`) |
| `lifecycle_manager_navigation` | Configura y activa todos los anteriores |

La salida final `cmd_vel_nav_out` entra a `twist_mux` (en `uvix_sim`), que da prioridad a la app
del móvil sobre Nav2.

## Configuración (`config/nav2_params.yaml`)

**Robot**
- Frame base: `base_footprint`. Odometría: `/odometry/filtered` (EKF).
- Velocidad máx.: 0.40 m/s lineal, 1.0 rad/s angular.

**Local costmap** (frame `odom`), huella 0.64 × 0.62 m:
- `voxel_layer` — obstáculos de `/scan` y de la nube de la cámara inferior `/camera_lower/points`
  (detecta cosas por debajo del lidar).
- `range_layer` — los 4 ultrasonidos ya corregidos (`/ultrasonic_nav/*`, ver `range_fix` en `uvix_sim`).
- `inflation_layer` — radio 0.60 m.

**Global costmap** (frame `map`), huella 0.58 × 0.58 m:
- `static_layer` (mapa de SLAM) + `obstacle_layer` (`/scan`) + `inflation_layer`.

## Enviar goals

- **RViz**: botón *2D Goal Pose* (usa `config/nav.rviz`).
- **Terminal**:

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 2.0, y: 1.0}, orientation: {w: 1.0}}}}"
```

- **Patrulla automática**: `ros2 run uvix_sim patrol_node`.

## Pendientes conocidos

- `map_server.yaml_filename` tiene una ruta absoluta (`/home/chino/...`). No afecta mientras se use
  con SLAM, pero hay que cambiarla si se lanza el `map_server`.
- Licencia: el launch deriva de Nav2 (Apache-2.0, © Intel Corporation); conserva su cabecera de
  copyright.

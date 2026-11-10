# uvix_slam

Mapeo y localización de UVIX con **slam_toolbox**. Necesita la simulación (`uvix_sim`) corriendo.

## Launch

### `slam_launch.py` — SLAM solo

Antes de arrancar `slam_toolbox` lanza `uvix_sim/slam_prereq_checker`, que espera a que `/scan`,
`/imu`, `/odometry/filtered` y `/tf` estén sincronizados con el tiempo simulado. Si el checker falla,
SLAM no arranca y te dice qué topic falta.

```bash
SLAM=~/uvix_ws/install/uvix_slam/share/uvix_slam/config/slam_params.yaml

ros2 launch uvix_slam slam_launch.py slam_params:=$SLAM                                   # mapa nuevo
ros2 launch uvix_slam slam_launch.py slam_params:=$SLAM map:=PASILLO                      # ampliar un mapa
ros2 launch uvix_slam slam_launch.py slam_params:=$SLAM mode:=localization map:=PASILLO   # solo localizarse
```

| Argumento | Defecto | Descripción |
|---|---|---|
| `slam_params` | ver *Pendientes* | YAML de parámetros de `slam_toolbox` |
| `mode` | `mapping` | `mapping` (crear/ampliar) o `localization` (solo localizarse en un mapa existente) |
| `map` | `''` | Nombre del mapa en `~/uvix_ws/src/uvix_sim/maps/` o ruta absoluta, sin extensión. Vacío = mapa nuevo |
| `start_pose` | `''` | `"x y yaw"` inicial en el mapa cargado. Vacío = pose del *dock* guardada en el mapa |
| `prereq_timeout` | `120.0` | Segundos máximos esperando sensores + EKF |

Según el modo usa `async_slam_toolbox_node` (mapping) o `localization_slam_toolbox_node`
(localization).

### `slam_simulado_launch.py` — SLAM + Nav2

Lanza `async_slam_toolbox_node` con `config/slam_params.yaml` e incluye
`uvix_nav/uvix_navigation_launch.py`. Es la forma rápida de **mapear y navegar a la vez**.

```bash
ros2 launch uvix_slam slam_simulado_launch.py
```

## Parámetros principales (`config/slam_params.yaml`)

| Parámetro | Valor | Significado |
|---|---|---|
| `odom_frame` / `map_frame` / `base_frame` | `odom` / `map` / `base_footprint` | Frames del robot |
| `scan_topic` | `/scan` | Lidar |
| `resolution` | `0.05` | 5 cm por celda |
| `max_laser_range` | `25.0` | Alcance máximo usado del lidar (m) |
| `minimum_travel_distance` / `heading` | `0.3` / `0.15` | Movimiento mínimo para procesar un nuevo scan |
| `map_update_interval` | `5.0` | Cada cuánto se publica `/map` (s) |
| `do_loop_closing` | `true` | Cierre de lazos para corregir la deriva |

Publica: `/map`, TF `map → odom`.

## Guardar un mapa

Con SLAM corriendo:

```bash
NOMBRE=mi_mapa
# Imagen para Nav2 (.pgm + .yaml)
ros2 run nav2_map_server map_saver_cli -f ~/uvix_ws/src/uvix_sim/maps/$NOMBRE
# Grafo para seguir ampliándolo con slam_toolbox (.posegraph + .data)
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
    "{filename: '$HOME/uvix_ws/src/uvix_sim/maps/$NOMBRE'}"
```

Los `.posegraph` y `.data` no se suben a git (pesan demasiado).

## Pendientes conocidos

- El valor por defecto de `slam_params` en `slam_launch.py` apunta a
  `uvix_sim/config/slam_params.yaml`, que ya no existe desde que el SLAM se movió a este paquete.
  Mientras se corrige, pasa `slam_params:=` como en los ejemplos.
- La carpeta de mapas está fija en `~/uvix_ws/src/uvix_sim/maps`.

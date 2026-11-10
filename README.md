# UVIX — Robot asistencial médico (ROS 2 Humble)

Workspace de ROS 2 para **UVIX**, un robot móvil diferencial pensado para entornos hospitalarios.
Incluye la simulación en Gazebo Classic, SLAM, navegación con Nav2, exploración autónoma,
teleoperación con joystick y la interfaz de hardware `ros2_control` para el robot real (Jetson).

![Gazebo](images/gazebo.jpg)

---

## Contenido

| Paquete | Tipo | Descripción |
|---|---|---|
| [`uvix_sim`](src/uvix_sim) | ament_python | Simulación principal: URDF/xacro, mundos de hospital, controladores, SLAM, Nav2, EKF, twist_mux, patrullaje. |
| [`uvix_description`](src/uvix_description) | ament_cmake | Descripción del robot para `ros2_control` con el hardware real (`display.launch.py`). |
| [`uvix_hadware`](src/uvix_hadware) | ament_cmake (C++) | Plugin `hardware_interface::SystemInterface` (`uvix_hadware/UvixSystem`). Aquí se conectan los drivers/SDKs del robot real. |
| [`joy_bridge`](src/joy_bridge) | ament_python | Recibe el joystick por UDP (puerto 5005, JSON) y lo publica en `/joy`. |
| [`m-explore-ros2`](src/m-explore-ros2) | externo | `explore_lite` para exploración autónoma de fronteras. |
| [`bobert_sim`](src/bobert_sim) | ament_python | Robot de pruebas (Bobert) usado como referencia. |

```
uvix_ws/
├── src/
│   ├── uvix_sim/          # simulación, config, launch, mapas, mundos
│   ├── uvix_description/  # URDF para el robot real + ros2_control
│   ├── uvix_hadware/      # plugin C++ de hardware
│   ├── joy_bridge/        # joystick por UDP
│   ├── m-explore-ros2/    # explore_lite
│   └── bobert_sim/        # robot de referencia
├── .vscode/               # configuración compartida del editor
├── README.md
└── .gitignore / .gitattributes
```

---

## Requisitos

- Ubuntu 22.04 + **ROS 2 Humble** (en PC y en Jetson)
- Gazebo Classic 11 (solo para simulación)

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions python3-rosdep
sudo rosdep init   # solo la primera vez
rosdep update
```

## Instalación

```bash
git clone https://github.com/chinoelmocho/uvix_ws.git ~/uvix_ws
cd ~/uvix_ws
git checkout slam-nav

source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

> Consejo: añade `source ~/uvix_ws/install/setup.bash` al final de tu `~/.bashrc`.

### Compilar en la Jetson (sin simulación)

En el robot real no hace falta compilar la simulación de referencia:

```bash
colcon build --symlink-install --packages-skip bobert_sim
```

---

## Uso

### 1. Simulación

```bash
ros2 launch uvix_sim sim_launch.py
```

| Argumento | Valores | Por defecto | Descripción |
|---|---|---|---|
| `muebles` | `true` / `false` | `true` | `hospital2.world` con muebles o `hospital_empty.world` |
| `gui` | `true` / `false` | `true` | Abrir la interfaz de Gazebo |
| `render` | `gpu` / `cpu` | `gpu` | Render de Gazebo (usa `cpu` si la GPU da problemas en WSL) |
| `rviz` | `true` / `false` | `true` | Abrir RViz |
| `rviz_render` | `gpu` / `cpu` | `gpu` | Render de RViz |

Ejemplo ligero: `ros2 launch uvix_sim sim_launch.py muebles:=false gui:=false render:=cpu`

### 2. SLAM (con la simulación ya abierta)

```bash
ros2 launch uvix_sim slam_launch.py                                   # mapa nuevo
ros2 launch uvix_sim slam_launch.py map:=PASILLO                      # ampliar un mapa
ros2 launch uvix_sim slam_launch.py mode:=localization map:=PASILLO   # solo localizarse
```

Guardar el mapa (imagen `.pgm/.yaml` + pose graph `.posegraph/.data`):

```bash
ros2 run nav2_map_server map_saver_cli -f ~/uvix_ws/src/uvix_sim/maps/<nombre>
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
    "{filename: '$HOME/uvix_ws/src/uvix_sim/maps/<nombre>'}"
```

### 3. SLAM + Nav2

```bash
ros2 launch uvix_sim slam_simulado_launch.py
```

### 4. Robot real (ros2_control)

```bash
ros2 launch uvix_description display.launch.py
```

### 5. Joystick por UDP

```bash
ros2 run joy_bridge joy_udp
```

Espera paquetes JSON en el puerto UDP **5005** con el formato `{"axes": [...], "buttons": [...]}`.

### Nodos útiles de `uvix_sim`

`patrol_node`, `slam_points_node`, `slam_prereq_checker`, `gazebo_ready_watcher`, `range_fix`
→ `ros2 run uvix_sim <nodo>`

---

## Mapas

Los mapas pesados de SLAM (`*.posegraph`, `*.data`) **no se suben a git**: GitHub rechaza archivos
de más de 100 MB. En el repositorio solo van `*.pgm` y `*.yaml`.

Para llevar un mapa completo a la Jetson cópialo aparte:

```bash
scp ~/uvix_ws/src/uvix_sim/maps/<nombre>.* usuario@IP_JETSON:~/uvix_ws/src/uvix_sim/maps/
```

---

## Flujo de trabajo con git

- `main` — versión estable.
- `slam-nav` — rama de desarrollo actual.
- Ramas de trabajo: `feat/<tema>`, `fix/<tema>`. Se fusionan a `slam-nav` con un Pull Request.

```bash
git checkout slam-nav && git pull
git checkout -b feat/mi-cambio
# ... cambios ...
git add -A && git commit -m "feat(uvix_hadware): leer encoders"
git push -u origin feat/mi-cambio
```

Mensajes de commit cortos con prefijo: `feat`, `fix`, `docs`, `config`, `refactor`.

> Usa **el git de Ubuntu (WSL)**, no Git de Windows: este último marca como modificados archivos
> que no cambiaron (permisos y finales de línea).

---

## Desarrollo con VS Code

Abre la carpeta desde WSL (`code ~/uvix_ws`) e instala las extensiones recomendadas
(VS Code las sugiere solo). Tareas disponibles en `Ctrl+Shift+P → Tasks: Run Task`:

- **colcon: build** (`Ctrl+Shift+B`) — compila todo y genera `compile_commands.json` para IntelliSense de C++.
- **colcon: build paquete** — compila solo el paquete que elijas.
- **colcon: clean** — borra `build/`, `install/` y `log/`.
- **sim: lanzar simulación** — `ros2 launch uvix_sim sim_launch.py`.

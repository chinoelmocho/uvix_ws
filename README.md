# UVIX Robot asistencial para adultos mayores (ROS 2 Humble)

UVIX es un robot móvil diferencial pensado para acompañar a adultos mayores en hospitales y
residencias. Este workspace contiene la simulación en Gazebo, el SLAM, la navegación autónoma con
Nav2 y la interfaz `ros2_control` para el robot real.

<p align="center">
  <img src="images/uvix_navegacion.gif" alt="UVIX navegando de forma autónoma en el hospital simulado" width="800">
</p>

<p align="center">
  <img src="images/gazebo.jpg" alt="UVIX en Gazebo" width="400">
  <img src="images/rviz.png" alt="UVIX en RViz" width="400">
</p>

---

## Paquetes

Cada paquete tiene su propio README con el detalle de sus nodos, topics y parámetros.

| Paquete | Tipo | Qué hace |
|---|---|---|
| [`uvix_sim`](src/uvix_sim/README.md) | ament_python | Simulación en Gazebo: modelo del robot, mundos de hospital, controladores, EKF, `twist_mux` y nodos auxiliares (patrulla, watchers). |
| [`uvix_slam`](src/uvix_slam/README.md) | ament_python | Mapeo y localización con `slam_toolbox`. |
| [`uvix_nav`](src/uvix_nav/README.md) | ament_python | Navegación autónoma con Nav2 (planner, controlador DWB, costmaps). |
| [`uvix_description`](src/uvix_description/README.md) | ament_cmake | Descripción del robot real con `ros2_control`. |
| [`uvix_hadware`](src/uvix_hadware/README.md) | ament_cmake (C++) | Plugin `hardware_interface::SystemInterface` para los motores del robot real. |
| [`m-explore-ros2`](src/m-explore-ros2/README.md) | externo | `explore_lite`: exploración autónoma de fronteras. |

---

## Requisitos

| | Versión |
|---|---|
| Sistema operativo | Ubuntu 22.04 (nativo o WSL2) |
| ROS 2 | Humble Hawksbill |
| Simulador | Gazebo Classic 11 |
| Python | 3.10 |

### 1. Instalar ROS 2 Humble

Si todavía no tienes ROS 2, sigue la guía oficial:
<https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html> (instala `ros-humble-desktop`).

### 2. Herramientas de compilación

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  python3-numpy \
  git jq
```

### 3. Dependencias de ROS del proyecto

```bash
sudo apt install -y \
  ros-humble-xacro \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-ros2-control \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-controller-manager \
  ros-humble-twist-mux \
  ros-humble-robot-localization \
  ros-humble-slam-toolbox \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-image-geometry \
  ros-humble-tf2-geometry-msgs
```

### 4. Inicializar rosdep

```bash
sudo rosdep init
rosdep update
```


## Flujo de trabajo con git

| Rama | Para qué |
|---|---|
| `main` | Versión **estable y protegida**. Solo entra código desde `develop` con un Pull Request. |
| `develop` | Integración: aquí se juntan y prueban las funciones nuevas. |
| `feat/<tema>`, `fix/<tema>`, `docs/<tema>` | Una rama por tarea (un issue). Sale de `develop` y vuelve a `develop` con un PR. |

```bash
git checkout develop && git pull
git checkout -b feat/mi-cambio
# ... cambios ...
git add <archivos>
git commit -m "feat(uvix_nav): waypoints de habitaciones"
git push -u origin feat/mi-cambio
# En GitHub: Pull Request feat/mi-cambio → develop, con "Closes #<issue>" en la descripción
```

Prefijos de commit: `feat`, `fix`, `docs`, `config`, `refactor`, `test`, `chore`.

> Usa **el git de Ubuntu (WSL)**, no Git de Windows: este último marca como modificados archivos
> que no cambiaron (permisos y finales de línea).

---

## Desarrollo con VS Code

Abre la carpeta desde WSL (`code ~/uvix_ws`) e instala las extensiones recomendadas (VS Code las
sugiere solo). Tareas en `Ctrl+Shift+P → Tasks: Run Task`:

- **colcon: build** (`Ctrl+Shift+B`) — compila todo y genera `compile_commands.json` para IntelliSense de C++.
- **colcon: build paquete** — compila solo el paquete que elijas.
- **colcon: clean** — borra `build/`, `install/` y `log/`.
- **sim: lanzar simulación** — `ros2 launch uvix_sim sim_launch.py`.

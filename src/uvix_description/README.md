# uvix_description

Descripción de UVIX para el **robot real** con `ros2_control`. A diferencia de `uvix_sim` (que usa
`gazebo_ros2_control`), aquí el URDF carga el plugin de hardware propio `uvix_hadware/UvixSystem`, y
el `controller_manager` corre como un nodo normal (`ros2_control_node`) con reloj real.

Reutiliza de `uvix_sim` los meshes (`package://uvix_sim/meshes/...`) y `materials.xacro`.

## Lanzar

```bash
ros2 launch uvix_description display.launch.py
```

## Qué arranca `display.launch.py`

| Nodo | Qué hace |
|---|---|
| `robot_state_publisher` | Procesa `urdf/uvix.xacro` y publica `/robot_description` y los TF fijos |
| `ros2_control_node` (`controller_manager`) | Carga el plugin `UvixSystem` y ejecuta el ciclo `read → update → write` a 100 Hz |
| `spawner` | Carga y activa `joint_state_broadcaster` y `uvix_base_controller` (espera hasta 60 s al `controller_manager`) |
| `rviz2` | Visualización con frame fijo `odom` |

Todos con `use_sim_time: false`.

## Bloque `ros2_control` del URDF

```xml
<ros2_control name="UvixSystem" type="system">
  <hardware>
    <plugin>uvix_hadware/UvixSystem</plugin>
  </hardware>
  <joint name="base_link_wheel_right_joint"> velocity (cmd, ±10 rad/s) · position, velocity (estado)
  <joint name="base_link_wheel_left_joint">  velocity (cmd, ±10 rad/s) · position, velocity (estado)
</ros2_control>
```

## Controladores (`config/Uvix_controllers.yaml`)

Mismo `diff_drive_controller` que en simulación (separación 0.473 m, radio 0.085 m), con estas
diferencias para el robot real:

| | Robot real | Simulación |
|---|---|---|
| `enable_odom_tf` | `true` (no hay EKF todavía) | `false` (el TF lo da el EKF) |
| Velocidad lineal máx. | 1.5 m/s | 4.0 m/s |
| Velocidad angular máx. | 2.0 rad/s | 4.0 rad/s |
| Aceleración máx. | 1.0 | 2.0 |

## Probar sin hardware

`UvixSystem` hoy es un **modelo ideal** (la velocidad medida es igual a la comandada), así que
puedes mover el robot en RViz sin motores:

```bash
ros2 topic pub -r 10 /uvix_base_controller/cmd_vel_unstamped geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.3}}"
```

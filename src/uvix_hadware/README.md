# uvix_hadware

Plugin C++ de **`ros2_control`** para las ruedas de UVIX. Implementa
`hardware_interface::SystemInterface` y se registra con pluginlib como
`uvix_hadware/UvixSystem` (clase `uvix_hardware::UvixSystem`). Lo carga el `controller_manager`
desde el bloque `<ros2_control>` del URDF de `uvix_description`.

Aquí es donde se conectarán los drivers/SDK de los motores y encoders reales.

> El nombre del paquete tiene una errata (`hadware`); se corregirá en un cambio aparte porque afecta
> al URDF y a `uvix_description`.

## Interfaces que exporta

| Joint | Command interface | State interfaces |
|---|---|---|
| `base_link_wheel_left_joint` | `velocity` (rad/s) | `position` (rad), `velocity` (rad/s) |
| `base_link_wheel_right_joint` | `velocity` (rad/s) | `position` (rad), `velocity` (rad/s) |

El `diff_drive_controller` escribe en las *command interfaces* y lee las *state interfaces* para
calcular la odometría.

## Ciclo de vida

| Callback | Qué hace ahora |
|---|---|
| `on_init` | Lee la info del URDF (llama a la clase base) |
| `on_configure` | Pone a cero comandos, velocidades y posiciones |
| `on_activate` | Para todo y marca el sistema como activo |
| `on_deactivate` | Para todo y lo marca inactivo |
| `read(dt)` | Velocidad medida = última velocidad aplicada; integra la posición `pos += vel·dt`. Devuelve `ERROR` si `dt` no es válido |
| `write()` | Si está activo, aplica los comandos. Devuelve `ERROR` y para si llega un `NaN`/`inf` |

Es un **modelo ideal** (sin inercia ni ruido) para probar la cadena `ros2_control` sin el robot.

## Cómo pasar al hardware real

1. `on_configure`: abrir la comunicación con la controladora de motores (serie/CAN/SDK).
2. `on_activate` / `on_deactivate`: habilitar o deshabilitar los drivers.
3. `read`: leer los encoders y convertir ticks → rad y rad/s.
4. `write`: convertir rad/s → la unidad del driver y enviar.
5. Leer puerto, baudios, ticks por vuelta, etc. desde `<param>` en el URDF
   (`info_.hardware_parameters`) en lugar de dejarlos fijos en el código.

## Compilar

```bash
colcon build --symlink-install --packages-select uvix_hadware
```

Dependencias: `hardware_interface`, `pluginlib`, `rclcpp`, `rclcpp_lifecycle` (C++17).

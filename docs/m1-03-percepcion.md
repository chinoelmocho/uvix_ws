# M1-03: percepción visual (contratos y fixtures)

## Entradas de cámara

| Entrada | Tipo | Uso |
|---|---|---|
| `/camera/color/image_raw` | `sensor_msgs/msg/Image` | Imagen y timestamp de adquisición. |
| `/camera/color/camera_info` | `sensor_msgs/msg/CameraInfo` | Intrínsecos, distorsión y frame óptico. |
| `/camera/depth/points` | `sensor_msgs/msg/PointCloud2` (opcional) | Geometría 3D cuando la fuente y TF sean válidos. |

Un bbox usa píxeles de la imagen indicada por `camera_id` y el `header`. No se infiere profundidad de un bbox. Las poses declaran `COORDINATES_PIXELS_2D` o `COORDINATES_METERS_3D`; una articulación ausente lleva `present=false` y visibilidad cero.

## Topics

| Topic | Tipo | Asociación |
|---|---|---|
| `/perception/people` | `uvix_interfaces/msg/PeopleObservations` | `track_id` temporal, `camera_id`, `source_id`, `tracker_session_id`, bbox, calidad y posición 3D opcional. |
| `/perception/body_poses` | `uvix_interfaces/msg/BodyPoseArray` | `track_id`, articulaciones, frame y espacio de coordenadas. |
| `/perception/face_matches` | `uvix_interfaces/msg/FaceMatchArray` | `track_id` y resultado `CANDIDATE`, `KNOWN`, `UNKNOWN` o `INSUFFICIENT_QUALITY`. No contiene permisos. |
| `/perception/gestures` | `uvix_interfaces/msg/GestureEvent` | Evento final con `event_id`, track/session, calidad, persistencia y vencimiento. |

`person_id` puede quedar vacío. Las fuentes no asignan la identidad mirando la cara más cercana ni convierten una cara conocida en autorización. Las matrices y eventos llevan `valid_for=1 s`; los consumidores comprueban `header.stamp + valid_for` y no conservan datos vencidos. Los topics de fixture usan QoS confiable; el de eventos también retiene el último evento para suscriptores tardíos, que deben descartar eventos vencidos.

## Gestos iniciales y duplicados

Vocabulario: `HAND_RAISED`, `WAVE`, `HELP_SIGN`. Se requieren 0.5 s de persistencia. El evento se publica una vez mientras el gesto siga presente; para emitirlo de nuevo debe desaparecer y volver a detectarse. La clave de deduplicación es `(tracker_session_id, track_id, gesture)`.

## Proveedores sintéticos

`synthetic_perception.launch.py` recorre `known`, `unknown`, `partial_pose`, `gesture`, `low_quality` y `empty`; se puede seleccionar un caso con `scenario:=...`. La salida se identifica como `synthetic_fixture`. Los fixtures validan los contratos y la caducidad de observaciones; no son inferencias de visión.

```bash
ros2 launch uvix_perception synthetic_perception.launch.py scenario:=all
ros2 topic echo /perception/people
ros2 topic echo /perception/body_poses
ros2 topic echo /perception/face_matches
ros2 topic echo /perception/gestures
```

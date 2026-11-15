# M1 — Interfaces de UVIX

Guía de cierre de la tarea de interfaces del hito **M1 (Base para encargos)**.
Recoge el catálogo de capacidades, la tabla de identificadores, los requisitos de
los futuros modelos y la evidencia de verificación.

Las explicaciones de cada mensaje **no se repiten aquí**: están en el
[README de `uvix_interfaces`](../src/uvix_interfaces/README.md).

| Documento | Contenido |
|---|---|
| [README de `uvix_interfaces`](../src/uvix_interfaces/README.md) | Orígenes y prioridades, flujo de una orden, identidad, diagramas, ejemplos YAML, anomalías |
| [`m1_capacidades.yaml`](m1_capacidades.yaml) | Catálogo de las seis capacidades (fuente de verdad de este documento) |
| Este documento | Resumen del catálogo, identificadores, requisitos de modelos, evidencia |

---

## 1. Interfaces disponibles

`uvix_interfaces` genera **19 interfaces**: 12 mensajes, 5 servicios y 2 acciones.
El inventario completo y los topics sugeridos están en el README
([Inventario](../src/uvix_interfaces/README.md#8-inventario-de-interfaces)).

Para entender el diseño, conviene leer en este orden:

1. [Idea de funcionamiento](../src/uvix_interfaces/README.md#1-idea-de-funcionamiento): orígenes, prioridades, permisos, catálogo de misiones.
2. [Flujo de una orden](../src/uvix_interfaces/README.md#2-flujo-de-una-orden).
3. [Identificación de personas](../src/uvix_interfaces/README.md#3-identificación-de-personas): `person_id`, `identity_status` y `role` como tres datos distintos.
4. [Ejemplos YAML](../src/uvix_interfaces/README.md#6-ejemplos-yaml).

---

## 2. Catálogo de capacidades

Detalle completo (entradas, QoS, parámetros, todos los fallos) en
[`m1_capacidades.yaml`](m1_capacidades.yaml). Resumen:

| Capacidad | Salida principal (nombre ROS · tipo) | Responsable | Consumidores | Timeout | Alcance M1 |
|---|---|---|---|---|---|
| **Personas** (detección y seguimiento) | `/uvix/perception/person_tracks` · `vision_msgs/Detection3DArray` *(propuesta)* | `uvix_perception` | rostros, posturas, interacción, manager | 1.0 s | simulado |
| **Rostros** (identidad) | `/uvix/get_request_identity` · `GetRequestIdentity` | `uvix_perception` (`identity_manager`) | manager, interpreter | 2.0 s | solo contrato |
| **Posturas / gestos** | `/uvix/register_mission` (caída) · `/uvix/user_command` (gesto) | `uvix_perception` | manager, interpreter | 2.0 s | simulado (gesto fuera, M7) |
| **Voz de entrada** | `/uvix/user_command` · `UserCommand` | `uvix_interaction` (`asr_node`) | interpreter, rostros | 10.0 s | simulado (texto) |
| **Voz de salida** | `/uvix/speak` · `SpeakText` (action) | `uvix_interaction` (`tts_node`) | interpreter, manager, ejecutor | 15.0 s | simulado (log) |
| **Personas / permisos** | `/uvix/get_person` · `GetPerson` | servicio local de datos (`people_registry`) | manager, interpreter, interacción | 1.0 s | implementado (perfiles ficticios) |

Todas las capacidades tienen versión de contrato **0.1.0**. El responsable
humano de cada una está **por asignar** (plan, sección 10).

**Fallos comunes.** Si una capacidad no responde dentro de su timeout, el
consumidor **no asume** un valor por defecto favorable: rechaza la orden o publica
`SystemStatus DEGRADED` con el componente en `failed_components`. Ejemplos: el
manager nunca asume un rol si `GetPerson` no responde; nunca asume identidad
verificada si `GetRequestIdentity` no responde.

> **Pendiente de contrato:** la salida de *Personas* usa el estándar
> `vision_msgs/Detection3DArray` (el plan pide preferir interfaces estándar). Falta
> añadir `vision_msgs` como dependencia y confirmar que `id` transporta el
> `track_id`.

---

## 3. Identificadores

| ID | Quién lo crea | Qué identifica | Cuándo cambia | Cuándo puede estar vacío | Formato |
|---|---|---|---|---|---|
| `request_id` | Quien emite el `UserCommand` (ASR, entrada de texto, detector de gestos) | **Un enunciado o petición** concreta | Nuevo en **cada** enunciado, incluidas las respuestas de aclaración | Nunca en `UserCommand`. En `MissionSpec`, vacío si el origen es `DETECTION`, `SCHEDULE` o `SYSTEM` | UUID v4 |
| `parent_request_id` | Emisor del `UserCommand` (con el contexto de sesión del interpreter) | La orden que esta respuesta aclara | Igual al `request_id` raíz durante toda la aclaración | Vacío si es una orden nueva | UUID v4 |
| `session_id` | `command_interpreter` / `uvix_interaction` al abrir una conversación | **Una conversación** (varios turnos con la misma persona) | Nueva al iniciar conversación; termina por despedida, timeout o cambio de interlocutor | Vacío si es una orden suelta sin conversación | UUID v4 |
| `utterance_id` | ASR | El audio de un enunciado (para depurar ASR) | Uno por enunciado de voz | Vacío si la entrada no fue voz | UUID v4 |
| `event_id` | Cada nodo que publica `CommandEvent` | Una entrada de la bitácora | Uno por evento | Nunca | UUID v4 |
| `mission_id` | **Solo** `mission_manager` al aceptar `RegisterMission` | Una misión | Nunca cambia durante la vida de la misión (pausa y reanudación conservan el mismo) | Vacío en la petición de registro y si fue rechazada | `mis-` + UUID v4 |
| `alert_id` | Quien publica el `Alert` | Una alerta (y su confirmación con `AckAlert`) | Uno por alerta; una alerta repetida por falta de confirmación **conserva** su `alert_id` | Nunca | `alt-` + UUID v4 |
| `person_id` | Registro de personas (al dar de alta) | **El registro persistente** de una persona | Nunca; es estable entre sesiones y reinicios | Vacío cuando no se reconoce a nadie (`IDENTITY_UNKNOWN`) | Texto estable, p. ej. `staff_juan` |
| `track_id` | Tracker de personas | **Un seguimiento visual temporal** | Nuevo cada vez que se crea un track; nunca se reutiliza | Vacío si la orden no tiene seguimiento visual (texto, prueba) | `track-` + contador o UUID |

### 3.1 `person_id` frente a `track_id`

- `person_id` = **quién es** (registro persistente). Lo asigna el registro de personas.
- `track_id` = **qué cuerpo se está siguiendo ahora** (temporal). Lo asigna el tracker.
- Un `track_id` **no identifica** a nadie. La relación `track_id → person_id`
  solo existe dentro de una `IdentityVerification` y vale hasta su `valid_until`.

### 3.2 Persona perdida y recuperada

| Situación | `track_id` | Identidad |
|---|---|---|
| Oclusión breve (menor que `max_age` del tracker, p. ej. 1–2 s) | **Se conserva** | La verificación anterior sigue valiendo hasta `valid_until` |
| Perdida más que `max_age` y vuelve a aparecer | **Nuevo `track_id`** (el anterior se cierra y no se reutiliza) | Hay que **volver a verificar**; no se hereda la identidad del track viejo |
| Mismo `person_id` en dos tracks a la vez | — | Conflicto: ambas verificaciones bajan a `IDENTITY_CANDIDATE` hasta resolverlo |

Así se evita que alguien que entra en el campo visual "herede" la identidad de la
persona que acaba de salir.

### 3.3 Respuesta a una aclaración

Ejemplo: Juan dice *"dale las vitaminas a María"* y el robot pregunta *"¿cuál vitamina?"*.

| Paso | Mensaje | `request_id` | `parent_request_id` | `session_id` |
|---|---|---|---|---|
| 1. Orden | `UserCommand` "dale las vitaminas a María" | `R1` | vacío | `S1` |
| 2. Pregunta | `ClarificationRequest` | `R1` (la orden que se aclara) | — | `S1` |
| 3. Respuesta | `UserCommand` "la C" | `R2` (**nuevo**) | `R1` | `S1` (**el mismo**) |
| 4. Registro | `RegisterMission` | `MissionSpec.request_id = R1` | — | — |

Reglas:

1. **Nuevo `request_id`, mismo `session_id`, `parent_request_id` = orden raíz.**
   Si hay varias preguntas seguidas, todas las respuestas apuntan a la **raíz** (`R1`),
   no a la respuesta anterior.
2. La misión usa el `request_id` **raíz** (`R1`): así la bitácora `CommandEvent`,
   la deduplicación (`CODE_DUPLICATE_REQUEST`) y la verificación de identidad
   giran en torno a un solo ID.
3. **Misma persona:** el interpreter solo acepta la respuesta si
   `GetRequestIdentity(R2).person_id == GetRequestIdentity(R1).person_id`. Si responde
   otra persona, se ignora la respuesta y se repite la pregunta.
4. **Caducidad:** `ClarificationRequest.timeout_s` (20 s) debe ser menor que
   `verification_ttl_s` (60 s). Si la verificación de `R1` caduca antes de
   registrar, el manager responde `CODE_IDENTITY_EXPIRED` y el robot pide repetir
   la orden.

---

## 4. Requisitos de los futuros modelos

Ningún modelo está elegido ni probado todavía. Para cada uno se deja
**modelo: pendiente** con los requisitos que debe cumplir el candidato.

**Requisitos comunes a todos:**

- **Ejecución local, sin nube.** Imágenes, audio y biometría de pacientes no salen
  del robot.
- **Licencia:** código y pesos con licencia que permita uso, modificación y
  despliegue en el robot (preferible Apache-2.0, MIT o BSD). Se descartan licencias
  "solo no comercial" o "solo investigación" si impiden el piloto, y modelos sin
  licencia explícita para los **pesos**. Registrar también la licencia del dataset
  de entrenamiento.
- **Recursos de referencia** (máquina de desarrollo; el hardware del robot está por
  definir): CPU AMD Ryzen 7 5800H, 15 GB RAM, sin depender de GPU. Si se usa GPU,
  documentar cuál y medir también solo con CPU.
- **Evaluación con datos propios:** un conjunto de prueba grabado en el entorno
  (con consentimiento) además de cualquier benchmark público. Los umbrales de abajo
  son **propuestas iniciales** y se acuerdan con el hardware (plan, sección 8).
- Aprobar una prueba con identidad inyectada **no** valida un modelo (plan, sección 11).

| Capacidad | Modelo | Datos de entrada esperados | Salida esperada | Recursos | Criterios de evaluación (propuesta) |
|---|---|---|---|---|---|
| Personas | pendiente | RGB 640×480 a ≥10 Hz; profundidad opcional; interiores, iluminación variable, sillas de ruedas y andadores | Caja 2D/3D en `frame_id` de la cámara + `track_id` estable | ≥10 FPS en CPU; ≤1.5 GB RAM | Recall de personas ≥95 % a ≤4 m; cambios de ID por oclusión ≤1 cada 5 min por persona; latencia ≤150 ms |
| Rostros | pendiente | Recorte de rostro desde el track; 5–10 fotos de alta por persona registrada; gafas, mascarilla, perfil parcial | `person_id` + confianza + `IDENTITY_*` | ≤300 ms por rostro en CPU; ≤1 GB RAM | Rechazo de no registrados (FAR) ≤1 %; aceptación de registrados (TAR) ≥90 % con FAR 1 %; la confianza debe estar calibrada (permite el umbral `min_confidence_verified`) |
| Posturas / caídas | pendiente | Secuencia de esqueleto o RGB por track, ventana de 1–3 s | Evento de caída con `track_id`, posición y confianza | ≥10 FPS en CPU junto con el detector | Recall de caídas ≥90 % en escenas simuladas y actuadas; falsas alarmas ≤1 por hora; latencia de detección ≤3 s |
| Gestos (M7) | pendiente | Esqueleto por track | Gesto "solicitar atención" + `track_id` | Compartido con posturas | Precisión ≥90 %; una sola solicitud por ventana de repetición |
| Voz de entrada | pendiente | Audio 16 kHz mono, español (Ecuador), ruido de pasillo, voces de adultos mayores | Texto + idioma + confianza + fin de enunciado | Factor de tiempo real ≤0.5 en CPU; ≤2 GB RAM | WER ≤15 % en el vocabulario de órdenes; detección de la frase de llamada ≥95 % con ≤1 falsa activación por hora |
| Voz de salida | pendiente | Texto en español, frases ≤200 caracteres | Audio 22 kHz | Primera muestra en ≤500 ms en CPU | Inteligibilidad: ≥95 % de frases entendidas por oyentes adultos mayores; voz en español latinoamericano |
| Personas / permisos | no aplica | — | — | — | No es un modelo: se valida con pruebas del registro |

---

## 5. Evidencia de verificación

| Campo | Valor |
|---|---|
| Fecha | 2026-11-15 |
| Repositorio | `uvix_ws` |
| Rama | `feature/m1-02-interfaces` |
| Commit base | `1ba3ccf` (Corrección del README) + cambios de este documento (`parent_request_id` en `UserCommand`, `docs/`) |
| PR | *pendiente de crear* |
| Equipo | AMD Ryzen 7 5800H, 15.4 GB RAM |
| Sistema | Windows 11 Home (build 26200) + WSL2 (kernel 6.18.33.2-microsoft-standard-WSL2) |
| Distribución | Ubuntu 22.04.5 LTS |
| ROS 2 | **Humble** (`/opt/ros/humble`, `ros-humble-ros-base` 0.10.0) |
| RMW | por defecto (`RMW_IMPLEMENTATION` sin definir → Fast DDS) |
| Herramientas | Python 3.10.12, CMake 3.22.1, colcon |

### 5.1 Compilación limpia

```bash
source /opt/ros/humble/setup.bash
cd ~/uvix_ws
rm -rf build/uvix_interfaces install/uvix_interfaces
colcon build --packages-select uvix_interfaces
```

Resultado:

```
Finished <<< uvix_interfaces [57.9s]
Summary: 1 package finished [58.7s]
```

Sin errores ni advertencias.

### 5.2 Inspección de interfaces

```bash
source install/setup.bash
ros2 interface package uvix_interfaces | wc -l     # -> 19
ros2 interface package uvix_interfaces | sort
```

```
uvix_interfaces/action/ExecuteMission
uvix_interfaces/action/SpeakText
uvix_interfaces/msg/Alert
uvix_interfaces/msg/ClarificationRequest
uvix_interfaces/msg/CommandEvent
uvix_interfaces/msg/IdentityVerification
uvix_interfaces/msg/KeyValue
uvix_interfaces/msg/MissionSpec
uvix_interfaces/msg/MissionStatus
uvix_interfaces/msg/Person
uvix_interfaces/msg/PowerStatus
uvix_interfaces/msg/RobotActivity
uvix_interfaces/msg/SystemStatus
uvix_interfaces/msg/UserCommand
uvix_interfaces/srv/AckAlert
uvix_interfaces/srv/CancelMission
uvix_interfaces/srv/GetPerson
uvix_interfaces/srv/GetRequestIdentity
uvix_interfaces/srv/RegisterMission
```

```bash
ros2 interface show uvix_interfaces/msg/UserCommand --no-comments
ros2 interface show uvix_interfaces/srv/GetRequestIdentity --no-comments
ros2 interface proto uvix_interfaces/msg/MissionSpec
```

Resultado (extracto): `UserCommand` incluye `request_id`, `parent_request_id`,
`session_id`, `identity_status`, `person_id`, `track_id`. `GetRequestIdentity`
devuelve `found` + `IdentityVerification` completa (incluye `valid_until`).
`MissionSpec` incluye `start_time` y `deadline`, y ya no tiene `requester_role`.

### 5.3 Validación del catálogo

```bash
python3 -c "import yaml; d=yaml.safe_load(open('docs/m1_capacidades.yaml')); print(len(d['capacidades']))"
```

Resultado: el YAML es válido; 6 capacidades, todas con `entrada`, `salida`,
`responsable`, `consumidores`, `timeout_s`, `fallos`, `version` y `alcance_m1`.

---

## 6. Pendientes para cerrar M1

- [ ] Validar automáticamente los ejemplos YAML del README contra los tipos
      (fixtures válidos e inválidos, criterio de UVIX-01).
- [ ] Documentar QoS y reloj por interfaz en el README (criterio de UVIX-01; el
      catálogo ya lo incluye para las capacidades).
- [ ] Decidir el contrato de *Personas* (`vision_msgs` o mensaje propio) y añadir la dependencia.
- [ ] Asignar responsable humano a cada capacidad.
- [ ] Corregir los diagramas (anomalías C1–C7 del README).
- [ ] Crear el PR y anotar su número en la sección 5.
- [ ] Revisión cruzada de contratos con el compañero (evidencia de UVIX-01).

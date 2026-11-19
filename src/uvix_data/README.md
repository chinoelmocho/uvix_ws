# uvix_data

Registro local de personas, preferencias, permisos y plantillas faciales de UVIX
(M1-05, issue #60). Django + SQLite, servido por ROS 2:

| Interfaz | Tipo | Ejecutable | Estado |
|---|---|---|---|
| `/uvix/get_person` | `GetPerson` (srv), con `status` OK / NOT_FOUND / UNAVAILABLE | `uvix_data_node` | implementado |
| `/uvix/check_permission` | `CheckPermission` (srv) | `uvix_data_node` | implementado |
| `/uvix/enroll_face` | `EnrollFace` (action) | `uvix_enroll_face_sim` | **simulado** (sin cámara) |

Explicación de `GetPerson` con diagramas: [FUNCIONAMIENTO.md](FUNCIONAMIENTO.md).
Diseño del siguiente módulo (recordatorios, grupos, notas): [DISENO_REMINDERS.md](DISENO_REMINDERS.md).

Todo lo de este documento se comprobó el 2026-11-19 en ROS 2 Humble (Ubuntu
22.04, WSL2), `/usr/bin/python3` sin entorno virtual, Cyclone DDS y solo datos
ficticios.

## 1. Esquema de relaciones

```
Person (person_id único, display_name, role, active)        ← registro central
 ├─< PersonPreference (key, value)        UNIQUE(person, key)
 └─< FaceTemplate (template_id único, consentimiento, modelo, estado)   ← interno

Capability (code único)  ─<  RolePermission (role ∈ {PATIENT, STAFF})   UNIQUE(role, capability)
```

- Los modelos nuevos usan campos estándar de Django; pasar a PostgreSQL es
  cambiar `DATABASES` y migrar. Las interfaces ROS no cambian.
- Migraciones: `0002` preferencias, `0003` catálogo y permisos, `0004` carga del
  catálogo inicial (datos), `0005` plantillas faciales. Las personas existentes
  no se modifican: siguen apareciendo en `GetPerson` con `preferences: []`.
- El historial de misiones no vive aquí (ver [DISENO_REMINDERS.md](DISENO_REMINDERS.md) §2).

## 2. Preferencias de interacción

| Clave | Valores | ¿La devuelve `GetPerson`? |
|---|---|---|
| `language` | `es`, `en` | sí |
| `speech_rate` | `slow`, `normal`, `fast` | sí |
| `form_of_address` | `tu`, `usted` | sí |
| `favorite_activity` | texto libre (≤64) | sí |

`GetPerson` devuelve solo las preferencias de esa persona, ordenadas por clave y
filtradas por la lista anterior (`PREFERENCIAS_GET_PERSON` en `people/models.py`).
Una clave escrita a mano en la base que no esté en la lista nunca sale por ROS.
**Las preferencias no conceden permisos**: `CheckPermission` no las lee.

## 3. Catálogo de operaciones

Una *operación* es algo que una persona puede **solicitar**. No es lo mismo que
las capacidades técnicas de [`docs/m1_capacidades.yaml`](../../docs/m1_capacidades.yaml)
(percepción, voz, rostros...). Cuando coincide con un `MissionSpec.TYPE_*`, se
usa el mismo código. La categoría es descriptiva: se autoriza siempre la
operación concreta (pedir `encargo` → `CODE_UNKNOWN_OPERATION`).

| Código | Operación | Origen | Ejecutor |
|---|---|---|---|
| `deliver_item` | Enviar un encargo a una persona | `MissionSpec.TYPE_DELIVER_ITEM` | contrato de misión; ejecutor pendiente |
| `reminder_round` | Recordatorios **siempre para un grupo** en un horario | `MissionSpec.TYPE_REMINDER_ROUND` | contrato de misión; ejecutor pendiente |
| `find_person` | Búsqueda física de una persona | nuevo | solo registrada |
| `operational_report` | Informe operativo (visitas, avisos, no localizados) | nuevo | solo registrada |
| `socialize_zone` | Socializar con pacientes en una zona | nuevo (distinto de `dance`/`chat`, que pide el paciente para sí) | solo registrada |
| `dispense_medication` | Dispensación de medicamentos para un grupo | nuevo (distinto de `dispense_vitamins`). **Solo autorización con datos ficticios; sin dispensación, dosis ni decisiones clínicas** | solo registrada |
| `list_patients` | Buscar y listar pacientes en el registro | nuevo (independiente de `find_person`). Da el resumen autorizado; notas o mediciones requerirían su propia operación | solo registrada |
| `attend_help_request` | Pedir ayuda (**nunca se deniega**) | `MissionSpec` | contrato; ejecutor pendiente |
| `personal_reminder` | Recordatorio individual que pide un paciente (P3), sin grupo | `MissionSpec.TYPE_PERSONAL_REMINDER` (nuevo) | contrato de misión; ejecutor pendiente |
| `dance`, `chat` | Bailar, conversar | `MissionSpec` | contrato; ejecutor pendiente |
| `dispense_vitamins` | Dispensar vitaminas | `MissionSpec` | contrato; ejecutor pendiente |
| `enroll_face` | Alta facial guiada | nuevo | `uvix_enroll_face_sim` (simulado) |

"Ejecutor pendiente": `mission_manager` todavía no tiene código; el tipo existe
en `MissionSpec`, pero nadie ejecuta la misión. `attend_fall` y `go_charge` no
están en el catálogo porque los origina el robot (`DETECTION`/`SYSTEM`), no una
persona.

**Carga reproducible:** la migración `0004_catalogo_inicial` crea el catálogo y
las concesiones en cualquier base con `migrate` (idempotente). Las operaciones
nuevas se añaden con el admin o con `Capability.objects.create(...)`.

## 4. Matriz de permisos

| Operación | PATIENT | STAFF | ADMIN | Cualquiera, sin condiciones |
|---|---|---|---|---|
| `attend_help_request` (pedir ayuda) | sí | sí | sí | **sí, siempre** |
| Las siete acordadas (`deliver_item` … `list_patients`, incluido `reminder_round` de grupo) | no | **sí** | sí | no |
| `dance`, `chat`, `personal_reminder` | sí | sí | sí | no |
| `dispense_vitamins` | no | sí | sí | no |
| `enroll_face` | no | no (sin concesión) | sí | no |
| Operación registrada después | solo con concesión | solo con concesión | **sí, de inmediato** | no |
| Operación no registrada | no | no | **no** | no |

Las concesiones de STAFF son el punto de partida; se amplían con
`RolePermission` (admin de Django) sin tocar código.

Condiciones comunes (todas las operaciones **salvo pedir ayuda**): identidad
`VERIFIED` y vigente para ese `request_id` (según el proveedor confiable),
persona en el registro y `active = true`. Una persona desactivada conserva su
registro y no autoriza nada. `ROLE_UNKNOWN` no tiene concesiones.

**Pedir ayuda nunca se deniega (seguridad primero).** `attend_help_request`
devuelve siempre `allowed = true`: `CODE_ALLOWED` si además todo está en regla, o
`CODE_ALLOWED_HELP` si la identidad es candidata, desconocida o está vencida, si
la persona está desactivada o no registrada, o si no se pudo consultar la
identidad o la base. El motivo va en `message` y, si se sabe, quién la pidió en
`evaluated_person_id`. No es configurable desde la base.

`reminder_round` es siempre un recordatorio para un grupo. Comprobar que el
`MissionSpec` lleve varios destinatarios o un grupo le corresponde al
`mission_manager`; el recordatorio individual de un paciente es `personal_reminder`.

## 5. `/uvix/get_person` y `status`

| Situación | `status` | `found` | Qué debe entender el cliente |
|---|---|---|---|
| Persona registrada (activa o no) | 0 `STATUS_OK` | true | Datos completos; si `active=false`, no autoriza nada |
| `person_id` desconocido o vacío | 1 `STATUS_NOT_FOUND` | false | No está registrada → sin permisos |
| Base ilegible en marcha | 2 `STATUS_UNAVAILABLE` | false | No se pudo consultar → **nunca asumir un rol** (`CODE_INTERNAL_ERROR`) |

Ante un error de base el nodo responde `UNAVAILABLE`, lo registra en el log y
**sigue en marcha**: cuando la base vuelve a estar disponible, responde de nuevo
`OK` sin reiniciar. `found` se mantiene por compatibilidad, pero los clientes
deben mirar `status`, porque `found=false` aparece tanto en `NOT_FOUND` como en `UNAVAILABLE`.

## 5b. `/uvix/check_permission`

Petición: `request_id` + `operation`. No acepta rol, `person_id` ni "verificado"
del cliente: la identidad se pide a `/uvix/get_request_identity` (parámetros
`identity_service` e `identity_timeout_s`, 2.0 s) y `role`/`active` se leen de la base.

Orden de comprobación y códigos estables (`CheckPermission.srv`). Pedir ayuda
no sigue esta tabla: siempre 0 `ALLOWED` o 1 `ALLOWED_HELP`.

| # | Comprobación | Código si falla |
|---|---|---|
| 1 | `request_id` y `operation` presentes | 16 `INVALID_REQUEST` |
| 2 | Operación registrada | 11 `UNKNOWN_OPERATION` |
| 3 | El proveedor de identidad responde | 20 `IDENTITY_UNAVAILABLE` |
| 4 | Existe verificación para ese `request_id` y es `VERIFIED` (`CANDIDATE` o `UNKNOWN` no bastan) | 12 `IDENTITY_NOT_VERIFIED` |
| 5 | `ahora ≤ valid_until` | 13 `IDENTITY_EXPIRED` |
| 6 | La persona está en el registro | 14 `PERSON_NOT_FOUND` |
| 7 | `active = true` | 15 `PERSON_INACTIVE` |
| 8 | ADMIN, o concesión `RolePermission` del rol | 10 `NOT_AUTHORIZED` |
| — | Base ilegible en cualquier paso | 21 `STORAGE_UNAVAILABLE` |

Rangos: 0–9 permitido, 10–19 denegación válida, 20–29 **sin decisión** (no se
pudo consultar; el cliente no debe tratarlo como permiso ni como denegación
definitiva → `RegisterMission.CODE_INTERNAL_ERROR`). La respuesta incluye
`evaluated_person_id`: siempre es el **solicitante** (si Juan pide una entrega
para María, se evalúa a Juan).

## 6. Plantillas faciales (`FaceTemplate`) y `EnrollFace`

| Campo | Contenido |
|---|---|
| `template_id` | `ftpl-` + UUID, único y estable |
| `person` | FK a `Person`; una persona tiene 0..n plantillas |
| `source` | `guided_capture` (futuro) o `simulated` (M1) |
| `consent_ref` | Referencia al consentimiento; obligatorio (restricción en la base) |
| `enrolled_by`, `request_id` | Operador autorizado y petición que la creó |
| `model_name`, `model_version` | Modelo con el que se generó |
| `quality`, `samples` | Calidad media y número de muestras |
| `embedding_ref` | Referencia al vector; en M1 `ficticio://…`. **No se guarda biometría** |
| `status`, `revoked_at`, `revoke_reason` | `active` / `revoked` |

- **Alta:** solo con `EnrollFace` terminado en `RESULT_ENROLLED`. La fila se
  crea al final, en una transacción, tras comprobar por última vez la
  cancelación. Cancelada, calidad insuficiente o incompleta = ninguna fila.
  Requiere `consent_ref`, persona registrada y activa, y `CheckPermission(enroll_face)`
  (solo ADMIN por defecto).
- **Consulta:** solo el componente de identificación, internamente. No sale por
  `GetPerson` (el mensaje `Person` no tiene campos para ello), ni por topics,
  ni en el resultado o el feedback de `EnrollFace` (solo `template_id`).
- **Actualización:** no se editan; se da de alta una nueva y se revoca la anterior
  (p. ej. al cambiar de modelo).
- **Baja:** `revoke()` (o la acción del admin) marca `revoked` y borra
  `embedding_ref`. Si se retira el consentimiento se eliminan las filas.
- **Quién administra:** ADMIN (admin de Django y `enroll_face`). Se conservan solo
  los metadatos de la tabla; no hay historias clínicas ni permisos derivados del
  reconocimiento facial.

`uvix_enroll_face_sim` simula la cámara: lee calidades por persona desde un
JSON (`-p sim_muestras_file:=...`; `null` = rostro perdido; sin entrada =
muestras buenas) con una muestra cada `sim_periodo_s`. Umbral de calidad 0.8,
más de 3 rechazos → `RESULT_LOW_QUALITY`. La captura real queda para la
integración con el componente de identificación.

## 7. Requisitos

- Django 5.2 y `ros2-django` (`requirements.txt`) para el `python3` del sistema
  (en el PC de desarrollo, `pip --user`).
- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` (en este WSL, Fast DDS no descubre nodos).

## 8. Compilar, migrar y arrancar

Base por defecto: `~/.local/share/uvix/uvix.sqlite3`. `UVIX_DATA_DB` elige otra.

```bash
source /opt/ros/humble/setup.bash
cd ~/uvix_ws
colcon build --packages-up-to uvix_data
source install/setup.bash
python3 -m django migrate --settings=uvix_data_project.settings
ros2 run uvix_data uvix_data_node
```

Si la base no existe o le faltan migraciones, el nodo no ofrece servicios, lo
indica en el log y termina con código 1. Ctrl+C y SIGTERM lo cierran con código 0.

## 9. Demostración manual (comprobada, base temporal)

```bash
export ROS_DOMAIN_ID=80 UVIX_DATA_DB=/tmp/uvix_demo/uvix.sqlite3
mkdir -p /tmp/uvix_demo && cd /tmp/uvix_demo
python3 -m django migrate --settings=uvix_data_project.settings
python3 -m django shell --settings=uvix_data_project.settings -c "
from people.models import Person, PersonPreference
juan = Person.objects.create(person_id='prueba_staff_juan', display_name='Juan Ficticio', role=2, active=True)
Person.objects.create(person_id='prueba_admin_01', display_name='Admin Ficticio', role=3, active=True)
PersonPreference.objects.create(person=juan, key='language', value='es')
PersonPreference.objects.create(person=juan, key='form_of_address', value='usted')"
cat > identidades.json <<'EOF'
{"req-demo-1": {"person_id": "prueba_staff_juan", "status": 2, "ttl_s": 600},
 "req-demo-2": {"person_id": "prueba_admin_01", "status": 2, "ttl_s": 600}}
EOF

# Cada uno en su terminal (mismo ROS_DOMAIN_ID y UVIX_DATA_DB):
python3 ~/uvix_ws/src/uvix_data/test/identidad_ficticia.py identidades.json
ros2 run uvix_data uvix_data_node
ros2 run uvix_data uvix_enroll_face_sim
```

```bash
ros2 service call /uvix/get_person uvix_interfaces/srv/GetPerson "{person_id: prueba_staff_juan}"
# status=0, found=True, person=Person(..., role=2, active=True, preferences=[KeyValue(key='form_of_address', value='usted'), KeyValue(key='language', value='es')])

ros2 service call /uvix/check_permission uvix_interfaces/srv/CheckPermission "{request_id: req-demo-1, operation: deliver_item}"
# allowed=True, code=0, evaluated_person_id='prueba_staff_juan', evaluated_role=2, identity_status=2

ros2 service call /uvix/check_permission uvix_interfaces/srv/CheckPermission "{request_id: req-demo-1, operation: enroll_face}"
# allowed=False, code=10, message='El rol Personal no tiene enroll_face'

ros2 action send_goal /uvix/enroll_face uvix_interfaces/action/EnrollFace \
  "{person_id: prueba_staff_juan, request_id: req-demo-2, consent_ref: consentimiento-ficticio-001}"
# result_code: 0, enrolled: true, template_id: ftpl-..., samples_accepted: 5 -> SUCCEEDED
```

## 10. Pruebas

Con el install cargado y Cyclone DDS. Ninguna toca la base habitual.

```bash
# Unitarias (51): GetPerson y status, preferencias, migración compatible, permisos, ayuda, EnrollFace
cd ~/uvix_ws/src/uvix_data
UVIX_DATA_DB=/tmp/uvix_unit.sqlite3 python3 -m django test people --settings=uvix_data_project.settings

# Extremo a extremo de GetPerson (15 casos): status, cierre, base sin migrar,
# error de base en marcha (UNAVAILABLE) y recuperación
python3 ~/uvix_ws/src/uvix_data/test/validar_get_person.py --domain 77

# Extremo a extremo de preferencias, CheckPermission, ayuda y EnrollFace (32 casos)
python3 ~/uvix_ws/src/uvix_data/test/validar_permisos.py --domain 79

# Mediciones de GetPerson
python3 ~/uvix_ws/src/uvix_data/test/medir_get_person.py --domain 77 --tandas 5 --llamadas 200 --reposo 30
```

`validar_permisos.py` arranca en procesos separados el proveedor de identidad
ficticio (`test/identidad_ficticia.py`), `uvix_data_node` y
`uvix_enroll_face_sim` instalados, y los consulta con un cliente rclpy.
Sale con código 0 solo si todos los casos pasan.

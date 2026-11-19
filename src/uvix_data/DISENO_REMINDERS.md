# Propuesta: app Django `reminders` (siguiente issue)

Estado: **diseño**. Este documento solo define el esquema y un ejemplo. Las
migraciones, los servicios ROS y el ejecutor quedan para el siguiente issue.

- Vive en el mismo paquete (`src/uvix_data/reminders/`) y en la misma base que
  `people`. Se relaciona con `people.Person` mediante claves foráneas.
- Solo usa campos estándar de Django: el paso a PostgreSQL es cambiar
  `DATABASES` y migrar, sin tocar las interfaces ROS.
- Autorización: programar un recordatorio usa la operación `reminder_round` de
  `/uvix/check_permission`; leer notas restringidas usaría una operación propia
  (`read_restricted_notes`), no `list_patients`.

## 1. Relaciones

```
people.Person ─┬─< Reminder (created_by: autor)
               ├─< ReminderRecipient (person: destinatario) >── Reminder
               │        └─< ReminderDelivery (una fila por destinatario y ocurrencia)
               ├─< GroupMembership >── ResidentGroup
               ├─< PersonNote (about: de quién trata)   PersonNote.author ──> Person
               └─o PersonBirthdate (1:1, opcional)

Historial de misiones (app aparte, futura): MissionRecord / MissionTargetResult
guardan mission_id y person_id como TEXTO, no como FK.
```

## 2. Modelos

### Reminder

| Campo | Tipo | Notas |
|---|---|---|
| `reminder_id` | Char único | `rem-` + UUID; identificador estable para ROS |
| `created_by` | FK → `Person` (PROTECT) | **Autor**. No es destinatario salvo que tenga su propia fila en `ReminderRecipient` |
| `request_id` | Char | Petición autorizada con `CheckPermission(reminder_round)`; trazabilidad |
| `message` | Char(280) | Texto que dirá el robot |
| `dtstart` | DateTime (aware, UTC) | Primera ocurrencia |
| `timezone` | Char | Zona IANA, p. ej. `America/Guayaquil` |
| `rrule` | Text, vacío = una sola vez | Recurrencia en formato RFC 5545, p. ej. `FREQ=DAILY;BYHOUR=10;BYMINUTE=0;COUNT=30` |
| `source_group` | FK → `ResidentGroup`, nulo | Solo informativo: de qué grupo salieron los destinatarios |
| `active` | Bool | Pausar o cancelar sin borrar historial |
| `created_at` | DateTime | |

**Recurrencia.** Se guarda `dtstart` + `timezone` + `rrule` y las ocurrencias
se calculan, no se guardan por adelantado. Se expanden en la hora local
(`dateutil.rrule` con `dtstart` convertido a la zona) y cada ocurrencia se pasa
a UTC; así "todos los días a las 10:00" sigue siendo a las 10:00 locales aunque
cambie el horario de verano. La **ocurrencia** se identifica por su instante UTC
(`occurrence_at`). Las excepciones (saltar un día) podrán añadirse con una
tabla `ReminderException(reminder, occurrence_at)`.

### ReminderRecipient

| Campo | Tipo | Notas |
|---|---|---|
| `reminder` | FK → `Reminder` (CASCADE) | |
| `person` | FK → `Person` (PROTECT) | **Destinatario** |
| `added_from_group` | FK → `ResidentGroup`, nulo | Trazabilidad |
| Restricción | `UNIQUE(reminder, person)` | |

### ReminderDelivery

Resultado por **destinatario** y por **ocurrencia**.

| Campo | Tipo | Notas |
|---|---|---|
| `recipient` | FK → `ReminderRecipient` (CASCADE) | |
| `occurrence_at` | DateTime (UTC) | Ocurrencia calculada |
| `status` | `pending` · `emitted` · `confirmed` · `not_found` · `failed` · `skipped` | |
| `attempts` | Int | Se incrementa en cada reintento |
| `emitted_at` | DateTime, nulo | El robot **dijo** el aviso a la persona identificada (`SpeakText` `RESULT_COMPLETED`) |
| `confirmed_at` | DateTime, nulo | La persona **respondió** que lo recibió. Exige `emitted_at` |
| `mission_id` | Char | Misión `reminder_round` que hizo el intento |
| `detail` | Char | Motivo (`CODE_PERSON_NOT_FOUND`, persona desactivada...) |
| Restricción | `UNIQUE(recipient, occurrence_at)` | |
| Restricción | `CHECK(confirmed_at IS NULL OR emitted_at IS NOT NULL)` | |

- **Sin duplicados al reintentar:** el ejecutor hace `update_or_create` sobre
  `(recipient, occurrence_at)`; un reintento actualiza la misma fila y suma
  `attempts`. La restricción única lo garantiza en la base.
- **Emitido ≠ confirmado:** `emitted` significa que se dijo; `confirmed`, que la
  persona lo reconoció. El estado no retrocede (de `confirmed` no se vuelve a
  `emitted`).
- Persona desactivada al llegar la ocurrencia → `skipped`, sin intento.

### ResidentGroup y GroupMembership

| Modelo | Campos |
|---|---|
| `ResidentGroup` | `code` único, `name`, `active` |
| `GroupMembership` | `group` FK, `person` FK, `joined_at`, `left_at` (nulo = vigente). `UNIQUE(group, person) WHERE left_at IS NULL` |

Una persona puede estar en varios grupos. Salir de un grupo cierra la fila
(`left_at`) y conserva el historial.

**Decisión: los destinatarios se fijan al programar.** Al programar para un
grupo se copian sus miembros vigentes a `ReminderRecipient`. Motivos:

1. El autor autorizó una lista concreta; quien entre después al grupo no
   recibe avisos que nadie programó para él.
2. El informe compara "programados" con "entregados" sobre la misma lista.
3. Sale del grupo ≠ deja de necesitar el aviso; si debe dejar de recibirlo, se
   quita su fila (o se desactiva la persona).

Para que alguien nuevo reciba un recordatorio recurrente ya programado, el autor
o un ADMIN lo añade (otra fila). Un modo "grupo dinámico" (miembros al momento de
cada ocurrencia) queda descartado para M1.

### PersonNote

| Campo | Tipo | Notas |
|---|---|---|
| `about` | FK → `Person` | Persona sobre la que trata |
| `author` | FK → `Person` (PROTECT) | Quién la escribió |
| `created_at` | DateTime | Las notas no se editan; una corrección es otra nota |
| `text` | Text | Sin diagnósticos ni historia clínica |
| `access_scope` | `staff` · `admin` | `staff` exige `read_restricted_notes` (concesión expresa); `admin` solo ADMIN |

Las notas no salen por `GetPerson` ni por `list_patients`.

### Cumpleaños y mediciones

- Si la función solo felicita, basta con **mes y día** (`birth_month`,
  `birth_day`), sin año. Si hace falta la edad, se guarda `birth_date` en una
  tabla 1:1 `PersonBirthdate` (acceso restringido). La edad **no se guarda**:
  `edad = hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))`, con
  `hoy` en la zona horaria de la residencia. Para el 29 de febrero se felicita el
  28 en años no bisiestos.
- **Peso y otras mediciones quedan fuera de M1.** Si se incorporan:
  `PersonMeasurement(person, kind, value, unit, measured_at, source,
  recorded_by)`, con lectura sólo mediante una operación propia
  (`read_measurements`) y nunca por topics generales.

### Historial de rondas y misiones

Va en su propia app (no en `reminders` ni en `people`). `MissionRecord`
(`mission_id` único, `mission_type`, `requested_by`, estado, código, horas) y
`MissionTargetResult` (`mission_id`, `person_id`, resultado) guardan los
identificadores como **texto**, para que el historial sobreviva a cambios del
registro. `ReminderDelivery.mission_id` enlaza con ese historial.

## 3. Ejemplo: Juan programa un recordatorio para tres pacientes

Datos ficticios. Juan (`staff_juan`) dice "recuerda a María, Pedro y Rosa tomar
agua a las 10:00". `CheckPermission(req-0100, reminder_round)` → `CODE_ALLOWED`.

**Reminder**

| reminder_id | created_by | message | dtstart (UTC) | timezone | rrule |
|---|---|---|---|---|---|
| rem-0001 | staff_juan | Es hora de tomar agua | 2026-11-20 15:00 | America/Guayaquil | *(vacío)* |

**ReminderRecipient** (Juan es autor, no destinatario)

| id | reminder | person |
|---|---|---|
| 1 | rem-0001 | patient_maria |
| 2 | rem-0001 | patient_pedro |
| 3 | rem-0001 | patient_rosa |

El ejecutor lanza la misión `mis-0042` (`reminder_round`, `report_on_failure:
true`, `report_to: staff_juan`). Rosa no aparece tras recorrer las zonas; se
reintenta una vez.

**ReminderDelivery** (ocurrencia 2026-11-20 15:00 UTC)

| recipient | status | attempts | emitted_at | confirmed_at | mission_id | detail |
|---|---|---|---|---|---|---|
| 1 María | confirmed | 1 | 15:03 | 15:03 | mis-0042 | |
| 2 Pedro | emitted | 1 | 15:06 | — | mis-0042 | sin respuesta |
| 3 Rosa | not_found | 2 | — | — | mis-0042 | CODE_PERSON_NOT_FOUND |

El reintento de Rosa actualizó la fila 3 (`attempts` 1 → 2) en lugar de crear otra.

**Informe que recibe Juan.** Sale de `ReminderDelivery` ⋈ `ReminderRecipient`
⋈ `Person` filtrando `reminder = rem-0001` y la ocurrencia:

```
Recordatorio "Es hora de tomar agua" (20/11 10:00):
  avisos emitidos: 2 (María, Pedro)
  confirmados:     1 (María)
  no localizados:  1 (Rosa)
```

Se entrega como `Alert` `LEVEL_INFO` con `notify_person_id: staff_juan` y
`mission_id: mis-0042`, coherente con `MissionStatus` `STATE_PARTIAL`
(`completed_targets: [patient_maria, patient_pedro]`, `failed_targets:
[patient_rosa]`). Si Juan pide el informe más tarde, la operación
`operational_report` lee las mismas filas.

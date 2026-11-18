# uvix_data

Registro local de personas de UVIX (M1-05). Un nodo ROS 2 ofrece
`/uvix/get_person` (`uvix_interfaces/srv/GetPerson`) leyendo una base SQLite
gestionada con Django.

| Petición | Respuesta |
|---|---|
| `person_id` registrado | `found: true` + `Person` (`person_id`, `display_name`, `role`, `active`) |
| `person_id` desconocido | `found: false`, `role: 0` (`ROLE_UNKNOWN`) |
| Base inutilizable | **no hay respuesta**: el nodo no arranca o se detiene con un error en el log. El cliente lo trata como servicio no disponible, nunca como `found: false` |

Una persona desactivada se sigue encontrando (`found: true`, `active: false`) y
conserva su identidad y su rol. `preferences` se devuelve siempre vacía: el
modelo aún no guarda preferencias.

Todos los pasos siguientes se comprobaron el 2026-11-18 en ROS 2 Humble
(Ubuntu 22.04, WSL2) con `/usr/bin/python3` y sin entorno virtual.

## Requisitos

- Django 5.2 y `ros2-django` (ver `requirements.txt`) instalados para el
  `python3` del sistema. En el PC de desarrollo están en `~/.local` (`pip --user`).
- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`. En este WSL, Fast DDS (el RMW por
  defecto) no descubre nodos, ni siquiera los de `demo_nodes_py`.

## Base de datos

Ruta por defecto: `~/.local/share/uvix/uvix.sqlite3`. La variable
`UVIX_DATA_DB` permite usar otra base, por ejemplo una temporal de prueba. El nodo
escribe en el log la ruta efectiva al arrancar.

## Compilar, migrar y arrancar

```bash
source /opt/ros/humble/setup.bash
cd ~/uvix_ws
colcon build --packages-up-to uvix_data
source install/setup.bash

# Crear o actualizar el esquema (sirve desde cualquier carpeta)
python3 -m django migrate --settings=uvix_data_project.settings

ros2 run uvix_data uvix_data_node
```

Si la base no existe o le faltan migraciones, el nodo no ofrece el servicio,
lo indica en el log (`Ejecute 'python3 -m django migrate --settings=uvix_data_project.settings'`) y termina con
código 1. Ctrl+C y SIGTERM lo cierran con código 0.

## Dar de alta una persona (datos ficticios)

```bash
python3 -m django shell --settings=uvix_data_project.settings -c \
  "from people.models import Person; Person.objects.create(person_id='prueba_staff_01', display_name='Cuidadora Ficticia', role=2, active=True)"
```

Roles: 0 desconocido, 1 paciente, 2 personal, 3 administrador.

## Consultar

```bash
ros2 service call /uvix/get_person uvix_interfaces/srv/GetPerson "{person_id: prueba_staff_01}"
# found=True, person=Person(person_id='prueba_staff_01', display_name='Cuidadora Ficticia', role=2, active=True, preferences=[])
```

## Pruebas

Ejecutar con el install cargado (`source install/setup.bash`) y con
`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`. Ninguna toca la base habitual.

```bash
# Unitarias del callback (base de prueba de Django, en memoria)
UVIX_DATA_DB=/tmp/uvix_unit.sqlite3 python3 -m django test people --settings=uvix_data_project.settings

# Extremo a extremo: ros2 run + cliente en ROS_DOMAIN_ID=77 sobre una base temporal
python3 src/uvix_data/test/validar_get_person.py --domain 77

# Mediciones: RSS, CPU en reposo y latencia por tandas
python3 src/uvix_data/test/medir_get_person.py --domain 77 --tandas 5 --llamadas 200 --reposo 30
```

`validar_get_person.py` cubre los siguientes casos: persona activa, persona
desactivada, persona inexistente, `preferences`, reinicio, cierre con
SIGINT/SIGTERM, base sin migraciones y error de almacenamiento en marcha. Sale con
código 0 solo si todos pasan.

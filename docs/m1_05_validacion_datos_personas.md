# M1-05: validación de `uvix_data` (`/uvix/get_person`)

| Campo | Valor |
|---|---|
| Fecha | 2026-11-18 |
| Rama de trabajo | `test/m1-05-validacion-datos-personas` (creada desde `feature/m1-05-datos-personas`) |
| Commit inicial | `91d3c50829a3bc03a6bfe30e005e06dc092941fb` |
| Equipo | **PC de desarrollo**: AMD Ryzen 7 5800H (16 hilos), 13.6 GiB visibles en WSL |
| Sistema | Windows 11 Home 26200 + WSL2 (kernel 6.18.33.2-microsoft-standard-WSL2), Ubuntu 22.04.5 LTS |
| ROS 2 | Humble (`/opt/ros/humble`) |
| RMW | `rmw_cyclonedds_cpp` (ver hallazgo H5) |
| Python | `/usr/bin/python3` 3.10.12, sin venv; Django 5.2.19 y `ros2-django` 1.0 en `~/.local` |
| Dominio ROS de prueba | `ROS_DOMAIN_ID=77` para el nodo y el cliente |

## 1. Fuentes revisadas

| Fuente | Estado |
|---|---|
| Issue #60 | Leído a través de la API pública de GitHub (`gh` no está instalado en WSL) |
| `docs/m1_interfaces.md`, `docs/m1_capacidades.yaml`, `docs/plan_uvix.md` (UVIX-15/16/26) | Revisados |
| README de `uvix_interfaces`, `Person.msg`, `GetPerson.srv`, `KeyValue.msg` | Revisados |
| Archivos de `uvix_data` | Revisados todos |

**Pruebas existentes al inicio:** ninguna. `people/tests.py` solo tenía la
plantilla de Django y no había `test/`. Faltaban todas: callback, nodo de extremo
a extremo, fallos de almacenamiento, cierre y recursos.

## 2. Método

- **Compilación limpia.** `env -i` + `source /opt/ros/humble/setup.bash` y
  `colcon build --packages-up-to uvix_data` (incluye `uvix_interfaces`) en
  `/tmp/uvix_m105_{base,fix}`. Tu `build/` e `install/` no se tocaron.
- **Línea base.** Código del commit inicial. Como no permitía elegir la base, se
  aisló con un `HOME` temporal (más `PYTHONUSERBASE` para conservar Django).
- **Versión corregida.** Base elegida con `UVIX_DATA_DB`. El script comprueba la
  ruta efectiva antes de migrar y aborta si no está dentro del temporal.
- **Ejecución.** Nodo instalado lanzado con `ros2 run` desde `/tmp`, fuera del
  repositorio. Cliente rclpy persistente en otro proceso. Solo datos ficticios.
- **Base diaria intacta.** `~/.local/share/uvix/uvix.sqlite3` sigue con fecha
  17:23:03 y 139264 bytes, anterior a la validación.

## 3. Resultados

"Antes" es el código del commit inicial; "después" incluye las correcciones de la
sección 4.

| # | Prueba | Resultado esperado | Antes: observado | Antes | Después: observado | Después |
|---|---|---|---|---|---|---|
| 1 | Compilación limpia de `uvix_interfaces` + `uvix_data` | sin errores | 2 paquetes, 57.5 s | PASÓ | 2 paquetes, 51.9 s | PASÓ |
| 2 | Ruta efectiva de la base | dentro del temporal | solo con `HOME` falso; `UVIX_DATA_DB` no existía | PASÓ (con apaño) | `…/datos/uvix_prueba.sqlite3` = `UVIX_DATA_DB` | PASÓ |
| 3 | Migraciones sobre base vacía | código 0 | código 0 | PASÓ | código 0 | PASÓ |
| 4 | Arranque con `ros2 run` fuera del repositorio | servicio disponible | disponible | PASÓ | disponible; el log indica la ruta de la base | PASÓ |
| 5 | Persona activa | `found=True`, id/nombre/rol 2, `active=True` | `found=True 'prueba_staff_01' 'Cuidadora Ficticia' role=2 active=True` | PASÓ | igual | PASÓ |
| 6 | Persona desactivada | `found=True`, conserva id/nombre/rol 1, `active=False` | `found=True 'prueba_paciente_02' 'Residente Ficticio' role=1 active=False` | PASÓ | igual | PASÓ |
| 7 | Identificador inexistente | `found=False`, `role=ROLE_UNKNOWN` | `found=False role=0`, campos vacíos | PASÓ | igual | PASÓ |
| 8 | `preferences` | vacía (ver H2) | `[]` | PASÓ | `[]` | PASÓ |
| 9 | Reinicio: detener y volver a consultar | mismo registro | mismo registro | PASÓ | mismo registro | PASÓ |
| 10 | Cierre con Ctrl+C (SIGINT al grupo) | código 0, sin traceback | código 0 | PASÓ | código 0 | PASÓ |
| 11 | Cierre con SIGTERM al nodo (como `ros2 launch` o systemd) | código 0, sin traceback | código 1 + traceback `ExternalShutdownException` | **FALLÓ** | código 0, sin traceback | PASÓ |
| 12 | Base sin migraciones (archivo inexistente) | no ofrece el servicio ni responde `found=False`; log claro; código ≠ 0 | prueba manual: anuncia el servicio, crea un `uvix.sqlite3` de 0 bytes y muere en la 1.ª consulta con traceback `no such table` | **FALLÓ** (manual; el script no pudo elegir la base) | servicio no anunciado; `ERROR No existe la base …`; código 1; el archivo no se crea | PASÓ |
| 13 | Base sin migraciones (archivo vacío) | igual que 12 | igual que 12 | **FALLÓ** (manual) | `ERROR Faltan 19 migraciones …`; código 1 | PASÓ |
| 14 | Error de almacenamiento en marcha (tabla renombrada) | no confundirlo con `found=False` | sin respuesta (timeout); el nodo muere con traceback, código 1 | PASÓ (distinguible, pero con caída sin mensaje claro) | sin respuesta (timeout); `FATAL Error de base de datos; el nodo se detiene: no such table…`; código 1 | PASÓ |
| 15 | Unitarias del callback (7) | todas OK | no existían | NO EJECUTADA | `Ran 7 tests … OK` | PASÓ |
| 16 | `ros2 service call` (activa e inexistente) | como 5 y 7 | — | NO EJECUTADA | `found=True … role=2, active=True, preferences=[]` / `found=False … role=0` | PASÓ |
| 17 | Mediciones (sección 5) | cifras registradas | registradas | PASÓ | registradas | PASÓ |

**Ya funcionaba al inicio:** los cuatro casos funcionales (activa, desactivada,
inexistente y reinicio), Ctrl+C y la distinción "fallo de base = sin respuesta"
(sin respuesta frente a `found=False`).
**Funciona después de las correcciones:** elegir una base de prueba, cierre
limpio con SIGTERM, y no anunciar el servicio con la base sin migrar ni crear
archivos vacíos. Un error de base en marcha ahora deja un mensaje claro.

## 4. Correcciones aplicadas

Todas son mínimas y mantienen SQLite, la interfaz `GetPerson` y la organización
del paquete.

| Fallo | Reproducción | Corrección | Archivo |
|---|---|---|---|
| No se podía elegir otra base sin cambiar `HOME` | Prueba 2 en la línea base | `UVIX_DATA_DB` opcional; sin ella se usa `~/.local/share/uvix/uvix.sqlite3` (verificado) | `uvix_data_project/settings.py` |
| Base sin migraciones: servicio anunciado, archivo de 0 bytes y caída en la 1.ª consulta | Pruebas 12 y 13 | Antes de `create_service` se comprueba que el archivo existe y que no hay migraciones pendientes (`MigrationExecutor`); si falla, `ERROR` y código 1 | `people/ros_node.py` |
| SIGTERM: traceback y código 1 | Prueba 11 | Se captura `ExternalShutdownException` igual que `KeyboardInterrupt` | `people/ros_node.py` |
| Error de base en marcha: traceback sin contexto y `main()` siempre devolvía 0 | Prueba 14 | `DatabaseError` → `FATAL` con la causa y código 1 (`sys.exit(main())`). El comportamiento sigue siendo "sin respuesta" | `people/ros_node.py` |

## 5. Mediciones (PC de desarrollo, no Jetson)

Proceso medido: el intérprete Python del nodo (hijo de `ros2 run`). Cliente rclpy
persistente en otro proceso. Consultas alternas a dos personas existentes.

- **RAM:** `VmRSS`, en MiB.
- **CPU en reposo:** (utime+stime)/tiempo real durante 30 s sin llamadas, en % de
  un núcleo. Resolución: 1 tick = 10 ms, así que 0.03 % equivale a un solo tick
  en la ventana.
- **Latencia:** ida y vuelta medida por el cliente (`call_async` +
  `spin_until_future_complete`), en ms.

### 5.1 RAM y CPU

| Corrida | RSS tras arranque | RSS tras 1.ª consulta | 1.ª consulta (ms) | RSS tras tandas | CPU reposo inicial / final |
|---|---|---|---|---|---|
| Línea base, 5×200 (corrida 1) | 68.4 | 69.1 | 7.51 | 69.4 → 69.9 | 0.03 % / 0.03 % |
| Línea base, 5×200 (corrida 2) | 68.4 | 69.1 | 9.24 | 69.3 → 69.9 | 0.03 % / 0.00 % |
| Corregida, 5×200 (corrida 1) | 69.3 | 69.5 | 6.14 | 69.8 → 70.3 | 0.03 % / 0.00 % |
| Corregida, 5×200 (corrida 2) | 69.3 | 69.5 | 4.24 | 69.7 → 70.3 | 0.00 % / 0.03 % |
| Corregida, 12×1000 | 69.5 | 69.6 | 6.11 | 70.4, 71.0, 71.6, 72.1, 72.7, 73.2, 73.8, 74.4, **74.9, 74.9, 74.9, 74.9** | 0.03 % / 0.03 % |

### 5.2 Latencia por tanda (ms)

Cada celda muestra p50 / p95 / máximo; n = llamadas por tanda.

| Corrida | n | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|---|
| Base 1 | 200 | 1.74 / 2.94 / 4.21 | 1.69 / 2.28 / 4.61 | 1.72 / 2.05 / 8.85 | 1.81 / 3.21 / 7.35 | 1.73 / 2.53 / 4.07 |
| Base 2 | 200 | 1.71 / 2.53 / 3.45 | 1.68 / 2.13 / 2.89 | 1.58 / 2.14 / 4.91 | 1.68 / 2.53 / 3.25 | 1.69 / 2.34 / 3.90 |
| Corregida 1 | 200 | 2.02 / 3.50 / 4.41 | 2.12 / 3.36 / 4.73 | 2.33 / 3.18 / 4.63 | 1.95 / 2.68 / 3.39 | 2.12 / 3.21 / 4.89 |
| Corregida 2 | 200 | 1.67 / 2.19 / 2.73 | 1.60 / 2.04 / 2.77 | 1.63 / 1.99 / 2.86 | 1.61 / 2.00 / 2.48 | 1.72 / 2.20 / 3.11 |
| Corregida larga | 1000 | p50 entre 1.66 y 2.25; p95 entre 2.58 y 4.63; máximo ≤ 8.47 en las 12 tandas | | | | |

Mínimo en todas las corridas: 1.33–1.59 ms.

**Lectura de los datos:**

- La comprobación de migraciones añade unos 0.9 MiB al arranque (68.4 → 69.3).
  La latencia no cambia: base y corregida coinciden dentro de la variación entre
  corridas (la corregida 1 fue la más lenta y la corregida 2 la más rápida).
- La RSS crece unos 0.6 KiB por llamada hasta unas 9000 llamadas y luego se
  estabiliza (74.9 MiB). Una sonda con `tracemalloc` lo explica: con
  `DEBUG=True`, Django guarda cada consulta en `connection.queries_log` (tope de
  9000), unos 5.0 MiB en total. Está acotado, así que no es una fuga (ver H3).
- En reposo el nodo prácticamente no consume CPU: queda en el límite de
  resolución de la medida.

### 5.3 LifecycleNode (para tu evaluación)

Con estos datos, un `LifecycleNode` no ahorraría recursos. En estado inactivo
seguirían cargados Python, rclpy y Django (unos 68 MiB), y en reposo el consumo
de CPU ya es prácticamente nulo. Su ventaja sería de orquestación: hacer en
`configure` la comprobación de base que ahora se hace al arrancar y ofrecer un
estado consultable por un gestor. Esto encaja mejor cuando `uvix_bringup` tenga
un *lifecycle manager*. **No se adoptó; el nodo sigue siendo normal.**

## 6. Hallazgos no corregidos y propuestas (para tu revisión)

| # | Hallazgo | Propuesta |
|---|---|---|
| H1 | El issue #60 pide que `GetPerson` distinga `NOT_FOUND` de `UNAVAILABLE`, pero el contrato solo tiene `found`. Hoy un fallo de base solo se distingue porque no hay respuesta (timeout), y el nodo se detiene. En rclpy Humble no se puede omitir la respuesta desde el callback: devolver `None` provoca `TypeError` en el ejecutor | **Cambio de interfaz:** añadir `uint8 status` con `STATUS_OK=0`, `STATUS_NOT_FOUND=1` y `STATUS_UNAVAILABLE=2` (y mantener `found` por compatibilidad). Así el nodo respondería `UNAVAILABLE` sin caerse |
| H2 | `Person.preferences` existe en el contrato M1 y el issue #60 pide "preferencias necesarias", pero el modelo no las guarda: siempre se devuelve `[]`. El alta y la edición de preferencias se planifican en UVIX-16 (M4) | Decidir si M1 solo exige el campo (vacío, "comportamiento genérico") o una tabla mínima `PersonPreference(person FK, key, value)` con su migración |
| H3 | `DEBUG=True` y `SECRET_KEY` fijos en `settings.py`: hasta unos 5 MiB extra en el nodo (sección 5.2) y una configuración de desarrollo en el robot | Leer `DEBUG` de una variable de entorno, con `False` por defecto en el nodo, y mover `SECRET_KEY` fuera de Git |
| H4 | La documentación no coincide con la implementación: `m1_capacidades.yaml` y el §6.5 del README de interfaces hablan de `personas.yaml` y `people_registry`; el issue #60 usa `/people/get`. La implementación usa SQLite + Django, nodo `uvix_data`, `/uvix/get_person`. El fallo "archivo corrupto → `SystemStatus ERROR`" no está implementado | Actualizar el catálogo y el README de interfaces (no lo toqué: son documentos de M1-02) |
| H5 | En este WSL, Fast DDS (el RMW por defecto) no descubre nodos, ni siquiera `demo_nodes_py`; Cyclone sí. Tu shell interactiva ya exporta Cyclone | Fijar el RMW en el *launch* o en el bringup y documentarlo para la Jetson |
| H6 | Django y `ros2-django` se instalan con pip en el *user site*. `package.xml` no los declara y `rosdep` no podría resolver `ros2-django` | Documentar la instalación en la Jetson (`pip3 install --user -r requirements.txt`) o empaquetarlos |
| H7 | Partes del issue #60 fuera de lo validado aquí: `CheckPermission.srv`, `EnrollFace.action`, `FaceTemplate` | Siguen pendientes para cerrar el issue |

## 7. Cómo repetir

En el PC o en la Jetson. Si es la Jetson, las cifras se registran como
**mediciones de la Jetson**.

```bash
# 0) Dependencias (una vez, Jetson): pip3 install --user -r ~/uvix_ws/src/uvix_data/requirements.txt
#    y sudo apt install ros-humble-rmw-cyclonedds-cpp
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# 1) Compilación limpia aislada (no toca build/ ni install/ del workspace)
B=$(mktemp -d /tmp/uvix_m105_XXXX)
cd ~/uvix_ws
env -i HOME=$HOME USER=$USER PATH=/usr/bin:/bin LANG=C.UTF-8 bash --noprofile --norc -c "
  source /opt/ros/humble/setup.bash
  colcon --log-base $B/log build --base-paths src/uvix_interfaces src/uvix_data \
    --packages-up-to uvix_data --build-base $B/build --install-base $B/install"

# 2) Pruebas (desde fuera del repositorio)
cd /tmp
source /opt/ros/humble/setup.bash && source $B/install/setup.bash
UVIX_DATA_DB=/tmp/uvix_unit.sqlite3 python3 -m django test people --settings=uvix_data_project.settings
python3 ~/uvix_ws/src/uvix_data/test/validar_get_person.py --domain 77          # 13 casos, código 0 si todo pasa
python3 ~/uvix_ws/src/uvix_data/test/medir_get_person.py --domain 77 \
    --tandas 5 --llamadas 200 --reposo 30 --json mediciones_jetson.json
python3 ~/uvix_ws/src/uvix_data/test/medir_get_person.py --domain 77 \
    --tandas 12 --llamadas 1000 --reposo 30                                      # meseta de RSS
```

`validar_get_person.py --conservar` deja los logs del nodo y `resultados.json`
en `/tmp/uvix_m105_*`.

## 8. Archivos modificados

| Archivo | Cambio |
|---|---|
| `src/uvix_data/uvix_data_project/settings.py` | `UVIX_DATA_DB` opcional; la ruta por defecto no cambia |
| `src/uvix_data/people/ros_node.py` | Comprobación de base y migraciones; cierre limpio con SIGTERM; `FATAL` + código 1 ante `DatabaseError`; registra la ruta de la base |
| `src/uvix_data/people/tests.py` | 7 pruebas unitarias del callback |
| `src/uvix_data/test/validar_get_person.py` | Nuevo: validación de extremo a extremo |
| `src/uvix_data/test/medir_get_person.py` | Nuevo: mediciones de RSS, CPU y latencia |
| `src/uvix_data/README.md` | Nuevo: pasos mínimos comprobados |
| `docs/m1_05_validacion_datos_personas.md` | Este informe |

## 9. Pendientes antes de integrar en `develop`

- [ ] Revisar y hacer *commit* de los cambios en `test/m1-05-validacion-datos-personas` (no hice *commit*, *merge* ni *push*).
- [ ] Recompilar tu `install/` (`colcon build --packages-select uvix_data`): el nodo diario sigue siendo el del commit inicial.
- [ ] Decidir H1 (`status` en `GetPerson`) y H2 (`preferences`).
- [ ] Decidir H3 (`DEBUG` y `SECRET_KEY`).
- [ ] Alinear el catálogo y el README de interfaces con la implementación (H4).
- [ ] Repetir las mediciones en la Jetson (sección 7).
- [ ] Completar el resto del issue #60 (H7).
- [ ] Opcional: borrar `/tmp/uvix_m105_*` (compilaciones y logs de esta validación).

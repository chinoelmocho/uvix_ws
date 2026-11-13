# UVIX — Objetivos, misiones, tareas e issues
Fecha: 10 de noviembre de 2026. Propuesta v2.

Esta revisión incorpora la visión acordada: UVIX busca un cuidador registrado, recibe encargos, realiza rondas, comunica avisos individuales y generales, conversa y ofrece juegos a quienes acepten, atiende interrupciones conservando su misión, custodia y entrega objetos asignados, y dispone de un flujo específico de dispensación autorizada. Al terminar informa y solicita otro encargo.

Se conservan los IDs de planificación UVIX-01…UVIX-24 y se añaden UVIX-25…UVIX-40. No son números reales de GitHub ni issues publicados. Los hitos M1…M7 de esta revisión sustituyen a los H1…H5 anteriores. No se ha modificado el código del repositorio.

## 1. Objetivo general
Desarrollar una plataforma robótica asistencial para un centro de adultos mayores que ejecute encargos autorizados de cuidadores, recorra áreas permitidas, se relacione con las personas de forma voluntaria y personalizada y conserve el estado de su trabajo durante la jornada, con resultados verificables y recuperación ante interrupciones y fallos.

## 2. Punto de partida verificado
Revisión estática del commit f58e867 de main, no validación de ejecución ni revisión de ramas locales del usuario.

| Capacidad | Evidencia actual | Uso en el plan |
|---|---|---|
| Descripción y control | src/uvix_description y src/uvix_hadware | Reutilizar y verificar; el plugin inspeccionado simula velocidades/posiciones, no demuestra comunicación real |
| Simulación | src/uvix_sim | Entorno inicial para pruebas de comportamiento |
| SLAM/localización | src/uvix_slam | Reutilizar configuración y validar contra el mapa de trabajo |
| Navegación | src/uvix_nav, configuración Nav2 | Reutilizar; añadir control de misiones sobre ella |
| Patrullaje por cobertura | src/uvix_sim/uvix_sim/patrol_node.py | Ya selecciona celdas, consulta rutas y mantiene visitadas/fallos; refactorizar a ronda finita |
| Reinicio de ronda | _select_candidates reinicia visitadas/fallos cuando no quedan pendientes elegibles | Cambiar a cierre con informe; siguiente ronda solo con autorización del supervisor |
| Cobertura | _update_visited usa proximidad; _skip_near_goal también marca visited | Separar realmente visitada, omitida y bloqueada; cobertura espacial no equivale a encontrar personas |
| Identidad, conversación, recordatorios, objetos | No se encontró implementación de estas capacidades en los paquetes propios inspeccionados | Desarrollar módulos nuevos; puede existir trabajo fuera de esta instantánea |

Referencias:
- https://github.com/chinoelmocho/uvix_ws/tree/f58e867dddca515e1bc595b86abb486f25e15fda
- https://github.com/chinoelmocho/uvix_ws/blob/f58e867dddca515e1bc595b86abb486f25e15fda/src/uvix_sim/uvix_sim/patrol_node.py

G0 — Reproducibilidad es el prerrequisito que ya definió Juan: entorno soportado, instalación, compilación y ejecución documentadas. No se considera cerrado por existir un README. Probar navegación y parada en el entorno elegido antes de integrar comportamiento.

## 3. Jerarquía del proyecto
- Objetivo: capacidad y beneficio deseados, por ejemplo comunicar recordatorios.
- Misión: encargo concreto en operación, por ejemplo avisar a María de una actividad.
- Tarea de desarrollo: trabajo necesario para habilitar esa capacidad, por ejemplo registrar entrega y caducidad.
- Issue: unidad implementable y revisable con criterios de aceptación, responsable y dependencia.
- Rama y PR: cambios de código/documentación que resuelven el issue.

No se crea una rama por cada misión que el robot ejecuta: las misiones son datos en tiempo de ejecución. Las ramas son para desarrollar o corregir capacidades.

## 4. Objetivos y criterios de resultado
| Objetivo | Resultado observable |
|---|---|
| O1. Recibir, organizar y completar encargos | Encuentra un cuidador autorizado, confirma el encargo, conserva pendientes, admite interrupciones, informa el resultado y solicita el siguiente |
| O2. Recorrer el complejo mediante rondas controladas | Recorre áreas permitidas, distingue visitadas/omitidas y termina sin repetir indefinidamente; mantiene registro separado de personas |
| O3. Reconocer personas y personalizar el encuentro | Distingue cuidador/residente/desconocido, representa incertidumbre y utiliza solo información del perfil confirmado |
| O4. Comunicar avisos individuales y generales | Entrega el contenido autorizado a la audiencia correcta, respeta vigencia y registra emitido/confirmado/rechazado/no encontrado |
| O5. Conversar y ofrecer juegos con aceptación | Invita, respeta el rechazo o silencio, realiza una actividad y termina sin olvidar el encargo en curso |
| O6. Custodiar y entregar elementos asignados | Relaciona objeto con destinatario, confirma carga y entrega; dispensación de vitaminas usa autorización y evidencia específicas |
| O7. Mantener continuidad y trazabilidad durante la jornada | Conserva registros, atiende fallos/energía, reinicia sin movimiento o liberación automática e informa limitaciones |

No repetir pacientes significa no reiterar una invitación o el mismo aviso ya resuelto dentro de la misma ronda. Una nueva petición de esa persona sí puede atenderse. Rechazar un juego no significa haber rechazado o recibido todos sus recordatorios.

## 5. Misiones operativas que tendrá UVIX
| Misión | Disparador y datos | Fin normal y excepciones |
|---|---|---|
| Buscar cuidador | Inicio de jornada o necesidad de nuevo encargo; zonas autorizadas y tiempo máximo | Encuentro confirmado; si no aparece, espera e informa |
| Realizar ronda | Encargo confirmado; mapa, zonas, round_id y límites | Ronda completa o parcial con informe; no asegura haber encontrado a todas las personas |
| Dar aviso general | Texto, audiencia, vigencia y ronda | Registro por encuentro de la audiencia configurada; no confundir con anuncio por altavoz a todo el edificio |
| Dar aviso individual | Texto, person_id confirmado y plazo | Entregado/rechazado/no encontrado/vencido/fallo, sin revelar contenido a identidad incierta |
| Conversar u ofrecer juego | Ronda social autorizada o solicitud de la persona | Aceptación, sesión y cierre; rechazo/silencio finalizan sin insistencia |
| Entregar objeto | Objeto cargado, destinatario y autorización | Retiro confirmado o incidencia; apertura no equivale a entrega |
| Dispensar unidad asignada | Asignación previa del responsable y validaciones del protocolo | Liberación confirmada o bloqueo/revisión; no inferir ingestión |
| Informar y pedir encargo | Tarea terminal y resultado disponible | Informe al cuidador autorizado y siguiente tarea confirmada |

Por defecto, los avisos generales de esta propuesta se comunican a personas encontradas de la audiencia acordada. Si se quiere anunciar por sala o por altavoz, crear una modalidad separada con sus propios criterios de alcance.

## 6. Tareas de desarrollo y trazabilidad a issues
| Objetivo | Tarea | Issues |
|---|---|---|
| O1 | T1.1 Encontrar cuidador y recibir un encargo confirmado | 29, 30 |
| O1 | T1.2 Definir contratos, prioridades, cola e interrupción/reanudación | 01, 02, 04, 07, 08, 10, 11, 19 |
| O1 | T1.3 Informar resultados y pedir otro encargo | 34 |
| O2 | T2.1 Adaptar navegación y definir destinos/zonas | 05, 06 |
| O2 | T2.2 Convertir patrullaje existente en ronda finita | 25 |
| O2 | T2.3 Registrar atención por ronda sin confundirla con cobertura | 33 |
| O3 | T3.1 Mantener registro, roles y preferencias | 26, 16 |
| O3 | T3.2 Reconocer rostros y manejar identidad incierta | 27 |
| O3 | T3.3 Establecer un encuentro o aproximación válida | 28 |
| O4 | T4.1 Comunicar avisos generales | 31 |
| O4 | T4.2 Buscar destinatario y comunicar aviso individual | 32 |
| O5 | T5.1 Solicitudes, aceptación y sesiones | 09, 12, 13 opcional, 14 |
| O5 | T5.2 Conversación guiada e invitación a actividades | 40 |
| O5 | T5.3 Primer juego completo | 17 |
| O6 | T6.1 Registro de objetos y compartimentos | 35 |
| O6 | T6.2 Entrega y confirmación física | 36 |
| O6 | T6.3 Flujo autorizado de vitaminas | 37 |
| O7 | T7.1 Contexto, energía, fallos y supervisor diario | 03, 20, 21, 38 |
| O7 | T7.2 Persistencia, historial y explicación de decisiones | 15, 18, 22 |
| O7 | T7.3 Pruebas integradas y piloto supervisado | 23, 39, 24 |

## 7. Arquitectura modular propuesta
| Módulo | Responsabilidad |
|---|---|
| uvix_description / hardware / sim / slam | Base robótica y entorno; reutilizar lo existente y validar sus límites |
| uvix_nav | Adaptador hacia Nav2, objetivos, cancelación y resultados |
| uvix_missions | Encargos, reglas, cola, checkpoints y supervisor; único coordinador de navegación |
| uvix_rounds o módulo interno de uvix_missions | Refactor de patrol_node, cobertura finita y progreso de ronda |
| uvix_perception | Señales de voz/visión, tracks y candidatos de identidad; nunca mandos de motor |
| uvix_interaction | Encuentros, turnos, aceptación, diálogos y juegos |
| Servicio local de datos | Personas, roles, recuerdos autorizados, avisos, rondas e inventario |
| uvix_delivery | Compartimentos, sensores y protocolos de entrega/dispensación |
| uvix_interfaces | Contratos compartidos; evitar interfaces propias cuando existan estándares adecuados |

Los nombres nuevos son propuestas; no es necesario crear un paquete por cada fila. Definir primero límites e interfaces. No mantener el patrullaje actual emitiendo objetivos en paralelo con un nuevo gestor de navegación.

## 8. Política inicial de decisiones
1. Validar modo operativo, permisos, localización, telemetría reciente y límites de seguridad.
2. Evaluar restricciones de energía y de la misión actual.
3. Atender encargos confirmados y peticiones de interacción según prioridad e interruptibilidad.
4. Si la tarea es una ronda social, permitir que UVIX invite a participar a personas elegibles; una detección aislada fuera de ese contexto no abre automáticamente una sesión.
5. Interrumpir guardando mission_id, round_id, destino, pendientes y registros; cancelar navegación y verificar detención antes de interactuar.
6. Tras una interacción revalidar el encargo y solicitar una ruta nueva; no reutilizar ciegamente la trayectoria.
7. Al completar la ronda informar; buscar cuidador o esperar según el supervisor y sus límites.

Una cara reconocida no sustituye autorización de entrega sensible. Un mensaje emitido no demuestra comprensión; un objeto liberado no demuestra retiro ni ingestión. Las métricas de reconocimiento, detención, batería y distancia se acuerdan y validan con el hardware, no se fijan como garantías en este documento.

## 9. Entregas ordenadas por dependencias
| Hito | Issues principales | Demostración |
|---|---|---|
| M1. Base para encargos | 01–08, 15, 22 | Recibe una misión de prueba, aplica reglas y muestra estado/resultados |
| M2. Primera ronda con avisos | 09–11, 14, 25, 26, 31–34 | Ronda finita; avisos general e individual; no repetición; interrupción y cierre |
| M3. Personas y cuidador reales | 12, 27–30 | Reconoce con manejo de incertidumbre, encuentra cuidador y confirma un encargo por voz |
| M4. Conversación y juego | 16–18, 40 | Conversa con aceptación, juega y guarda resultado |
| M5. Objetos y dispensador | 35–37 | Carga/entrega trazable y mecanismo autorizado validado primero con material inerte |
| M6. Jornada integrada | 19–21, 23, 38, 39, 24 | Encargo → ronda → informe → siguiente encargo; fallos y reinicio controlados |
| M7. Ampliación opcional | 13 | Gesto visual como entrada adicional |

En M2 se usan encargos, identidades y posiciones simuladas. No se declara reconocimiento facial ni búsqueda humana real hasta M3. Para desplegar avisos individuales con percepción real se deben cerrar 27 y 28 además del issue 32. M5 exige completar los encuentros reales de M3. El piloto UVIX-24 se realiza después de UVIX-39.

M1…M6 son el plan del producto acordado; M7 es opcional. No se asignan fechas hasta medir disponibilidad y velocidad del equipo.

## 10. Primer conjunto de trabajo después de G0
1. Ambos: UVIX-01, contratos y estados; asignar un responsable único.
2. Juan: UVIX-03 → 04/05; compañero: UVIX-02 y 15.
3. Juan: UVIX-06 → 07 → 08 y UVIX-25 al tener sus dependencias; compañero: UVIX-26 y UVIX-09 → 14.
4. Compañero: UVIX-33; ambos integrar UVIX-22.
5. Juan: UVIX-10 → 11; compañero: UVIX-31, con apoyo de Juan para UVIX-32.
6. Juan: UVIX-34. Demostrar M2 antes de integrar reconocimiento real.

Las flechas indican dependencia, no duración de un día. Si una tarea se bloquea, elegir otra con dependencias satisfechas.

## 11. Trabajo en GitHub
- Objetivos O1…O7: etiquetas area:* o campos del tablero; cada uno puede ser un issue padre de seguimiento si conviene.
- Tareas T*: grupos de trabajo dentro del objetivo. No duplicar todos los grupos como issues vacíos.
- Issues UVIX-*: trabajo verificable, responsable único, criterios y evidencia. Estado inicial: propuesto.
- Milestones M*: entregas demostrables. Prioridad y milestone no son lo mismo.
- Ramas: feat/<numero-real>-tema, fix/<numero-real>-tema o refactor/<numero-real>-tema. El prefijo UVIX usado aquí es solo provisional.
- PR hacia main, revisión del compañero, referencia al issue y pruebas pertinentes.
- Tablero: Pendiente → Lista → En curso → En revisión → Terminada; registrar Bloqueada y dependencia.
- Una tarea principal en curso por persona; integrar frecuentemente. No ramas permanentes por persona.
- Cerrar un issue solo cuando su aceptación está demostrada y el PR integrado. Si requiere más de unas dos jornadas efectivas, separar evaluación, implementación o pruebas físicas en subissues.
- Progreso: reportar escenarios demostrados y pendientes, no porcentajes arbitrarios. Los 40 issues no tienen el mismo tamaño.
- Casos reales se validan aparte de pruebas simuladas; aprobar un test con identidad inyectada no prueba un reconocedor facial.

## 12. Catálogo de issues
Se mantienen los 24 issues anteriores con su nuevo objetivo, tarea e hito, y se incorporan 16. Compartido significa colaboración, pero en GitHub debe existir un responsable principal. Las dependencias aluden a IDs de este documento.

### UVIX-01 — Definir contratos de eventos, misiones y estados

- Objetivo padre: O1
- Tarea padre: T1.2

- Hito: M1
- Prioridad: P0
- Responsable propuesto: Compartido
- Rama propuesta: `feat/uvix-01-interfaces`
- Dependencias: Hito de reproducibilidad
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m1`

**Objetivo:** Permitir que percepción, navegación e interacción evolucionen sin depender de variables internas de otros módulos.

**Alcance:** Especificar mensajes/eventos, estados terminales, errores y autoridad de cada módulo. Usar interfaces estándar ROS 2 para navegación cuando correspondan; crear interfaces propias solo para conceptos de UVIX.

**Criterios de aceptación:**

- [ ] Un evento contiene event_id, tipo, fuente, marca temporal, caducidad y confianza cuando aplique; las fuentes comparten una base de tiempo documentada.
- [ ] Una misión contiene mission_id, tipo, destino opcional, prioridad, interruptible, fecha límite y estado; pose y destino especifican frame_id.
- [ ] Los contratos separan persona detectada, solicitud de interacción y usuario identificado; un track visual no identifica a un paciente.
- [ ] Se documentan unidades, QoS por interfaz, reloj de simulación/real y ejemplos válidos e inválidos.

**Evidencia para cerrar:** Validar fixtures de ejemplo; revisar contratos entre ambas personas.

**Ampliación de contratos v2:** incluir round_id, person_id/track_id diferenciados, caregiver_id, notice_id, audiencia, vigencia, item_id y dispense_id cuando aplique. Preparar ejemplos sintéticos de aviso individual y general.

### UVIX-02 — Recibir, validar y deduplicar eventos

- Objetivo padre: O1
- Tarea padre: T1.2

- Hito: M1
- Prioridad: P0
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-02-events`
- Dependencias: UVIX-01
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m1`

**Objetivo:** Evitar que ruido, repeticiones o información antigua produzcan decisiones repetidas.

**Alcance:** Implementar un punto de entrada de eventos con validación, caducidad, deduplicación y limitación de repetición por fuente.

**Criterios de aceptación:**

- [ ] El mismo event_id recibido cinco veces genera como máximo una solicitud.
- [ ] Eventos caducados, sin campos obligatorios o de fuentes no admitidas se rechazan con motivo.
- [ ] Dos eventos válidos de fuentes distintas se conservan sin confundirse.
- [ ] Los límites de repetición son parámetros y se prueban con tiempo controlado.

**Evidencia para cerrar:** Pruebas de duplicados, desorden temporal, caducidad y ráfagas.

### UVIX-03 — Exponer contexto del robot y permisos de movimiento

- Objetivo padre: O7
- Tarea padre: T7.1

- Hito: M1
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-03-robot-context`
- Dependencias: UVIX-01
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m1`

**Objetivo:** Impedir decisiones basadas en un estado desconocido o incompatible con la operación.

**Alcance:** Agregar estado de localización, odometría, disponibilidad de Nav2, modo manual/autónomo, inhibición de movimiento y estado energético. Definir dueño único de los comandos finales; reutilizar la cadena de control existente.

**Criterios de aceptación:**

- [ ] Cada dato incluye validez y antigüedad; desconocido no equivale a correcto.
- [ ] El modo manual y una inhibición activa bloquean nuevas órdenes autónomas.
- [ ] La telemetría vencida impide iniciar misiones que dependan de ella.
- [ ] La inhibición de seguridad prevalece sobre todas las fuentes de velocidad; se documenta su relación con la parada física y el watchdog existentes.

**Evidencia para cerrar:** Simular pérdida de odometría/localización y cambio a manual; verificar permisos y salida de mando.

### UVIX-04 — Implementar la máquina de estados de misión

- Objetivo padre: O1
- Tarea padre: T1.2

- Hito: M1
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-04-mission-states`
- Dependencias: UVIX-01, UVIX-03
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m1`

**Objetivo:** Dar un estado explícito al comportamiento global del robot.

**Alcance:** Implementar IDLE, NAVIGATING, STOPPING, INTERACTING, RESUMING, MANUAL y FAULT con transiciones declaradas. Mantener la misión separada del estado de Nav2.

**Criterios de aceptación:**

- [ ] Solo existe un estado principal activo y una misión activa.
- [ ] Una transición inválida se rechaza y queda registrada.
- [ ] MANUAL y FAULT impiden activación autónoma; salir de FAULT requiere verificar condiciones y autorización definida.
- [ ] La máquina puede probarse con adaptadores simulados, sin motores.

**Evidencia para cerrar:** Tabla de transiciones y pruebas parametrizadas de eventos permitidos y prohibidos.

### UVIX-05 — Crear un adaptador de navegación con resultados explícitos

- Objetivo padre: O2
- Tarea padre: T2.1

- Hito: M1
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-05-navigation-adapter`
- Dependencias: UVIX-01, UVIX-03
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m1`

**Objetivo:** Conectar las misiones con la navegación existente sin repetir la lógica de Nav2.

**Alcance:** Enviar objetivos, consultar progreso, solicitar cancelación y traducir aceptación/rechazo/éxito/fallo/cancelación a estados de UVIX.

**Criterios de aceptación:**

- [ ] Como máximo un objetivo de UVIX queda activo; se correlaciona goal_id con mission_id.
- [ ] Un servidor no disponible provoca un resultado controlado y un plazo acotado.
- [ ] Una solicitud de cancelación no se trata como cancelación confirmada.
- [ ] Un resultado tardío de una misión anterior no altera la misión actual.

**Evidencia para cerrar:** Servidor de acción simulado para éxito, rechazo, cancelación y resultado tardío; luego prueba en simulación ROS.

**Integración existente:** coordinar el refactor de patrol_node (UVIX-25) para que no exista un segundo emisor independiente de objetivos.

### UVIX-06 — Crear un catálogo de destinos semánticos

- Objetivo padre: O2
- Tarea padre: T2.1

- Hito: M1
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-06-semantic-locations`
- Dependencias: UVIX-01
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m1`

**Objetivo:** Traducir 'sala de actividades' a una pose de navegación verificable.

**Alcance:** Definir locations.yaml con identificador, mapa/version, pose, orientación y condición de disponibilidad. Crear destinos de espera e interacción conocidos.

**Criterios de aceptación:**

- [ ] Un ID válido devuelve pose y frame correctos para el mapa actual.
- [ ] Un destino inexistente, deshabilitado o de otro mapa se rechaza.
- [ ] El catálogo se valida al arrancar.
- [ ] Un saludo o una detección de persona sin posición fiable no se convierte automáticamente en un destino.

**Evidencia para cerrar:** Validación de archivo y prueba de selección de tres destinos en simulación.

### UVIX-07 — Implementar la política inicial de selección de tareas

- Objetivo padre: O1
- Tarea padre: T1.2

- Hito: M1
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-07-mission-policy`
- Dependencias: UVIX-02, UVIX-03, UVIX-04, UVIX-06
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m1`

**Objetivo:** Decidir qué hacer y a dónde ir a partir de señales verificadas.

**Alcance:** Aplicar restricciones obligatorias y después prioridades deterministas. Entrada: contexto, petición del operador, agenda, interacción y misión actual. Salida: iniciar, mantener, interrumpir, aplazar o rechazar, con motivo.

**Criterios de aceptación:**

- [ ] La misma entrada produce la misma decisión y código de motivo.
- [ ] Una restricción de seguridad invalida cualquier prioridad de misión.
- [ ] Una misión no interrumpible no se sustituye por un saludo.
- [ ] Sin tarea válida el robot permanece en espera; no patrulla por defecto.
- [ ] La decisión devuelve un destino semántico cuando lo necesita, y no inventa coordenadas.

**Evidencia para cerrar:** Tabla de al menos 12 escenarios, incluidos eventos simultáneos y ausencia de tareas.

### UVIX-08 — Gestionar cola, caducidad y cancelación de misiones

- Objetivo padre: O1
- Tarea padre: T1.2

- Hito: M1
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-08-mission-queue`
- Dependencias: UVIX-04, UVIX-07
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m1`

**Objetivo:** Ordenar solicitudes sin perder tareas ni ejecutarlas tarde.

**Alcance:** Cola acotada con FIFO para empates, prioridad, caducidad, cancelación por ID y aplazamiento.

**Criterios de aceptación:**

- [ ] Dos solicitudes simultáneas no activan dos misiones.
- [ ] Una solicitud vencida no se ejecuta aunque llegue al principio de la cola.
- [ ] Cancelar una misión en espera no afecta a la activa.
- [ ] Un operador puede consultar las tareas aplazadas y sus motivos.
- [ ] La cola llena devuelve un rechazo explícito; no crece sin límite.

**Evidencia para cerrar:** Pruebas de orden, empates, expiración, cancelación y saturación.

### UVIX-09 — Crear una entrada simulada de solicitud de interacción

- Objetivo padre: O5
- Tarea padre: T5.1

- Hito: M2
- Prioridad: P0
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-09-interaction-trigger`
- Dependencias: UVIX-01, UVIX-02
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m2`

**Objetivo:** Probar el comportamiento ante un saludo antes de depender de cámara o reconocimiento de voz.

**Alcance:** Botón de interfaz o herramienta de desarrollo que emita interaction_requested y permita confirmar, rechazar o finalizar la interacción.

**Criterios de aceptación:**

- [ ] La solicitud recorre el mismo canal que usarán voz y visión.
- [ ] Una pulsación genera un único evento válido.
- [ ] Se pueden reproducir saludo durante navegación, saludo en espera y solicitud caducada.
- [ ] El modo de desarrollo queda identificado y configurable.

**Evidencia para cerrar:** Demostración reproducible de los tres escenarios sin hardware de percepción.

### UVIX-10 — Interrumpir una misión y verificar la detención

- Objetivo padre: O1
- Tarea padre: T1.2

- Hito: M2
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-10-mission-interruption`
- Dependencias: UVIX-04, UVIX-05, UVIX-07, UVIX-08, UVIX-09
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m2`

**Objetivo:** Responder a una solicitud sin perder la misión ni empezar una interacción mientras el robot continúa desplazándose.

**Alcance:** Guardar un checkpoint lógico, solicitar cancelación, mantener STOPPING y comprobar odometría reciente bajo umbrales de movimiento durante una ventana configurable. Considerar si la ubicación admite una interacción.

**Criterios de aceptación:**

- [ ] El checkpoint conserva destino, mission_id, plazo, progreso lógico y razón de pausa.
- [ ] La confirmación de cancelación por sí sola no habilita INTERACTING.
- [ ] Con odometría ausente/vencida o plazo de parada superado se pasa a FAULT y se inhibe movimiento autónomo.
- [ ] Una zona no apta aplaza la interacción; no se cambia de rumbo hacia una persona no localizada.
- [ ] Los umbrales de parada se definen y validan en el robot; el evento social no sustituye a la parada física.

**Evidencia para cerrar:** Pruebas con cancelación inmediata, retrasada y fallida; odometría que tarda en llegar a cero y odometría vencida.

### UVIX-11 — Reanudar la misión desde la posición actual

- Objetivo padre: O1
- Tarea padre: T1.2

- Hito: M2
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-11-mission-resume`
- Dependencias: UVIX-06, UVIX-07, UVIX-08, UVIX-10, UVIX-14
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m2`

**Objetivo:** Continuar el trabajo después de una interacción sin repetir acciones ya realizadas.

**Alcance:** Validar checkpoint, plazo, localización, energía, modo y disponibilidad del destino; enviar un nuevo objetivo a Nav2 desde la posición actual.

**Criterios de aceptación:**

- [ ] Una misión vigente se reanuda una sola vez al finalizar la interacción.
- [ ] Una misión vencida, cancelada o completada no se reanuda.
- [ ] No se reutiliza a ciegas la trayectoria anterior; se solicita navegación nuevamente.
- [ ] Un fallo de reanudación produce estado y motivo visibles, sin bucle infinito.

**Evidencia para cerrar:** Prueba de pausa/reanudación con cambios de posición, destino deshabilitado y misión vencida.

### UVIX-12 — Detectar una llamada por voz con vocabulario limitado

- Objetivo padre: O5
- Tarea padre: T5.1

- Hito: M3
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-12-voice-request`
- Dependencias: UVIX-02, UVIX-09, UVIX-14
- Etiquetas sugeridas: `type:feature`, `priority:p1`, `milestone:m3`

**Objetivo:** Permitir que una persona solicite atención de manera natural.

**Alcance:** Elegir un detector local compatible con el micrófono y equipo; comenzar con 'Hola UVIX', confirmación y cancelación. Publicar eventos, nunca comandos de motor.

**Criterios de aceptación:**

- [ ] Se usa un corpus etiquetado de frases objetivo y distractores, incluido audio emitido por el propio robot.
- [ ] Se informa tasa de detección, falsas activaciones y latencia; el umbral objetivo se acuerda antes de cerrar el issue.
- [ ] Una detección incierta pide confirmación o se descarta según la política.
- [ ] Micrófono ausente no bloquea el botón ni otras funciones.
- [ ] No se conserva audio por defecto.

**Evidencia para cerrar:** Informe de evaluación en silencio y ruido representativo; prueba de no autoactivación por la voz de UVIX.

### UVIX-13 — Evaluar y añadir un gesto visual de solicitud de atención

- Objetivo padre: O5
- Tarea padre: T5.1

- Hito: M7
- Prioridad: P2
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-13-visual-request`
- Dependencias: UVIX-02, UVIX-09, UVIX-14
- Etiquetas sugeridas: `type:feature`, `priority:p2`, `milestone:m7`

**Objetivo:** Ofrecer una alternativa a la voz cuando la cámara y el entorno lo permitan.

**Alcance:** Evaluar detección de mano levantada/saludo con seguimiento temporal. Esta es una ampliación opcional; separar evaluación e implementación si supera dos jornadas.

**Criterios de aceptación:**

- [ ] Una persona visible no genera por sí sola una solicitud.
- [ ] Un gesto persistente del mismo track genera una solicitud por ventana de repetición.
- [ ] Se reportan precisión/recobrado o matriz de confusión, latencia y condiciones de prueba.
- [ ] Track ID se mantiene distinto de identidad de paciente.
- [ ] Sin cámara o con datos antiguos, la vía visual se deshabilita sin bloquear el sistema.

**Evidencia para cerrar:** Dataset de prueba autorizado o escenas sintéticas; casos de varias personas y oclusión.

### UVIX-14 — Implementar sesiones de interacción con confirmación y timeout

- Objetivo padre: O5
- Tarea padre: T5.1

- Hito: M2
- Prioridad: P0
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-14-interaction-session`
- Dependencias: UVIX-04, UVIX-09
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m2`

**Objetivo:** Controlar saludo, consentimiento para continuar, actividad y finalización.

**Alcance:** Una sesión a la vez: saludo, ofrecer actividad, esperar respuesta, ejecutar o finalizar. Temporizadores no bloqueantes y eventos session_finished/session_cancelled.

**Criterios de aceptación:**

- [ ] No empieza una actividad hasta recibir permiso de interacción del coordinador, que exige la detención verificada cuando había navegación activa.
- [ ] Rechazo, silencio durante el plazo o petición de finalizar cierran la sesión una sola vez.
- [ ] Una segunda solicitud no crea una sesión concurrente.
- [ ] El robot puede explicar que está ocupado sin prometer una visita futura que no ha registrado.
- [ ] El módulo se prueba con un permiso simulado antes de integrar UVIX-10.

**Evidencia para cerrar:** Pruebas de sí/no/silencio, duplicados y cancelación en cada etapa.

### UVIX-15 — Crear almacenamiento local con migraciones y perfiles ficticios

- Objetivo padre: O7
- Tarea padre: T7.2

- Hito: M1
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-15-local-storage`
- Dependencias: UVIX-01
- Etiquetas sugeridas: `type:feature`, `priority:p1`, `milestone:m1`

**Objetivo:** Conservar datos de manera consistente y permitir evolución del esquema.

**Alcance:** Servicio de almacenamiento local con tablas de usuarios, preferencias, recuerdos autorizados y sesiones; transacciones, migración inicial y datos de ejemplo.

**Criterios de aceptación:**

- [ ] Crear, consultar y actualizar un perfil ficticio conserva un ID estable.
- [ ] Una escritura fallida no deja una sesión parcialmente guardada.
- [ ] Los datos sobreviven al reinicio del servicio.
- [ ] Base real, copias, secretos y medios personales quedan fuera de Git y de logs.
- [ ] Se implementa acceso por rol para operador y proceso de aplicación; se documenta y comprueba el mecanismo de protección del almacenamiento.

**Evidencia para cerrar:** Pruebas con base temporal, migración y fallo de escritura; revisar permisos.

### UVIX-16 — Añadir preferencias y recuerdos autorizados al perfil

- Objetivo padre: O3
- Tarea padre: T3.1

- Hito: M4
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-16-patient-preferences`
- Dependencias: UVIX-14, UVIX-15
- Etiquetas sugeridas: `type:feature`, `priority:p1`, `milestone:m4`

**Objetivo:** Personalizar interacciones a partir de información explícita.

**Alcance:** Selección inicial del perfil por operador; al integrar reconocimiento, usar únicamente identidad confirmada mediante UVIX-27; alta/edición/borrado de preferencias y recuerdos, origen y autorización. Mostrar un saludo o actividad usando ese perfil.

**Criterios de aceptación:**

- [ ] La identidad no se deduce de una voz o track visual.
- [ ] Un recuerdo de un perfil no aparece al seleccionar otro.
- [ ] Al retirar un recuerdo se deja de usar en interacciones posteriores.
- [ ] Un perfil sin preferencias usa un comportamiento genérico.
- [ ] No se guardan todas las conversaciones como 'memoria' automáticamente.

**Evidencia para cerrar:** Prueba con dos perfiles ficticios, cambios de selección y retiro de autorización.

### UVIX-17 — Implementar un primer juego de memoria

- Objetivo padre: O5
- Tarea padre: T5.3

- Hito: M4
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-17-memory-game`
- Dependencias: UVIX-14, UVIX-16
- Etiquetas sugeridas: `type:feature`, `priority:p1`, `milestone:m4`

**Objetivo:** Entregar una actividad completa y accesible que pueda repetirse.

**Alcance:** Juego sencillo de parejas o secuencias, con instrucciones, dificultad explícita, reinicio, abandono y resultado estructurado.

**Criterios de aceptación:**

- [ ] La partida puede completarse y cancelarse desde la interfaz.
- [ ] Registra intentos, aciertos, duración y motivo de fin sin derivar diagnósticos.
- [ ] Los controles e instrucciones se revisan con el responsable de las actividades.
- [ ] El juego no depende de navegación ni publica velocidades.
- [ ] Usa un reloj controlable para probar tiempos sin esperas reales.

**Evidencia para cerrar:** Pruebas de puntuación y estados de partida; demostración de interacción completa.

### UVIX-18 — Guardar resultados y consultar historial de sesiones

- Objetivo padre: O7
- Tarea padre: T7.2

- Hito: M4
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-18-session-history`
- Dependencias: UVIX-15, UVIX-17
- Etiquetas sugeridas: `type:feature`, `priority:p1`, `milestone:m4`

**Objetivo:** Dar continuidad entre sesiones y evitar resultados duplicados.

**Alcance:** Guardar por session_id y profile_id, consultar historial y gestionar errores visibles de persistencia.

**Criterios de aceptación:**

- [ ] Reintentar guardar la misma sesión no duplica resultados.
- [ ] Una sesión interrumpida se distingue de una completada.
- [ ] El historial sigue disponible después de reiniciar.
- [ ] Una avería de almacenamiento no bloquea la capacidad de finalizar la interacción; informa que no se guardó.
- [ ] Se prueba copia/restauración y se documenta retención y borrado de datos.

**Evidencia para cerrar:** Pruebas de idempotencia, base no disponible, aislamiento por perfil y restauración.

### UVIX-19 — Generar misiones desde una agenda

- Objetivo padre: O1
- Tarea padre: T1.2

- Hito: M6
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-19-scheduled-missions`
- Dependencias: UVIX-06, UVIX-08, UVIX-16
- Etiquetas sugeridas: `type:feature`, `priority:p1`, `milestone:m6`

**Objetivo:** Elegir destinos por compromisos configurados, además de órdenes inmediatas.

**Alcance:** Agenda local con horario, destino conocido, perfil opcional, ventana de validez y clave única de ocurrencia.

**Criterios de aceptación:**

- [ ] Un evento programado genera una sola misión por ocurrencia.
- [ ] Tras reiniciar no se duplican ni se ejecutan sin límite todas las citas perdidas.
- [ ] Una cita vencida queda marcada como omitida o pendiente de revisión según política explícita.
- [ ] La zona horaria y el tratamiento de cambios de reloj quedan definidos.
- [ ] Una cita señala un destino configurado, no presupone conocer la posición actual de una persona.

**Evidencia para cerrar:** Pruebas con reloj simulado, reinicio y dos citas coincidentes.

### UVIX-20 — Integrar energía y disponibilidad en las decisiones

- Objetivo padre: O7
- Tarea padre: T7.1

- Hito: M6
- Prioridad: P1
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-20-energy-policy`
- Dependencias: UVIX-03, UVIX-06, UVIX-07
- Etiquetas sugeridas: `type:feature`, `priority:p1`, `milestone:m6`

**Objetivo:** Evitar iniciar tareas que el robot no puede completar con el estado disponible.

**Alcance:** Adaptar la telemetría real de batería; distinguir normal, baja, crítica y desconocida con umbrales e histéresis acordados. Si hay varios packs, evaluar todos los subsistemas críticos.

**Criterios de aceptación:**

- [ ] Batería baja impide iniciar actividades no prioritarias según la política.
- [ ] Un estado crítico o desconocido produce una decisión explícita basada en el hardware, no en un porcentaje supuesto.
- [ ] Solo se envía al robot a espera/carga si el trayecto es viable y tiene margen suficiente; en otro caso se detiene y solicita operador.
- [ ] Los umbrales se prueban sin oscilación entre estados.
- [ ] Llegar al punto de carga no se considera acoplamiento ni carga confirmada; docking queda fuera de este issue.

**Evidencia para cerrar:** Inyección de telemetría normal/baja/crítica/ausente y prueba con el número real de baterías.

### UVIX-21 — Gestionar fallos con reintentos limitados

- Objetivo padre: O7
- Tarea padre: T7.1

- Hito: M6
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-21-fault-recovery`
- Dependencias: UVIX-04, UVIX-05, UVIX-08, UVIX-10, UVIX-11
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m6`

**Objetivo:** Responder a bloqueo de ruta, pérdida de localización o caída de servicios sin quedar en bucles.

**Alcance:** Tabla de errores recuperables/no recuperables, plazos, máximo de reintentos y escalado al operador.

**Criterios de aceptación:**

- [ ] Un destino bloqueado solo reintenta hasta el límite configurado.
- [ ] Pérdida de localización o fallo de parada no produce movimiento de búsqueda sin autorización.
- [ ] Un fallo de interfaz no elimina el control de detención.
- [ ] Un resultado tardío no saca al sistema de FAULT.
- [ ] Cada fallo finaliza, suspende o rechaza la misión con motivo consultable.

**Evidencia para cerrar:** Pruebas de inyección de fallos y recuperación; medir que todos los plazos son acotados.

### UVIX-22 — Registrar y visualizar las razones de cada decisión

- Objetivo padre: O7
- Tarea padre: T7.2

- Hito: M1
- Prioridad: P0
- Responsable propuesto: Compartido
- Rama propuesta: `feat/uvix-22-decision-trace`
- Dependencias: UVIX-01, UVIX-02, UVIX-04
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m1`

**Objetivo:** Entender por qué UVIX fue a un sitio o ignoró/aplazó una solicitud.

**Alcance:** Traza estructurada con evento, misión, estado anterior/nuevo, acción y código de motivo; vista simple del estado, cola y bloqueos.

**Criterios de aceptación:**

- [ ] Cada decisión relevante puede seguirse por event_id y mission_id.
- [ ] Se distingue evento descartado, solicitud aplazada y misión fallida.
- [ ] Los registros excluyen nombres de pacientes, recuerdos, audio y credenciales.
- [ ] El tamaño/retención de logs está limitado.
- [ ] Una vista de desarrollo permite explicar una demostración sin inspeccionar variables internas.

**Evidencia para cerrar:** Reproducir una secuencia y comprobar trazabilidad y ausencia de datos personales.

### UVIX-23 — Validar el escenario completo en simulación

- Objetivo padre: O7
- Tarea padre: T7.3

- Hito: M6
- Prioridad: P0
- Responsable propuesto: Compartido
- Rama propuesta: `feat/uvix-23-autonomy-scenarios`
- Dependencias: UVIX-11, UVIX-14, UVIX-18, UVIX-19, UVIX-20, UVIX-21, UVIX-22
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m6`

**Objetivo:** Probar que los módulos funcionan juntos y los fallos no rompen el comportamiento.

**Alcance:** Suite reproducible con eventos inyectados. La demostración base no depende de detección por voz o visión; esas vías se incorporan después de validar sus issues.

**Criterios de aceptación:**

- [ ] Escenario nominal: ir a destino, recibir saludo, detenerse, interactuar, guardar y reanudar.
- [ ] Casos: saludo duplicado, misión no interrumpible, silencio, batería baja, localización perdida, cancelación fallida y dos personas solicitando atención.
- [ ] Se verifican invariantes: una misión activa, una sesión, ninguna reanudación sin validar y ningún resultado duplicado.
- [ ] Cada ejecución produce evidencia y resultado aprobado/fallido; se declara qué casos siguen pendientes en hardware.

**Evidencia para cerrar:** Ejecutar la suite en el entorno reproducible; adjuntar resultados y vídeo breve del nominal.

### UVIX-24 — Validar reinicio seguro y realizar un piloto supervisado

- Objetivo padre: O7
- Tarea padre: T7.3

- Hito: M6
- Prioridad: P0
- Responsable propuesto: Compartido
- Rama propuesta: `feat/uvix-24-supervised-pilot`
- Dependencias: UVIX-23, UVIX-39
- Etiquetas sugeridas: `type:feature`, `priority:p0`, `milestone:m6`

**Objetivo:** Transferir la demostración al robot real con un procedimiento repetible.

**Alcance:** Arranque sin movimiento automático, recuperación de estado lógico pendiente y autorización de operador para continuar; protocolo de pruebas graduado antes de interacción con usuarios finales.

**Criterios de aceptación:**

- [ ] Reiniciar durante navegación o un juego no provoca movimiento automático ni duplica una sesión.
- [ ] El operador ve la misión pendiente y puede descartarla o revalidarla antes de continuar.
- [ ] Se documentan umbrales reales de parada, límites de velocidad/distancia y respuesta ante desconexión.
- [ ] El piloto usa primero personal del proyecto y perfiles ficticios; luego se acuerdan escenario y actividades con el responsable asistencial.
- [ ] Se registran pruebas aprobadas, fallidas, limitaciones y siguientes issues; 'funciona una vez' no cierra el hito.

**Evidencia para cerrar:** Informe de pruebas físicas supervisadas y lista de defectos reproducibles.

### UVIX-25 — Convertir la patrulla existente en una ronda finita

- Objetivo padre: O2
- Tarea padre: T2.2
- Hito: M2
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `refactor/uvix-25-finite-round`
- Dependencias: UVIX-04, UVIX-05, UVIX-06
- Etiquetas sugeridas: `type:refactor`, `area:o2`, `milestone:m2`

**Alcance:** Reutilizar patrol_node.py para ejecutar un encargo con principio y fin; separar selección de destinos del envío de objetivos, conservando una única autoridad de navegación.

**Criterios de aceptación:**

- [ ] Una ronda tiene round_id, mapa/version, zonas permitidas, criterio de fin, tiempo máximo y resultado.
- [ ] Al terminar una vuelta no reinicia automáticamente ni borra resultados; devuelve éxito, parcial o cancelación.
- [ ] Las zonas visitadas, omitidas y bloqueadas se distinguen: _skip_near_goal ya no aumenta silenciosamente la cobertura visitada.
- [ ] Pausar conserva el recorrido pendiente y reanudar no activa un segundo cliente de navegación.
- [ ] Se comparan rutas y omisiones frente al patrullaje actual en un mapa fijo; visitar una zona no certifica haber observado a todas las personas.

**Evidencia para cerrar:** Ronda con una zona bloqueada, pausa y final único; informe de cobertura sin contar omisiones como visitas.

### UVIX-26 — Registrar personas y roles de cuidador o adulto mayor

- Objetivo padre: O3
- Tarea padre: T3.1
- Hito: M2
- Prioridad: P0
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-26-person-registry`
- Dependencias: UVIX-01, UVIX-15
- Etiquetas sugeridas: `type:feat`, `area:o3`, `milestone:m2`

**Alcance:** Registro local de personas, rol, autorización de operaciones y consentimiento de registro; usar perfiles ficticios inicialmente. Las plantillas faciales se incorporan en UVIX-27.

**Criterios de aceptación:**

- [ ] Un ID estable identifica a la persona sin depender del nombre mostrado.
- [ ] Crear, modificar y desactivar una persona conserva integridad de sus referencias.
- [ ] El rol determina qué encargos puede autorizar; la interfaz muestra la identidad seleccionada.
- [ ] Las pruebas usan datos ficticios; no se suben imágenes ni plantillas biométricas a Git.
- [ ] Se define alta/baja autorizada y la eliminación o retención de datos relacionados.

**Evidencia para cerrar:** Dos cuidadores y tres residentes ficticios; pruebas de permisos y desactivación.

### UVIX-27 — Reconocer rostros registrados y representar la incertidumbre

- Objetivo padre: O3
- Tarea padre: T3.2
- Hito: M3
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-27-face-identity`
- Dependencias: UVIX-02, UVIX-26
- Etiquetas sugeridas: `type:feat`, `area:o3`, `milestone:m3`

**Alcance:** Evaluar reconocimiento facial local y alta de plantillas autorizadas. Distinguir detección, track, candidato de identidad y confirmación. No usar la cara como autorización suficiente para dispensar vitaminas.

**Criterios de aceptación:**

- [ ] El resultado puede ser identificado, desconocido, ambiguo o dato vencido; nunca se fuerza un nombre.
- [ ] Se informa tasa de falsos aceptados/rechazados y latencia bajo iluminación y ángulos representativos; los criterios de aprobación se acuerdan antes de evaluar.
- [ ] Identidades ambiguas solicitan una confirmación alternativa y no generan mensajes personales.
- [ ] Al cambiar el track o vencer la observación se revalida la identidad.
- [ ] Se documenta el riesgo de foto/reproducción y la confirmación adicional exigida para acciones sensibles; las plantillas están protegidas y pueden retirarse.

**Evidencia para cerrar:** Evaluación con participantes autorizados, desconocidos y dos caras simultáneas; informe de limitaciones.

### UVIX-28 — Establecer un encuentro con una persona localizada

- Objetivo padre: O3
- Tarea padre: T3.3
- Hito: M3
- Prioridad: P1
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-28-person-encounter`
- Dependencias: UVIX-03, UVIX-05, UVIX-06, UVIX-27
- Etiquetas sugeridas: `type:feat`, `area:o3`, `milestone:m3`

**Alcance:** Determinar si se puede conversar desde la posición actual o aproximarse a un punto de interacción. Definir fuente de distancia/profundidad antes de implementar aproximación.

**Criterios de aceptación:**

- [ ] Una detección 2D sin distancia/transformación fiable no se convierte directamente en coordenadas de navegación.
- [ ] Si existe localización fiable, se calcula un punto accesible fuera de la posición ocupada por la persona.
- [ ] Se verifica vigencia del track, pose, ruta, separación acordada y lugar apto.
- [ ] Si la persona se mueve, se pierde o la ruta se bloquea, se cancela o replantea de manera acotada.
- [ ] Con sensores insuficientes, el comportamiento documentado es detenerse a distancia válida o pedir que se acerque; no se declara aproximación autónoma implementada.

**Evidencia para cerrar:** Persona quieta, en movimiento, ocluida y al otro lado de un obstáculo; evaluación física supervisada.

### UVIX-29 — Buscar a un cuidador y solicitar un encargo

- Objetivo padre: O1
- Tarea padre: T1.1
- Hito: M3
- Prioridad: P1
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-29-find-caregiver`
- Dependencias: UVIX-14, UVIX-25, UVIX-27, UVIX-28
- Etiquetas sugeridas: `type:feat`, `area:o1`, `milestone:m3`

**Alcance:** Recorrer zonas autorizadas del mapa para localizar un cuidador registrado, establecer el encuentro y pedir una tarea.

**Criterios de aceptación:**

- [ ] La búsqueda tiene zonas, presupuesto de tiempo/reintentos y resultado: encontrado, no encontrado, cancelado o fallo.
- [ ] Solo una identidad confirmada con rol cuidador inicia el intercambio de encargos autorizados.
- [ ] Si no encuentra a nadie, informa y espera o usa un punto acordado; no recorre indefinidamente.
- [ ] Si detecta varios cuidadores aplica una selección explícita y conserva un interlocutor activo.
- [ ] Puede probarse primero con detecciones/identidades inyectadas; la entrega final exige validación con percepción real.

**Evidencia para cerrar:** Mapa con cuidador visible, ausente y persona no autorizada; búsqueda termina en los tres casos.

### UVIX-30 — Recibir y confirmar encargos individuales o generales

- Objetivo padre: O1
- Tarea padre: T1.1
- Hito: M3
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-30-caregiver-orders`
- Dependencias: UVIX-08, UVIX-12, UVIX-14, UVIX-26
- Etiquetas sugeridas: `type:feat`, `area:o1`, `milestone:m3`

**Alcance:** Convertir una solicitud del cuidador a un encargo estructurado. Empezar por entrada de texto/formulario y añadir voz transcrita de vocabulario acotado; configurar transcripción y evaluación como subtarea explícita.

**Criterios de aceptación:**

- [ ] Cada encargo incluye ID, autor confirmado, tipo, mensaje/acción, destinatario o audiencia, vigencia, prioridad e interruptibilidad.
- [ ] El robot repite o muestra lo entendido y solo lo activa tras confirmación.
- [ ] Si falta destinatario, contenido u horario necesario, pide el dato; no lo inventa.
- [ ] Una orden repetida o confirmación duplicada no crea dos encargos.
- [ ] Se validan por texto y por voz ejemplos de aviso individual y general; corregir un nombre antes de confirmar no envía el aviso al candidato anterior.

**Evidencia para cerrar:** Corpus acotado con órdenes claras, nombres ambiguos, correcciones y cancelaciones; registro del encargo confirmado.

### UVIX-31 — Ejecutar avisos generales durante una ronda

- Objetivo padre: O4
- Tarea padre: T4.1
- Hito: M2
- Prioridad: P0
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-31-general-notices`
- Dependencias: UVIX-08, UVIX-14, UVIX-25, UVIX-33
- Etiquetas sugeridas: `type:feat`, `area:o4`, `milestone:m2`

**Alcance:** Comunicar un mismo aviso a la audiencia configurada durante una ronda. La propuesta inicial es avisar a las personas encontradas; anuncios por sala son una modalidad separada.

**Criterios de aceptación:**

- [ ] El aviso conserva notice_id, contenido confirmado, audiencia y vigencia.
- [ ] Cada encuentro registra emitido, confirmado por la persona si corresponde, rechazado o no entregado; emitir no demuestra comprensión.
- [ ] El mismo aviso no se vuelve a ofrecer a la misma persona durante la ronda salvo que esta lo solicite.
- [ ] Un aviso vencido deja de emitirse incluso después de una pausa.
- [ ] El cierre informa alcance observado y pendientes; no afirma que todo el complejo recibió el aviso.

**Evidencia para cerrar:** Ronda con tres personas, un rechazo, reencuentro de una persona y caducidad durante la ejecución.

### UVIX-32 — Buscar destinatario y entregar un aviso individual

- Objetivo padre: O4
- Tarea padre: T4.2
- Hito: M2
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-32-individual-notices`
- Dependencias: UVIX-08, UVIX-14, UVIX-25, UVIX-26, UVIX-33
- Etiquetas sugeridas: `type:feat`, `area:o4`, `milestone:m2`

**Alcance:** Encargo dirigido a un ID concreto. En M2 se prueba con identidad y encuentro simulados; la operación real incorpora UVIX-27 y 28 como condición de habilitación.

**Criterios de aceptación:**

- [ ] El contenido privado solo se comunica tras confirmar el destinatario; desconocido o ambiguo no reciben el mensaje.
- [ ] La búsqueda tiene límite y distingue entregado, rechazado, no encontrado, vencido y fallo.
- [ ] Un aviso entregado no se repite por reconexión o reintento del comando.
- [ ] Una interrupción conserva destinatario y progreso de búsqueda.
- [ ] Las pruebas M2 usan eventos simulados explícitos; la entrega real exige además pasar los criterios de reconocimiento y encuentro.

**Evidencia para cerrar:** Destinatario correcto, homónimo, identidad incierta, ausencia y reinicio antes/después de entregar.

### UVIX-33 — Registrar personas atendidas por ronda sin duplicarlas

- Objetivo padre: O2
- Tarea padre: T2.3
- Hito: M2
- Prioridad: P0
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-33-round-contact-ledger`
- Dependencias: UVIX-15, UVIX-25, UVIX-26
- Etiquetas sugeridas: `type:feat`, `area:o2`, `milestone:m2`

**Alcance:** Separar cobertura espacial de atención a personas. Mantener registros por round_id y person_id, o track temporal sin afirmar identidad.

**Criterios de aceptación:**

- [ ] Se distinguen invitado, aceptó, atendido, rechazó, sin respuesta y pendiente; el estado no se infiere de haber pasado cerca.
- [ ] Reencontrar a una persona identificada no dispara otra invitación o aviso ya resuelto en la misma ronda.
- [ ] Una petición iniciada por la persona puede abrir una nueva interacción sin borrar el registro anterior.
- [ ] Con identidad desconocida se aplica un intervalo conservador por track y se documenta que no hay garantía de deduplicación entre tracks perdidos.
- [ ] Ronda nueva crea un contexto nuevo; la persistencia evita duplicados tras reiniciar la misma ronda.
- [ ] Rechazar un juego no marca un aviso pendiente como entregado; se conserva también el estado por notice_id/actividad.

**Evidencia para cerrar:** Reencuentros, pérdida de track, rechazo de juego con aviso pendiente y reinicio de ronda.

### UVIX-34 — Informar resultado y solicitar el siguiente encargo

- Objetivo padre: O1
- Tarea padre: T1.3
- Hito: M2
- Prioridad: P0
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-34-mission-report`
- Dependencias: UVIX-08, UVIX-22, UVIX-25, UVIX-31, UVIX-32
- Etiquetas sugeridas: `type:feat`, `area:o1`, `milestone:m2`

**Alcance:** Producir un informe de cierre con cobertura, entregas, rechazos, ausencias y fallos. El punto de entrega de informe es configurable.

**Criterios de aceptación:**

- [ ] Cada encargo emite un solo cierre con su resultado y pendientes.
- [ ] Un encargo parcial no se anuncia como completado sin pendientes.
- [ ] Puede presentar el informe en la interfaz del cuidador en M2; buscarlo físicamente se habilita con UVIX-29.
- [ ] La siguiente tarea no empieza sin autorización/agenda vigente y contexto válido.
- [ ] El informe evita exponer mensajes privados a personas no autorizadas.

**Evidencia para cerrar:** Finalizar ronda completa y parcial, consultar informe y confirmar una tarea siguiente.

### UVIX-35 — Registrar custodia de objetos y destinatarios

- Objetivo padre: O6
- Tarea padre: T6.1
- Hito: M5
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-35-item-custody`
- Dependencias: UVIX-15, UVIX-26, UVIX-30
- Etiquetas sugeridas: `type:feat`, `area:o6`, `milestone:m5`

**Alcance:** Registrar quién carga un objeto, a quién pertenece, compartimento, vigencia y estado. Empezar con objetos de prueba y compartimentos simulados.

**Criterios de aceptación:**

- [ ] El cuidador asigna un item_id a un destinatario y un compartimento sin colisiones.
- [ ] Se distinguen asignado, cargado, reservado, entregado, retirado e incidencia.
- [ ] Una carga no confirmada no se anuncia como objeto disponible.
- [ ] El estado persiste y toda modificación queda asociada a un operador autorizado.
- [ ] Un residente no puede consultar el contenido asignado a otro.

**Evidencia para cerrar:** Asignación, carga, cambio de destinatario autorizado, cancelación y reinicio.

### UVIX-36 — Entregar un objeto con confirmación y control del compartimento

- Objetivo padre: O6
- Tarea padre: T6.2
- Hito: M5
- Prioridad: P1
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-36-item-handover`
- Dependencias: UVIX-10, UVIX-27, UVIX-28, UVIX-32, UVIX-35
- Etiquetas sugeridas: `type:feat`, `area:o6`, `milestone:m5`

**Alcance:** Protocolo de entrega con destinatario confirmado, permiso, apertura controlada y evidencia del resultado; interfaz de hardware documentada antes de conectar actuadores.

**Criterios de aceptación:**

- [ ] La apertura requiere robot detenido, destinatario confirmado, objeto asignado y autorización de entrega.
- [ ] Reconocer una cara o abrir una puerta no marca por sí solo el objeto como entregado.
- [ ] Se elige y documenta confirmación de retiro por sensor/operador; ausencia de confirmación deja resultado incierto.
- [ ] Repetir el comando o reiniciar no abre/libera otra vez automáticamente.
- [ ] Atasco, puerta abierta o rechazo llevan a incidencia o devolución al cuidador, sin reintentos físicos ilimitados.

**Evidencia para cerrar:** Primero simulador, después objetos inertes: retiro confirmado, rechazo, sensor fallido y desconexión durante apertura.

### UVIX-37 — Definir y validar el flujo autorizado de dispensación de vitaminas

- Objetivo padre: O6
- Tarea padre: T6.3
- Hito: M5
- Prioridad: P1
- Responsable propuesto: Compartido
- Rama propuesta: `feat/uvix-37-authorized-dispensing`
- Dependencias: UVIX-35, UVIX-36
- Etiquetas sugeridas: `type:feat`, `area:o6`, `milestone:m5`

**Alcance:** Separar dispensación de objetos ordinarios. Definir con el responsable el contenido previamente preparado y asignado, autorización y evidencia del mecanismo; UVIX no decide dosis ni indicaciones.

**Criterios de aceptación:**

- [ ] El responsable confirma destinatario, unidad preparada, ventana y autorización; la cara por sí sola no autoriza la liberación.
- [ ] Un dispense_id solo puede ejecutarse una vez; reinicio o timeout ambiguo bloquea reintento automático y exige revisión.
- [ ] Se define cómo se confirma la unidad liberada, un atasco o una liberación incierta.
- [ ] No se registra ingestión por observar apertura, entrega o retiro.
- [ ] Se valida primero con unidades inertes; el hito de software no implica autorización de uso con personas.
- [ ] Si las decisiones de mecanismo, autorización o supervisión no están resueltas, el issue se mantiene bloqueado.

**Evidencia para cerrar:** Revisión del protocolo con el responsable y pruebas del mecanismo con material inerte y fallos inyectados.

### UVIX-38 — Coordinar una jornada de encargos con límites y recuperación

- Objetivo padre: O7
- Tarea padre: T7.1
- Hito: M6
- Prioridad: P1
- Responsable propuesto: A
- Rama propuesta: `feat/uvix-38-daily-supervisor`
- Dependencias: UVIX-19, UVIX-20, UVIX-21, UVIX-29, UVIX-30, UVIX-34
- Etiquetas sugeridas: `type:feat`, `area:o7`, `milestone:m6`

**Alcance:** Orquestar inicio de jornada, búsqueda de cuidador, encargo, informe y siguiente tarea; incluir disponibilidad, mantenimiento y fin de jornada.

**Criterios de aceptación:**

- [ ] El ciclo tiene estados y condiciones de salida; no inicia patrullas infinitas cuando no hay cuidador o tarea.
- [ ] Respeta modo manual, detención, energía y horarios.
- [ ] Al reiniciar recupera tareas y registros, pero no mueve ni dispensa hasta revalidación y autorización definida.
- [ ] La batería baja aplica la política probada; llegar a la estación no equivale a cargar.
- [ ] Se establece una duración de prueba de jornada y métricas antes de ejecutarla; no se declara funcionamiento todo el día sin medirlo.

**Evidencia para cerrar:** Simulación acelerada de jornada y prueba física de duración acordada con número de encargos, incidencias y energía.

### UVIX-39 — Validar la visión completa y sus excepciones

- Objetivo padre: O7
- Tarea padre: T7.3
- Hito: M6
- Prioridad: P1
- Responsable propuesto: Compartido
- Rama propuesta: `test/uvix-39-complete-scenarios`
- Dependencias: UVIX-18, UVIX-23, UVIX-27, UVIX-28, UVIX-29, UVIX-30, UVIX-31, UVIX-32, UVIX-33, UVIX-34, UVIX-36, UVIX-37, UVIX-38, UVIX-40
- Etiquetas sugeridas: `type:test`, `area:o7`, `milestone:m6`

**Alcance:** Escenarios de aceptación desde buscar cuidador hasta informar y pedir otra tarea; las entregas físicas se prueban con objetos/unidades inertes.

**Criterios de aceptación:**

- [ ] Escenario nominal: cuidador → encargo general/individual → ronda → interacción/juego → interrupción → reanudación → informe.
- [ ] Demostrar que no se repite la invitación ni el mismo aviso a un residente en la misma ronda.
- [ ] Excepciones: cuidador ausente, identidad incierta, residente que rechaza, zona bloqueada, aviso vencido y batería baja.
- [ ] Entrega: destinatario incorrecto, retiro no confirmado, reinicio durante liberación y prevención de doble dispensación.
- [ ] Los resultados distinguen pruebas simuladas, físicas y pendientes; cada objetivo O1–O7 tiene evidencia trazable.

**Evidencia para cerrar:** Matriz objetivo/escenario/resultado y demostración supervisada; UVIX-24 cierra el piloto después de esta validación.

### UVIX-40 — Mantener conversación guiada e invitar a juegos

- Objetivo padre: O5
- Tarea padre: T5.2
- Hito: M4
- Prioridad: P1
- Responsable propuesto: B
- Rama propuesta: `feat/uvix-40-guided-conversation`
- Dependencias: UVIX-12, UVIX-14, UVIX-16, UVIX-17
- Etiquetas sugeridas: `type:feat`, `area:o5`, `milestone:m4`

**Alcance:** Diálogo inicial sobre temas y actividades configurados: saludo, preferencia, invitación a juego, rechazo y despedida; conservar contexto de la sesión.

**Criterios de aceptación:**

- [ ] Durante una ronda social autorizada el robot puede ofrecer una conversación una vez por encuentro elegible, sin exigir que la persona salude primero.
- [ ] Antes de continuar comprueba aceptación; no insistir, cambiar de tema, terminar y silencio tienen respuestas definidas.
- [ ] Puede ofrecer/iniciar un juego sin perder la misión pausada.
- [ ] El contexto se limita a la sesión y a recuerdos explícitamente autorizados; no guarda por defecto audio o toda la conversación.
- [ ] Una pregunta no soportada recibe una respuesta clara o derivación al cuidador; no genera nuevas órdenes de movimiento ni dispensación.

**Evidencia para cerrar:** Guiones de aceptación/rechazo, cambio a juego, silencio y pregunta fuera de alcance; revisión de accesibilidad.

## 13. Primer escenario de aceptación del producto
En un mapa de prueba con tres residentes ficticios, un encargo contiene un aviso general y otro dirigido a una persona concreta. UVIX ejecuta una ronda finita, registra las zonas omitidas, comunica los avisos a sus destinatarios elegibles y evita repetirlos al reencontrarse con una persona. Durante el recorrido recibe una petición de interacción, detiene y verifica el movimiento, atiende y retoma lo pendiente. Al terminar informa quién recibió/rechazó/no recibió cada aviso y qué zonas quedaron pendientes. Una ronda espacial terminada puede tener avisos pendientes.

En M2 se usan entradas simuladas. En M3 se sustituye esa entrada por reconocimiento y solicitud real del cuidador sin cambiar el contrato de misión. M4 agrega diálogo y juegos; M5, entregas físicas; M6, el ciclo completo de jornada.

## 14. Decisiones que se resuelven dentro de los issues correspondientes
- Cámara, profundidad disponible y micrófono reales; condiciones de iluminación/ruido.
- Confirmación alternativa para identidad incierta y autorización de cuidadores.
- Mensajes generales por persona frente a anuncio por sala: aquí se propone por persona encontrada.
- Condición exacta de cobertura y zonas prohibidas; no prometer encontrar a todos en una vuelta.
- Criterios medidos de reconocimiento, parada, separación, batería y duración de jornada.
- Mecanismo de compartimentos/dispensador, evidencia de retiro/liberación y responsable de autorización.
- Alcance inicial de conversación guiada; conversación abierta y adaptación avanzada quedan como extensiones.
- Docking/carga automática: proyecto adicional; llegar a un punto de carga no verifica carga eléctrica.

## 15. Referencia técnica
Nav2 Simple Commander permite enviar objetivos, consultar feedback y resultados y solicitar cancelación. La supervisión de misión, autorización, detención observada, rondas y avisos es responsabilidad de la aplicación UVIX.
https://api.nav2.org/nav2-humble/html/md_nav2_simple_commander_README.html

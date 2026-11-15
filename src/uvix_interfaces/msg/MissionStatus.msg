# msg/MissionStatus.msg
std_msgs/Header header
string mission_id
string mission_type

uint8 STATE_UNKNOWN=0
uint8 STATE_QUEUED=1           # registrada, esperando turno u hora
uint8 STATE_EXECUTING=2
uint8 STATE_PAUSED=3           # ej. fue a cargar
uint8 STATE_COMPLETED=4
uint8 STATE_PARTIAL=5          # atendió a algunos pacientes, no a todos
uint8 STATE_FAILED=6
uint8 STATE_CANCELED=7
uint8 state

uint16 code                    # motivo si falló o fue rechazada
string detail

float32 progress               # 0.0 a 1.0
string current_target          # person_id que atiende ahora; vacío si ninguno
string[] completed_targets     # pacientes ya atendidos
string[] failed_targets        # pacientes no encontrados o no atendidos

builtin_interfaces/Time started   # cero si no ha empezado
builtin_interfaces/Time finished  # cero si no ha terminado

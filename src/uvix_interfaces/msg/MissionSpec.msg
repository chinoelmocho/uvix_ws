# msg/MissionSpec.msg
string mission_id
string mission_type
string description

uint8 ORIGIN_UNKNOWN=0
uint8 ORIGIN_STAFF=1         # orden de un encargado
uint8 ORIGIN_PATIENT=2       # petición de un paciente
uint8 ORIGIN_DETECTION=3     # el robot detectó algo (caída)
uint8 ORIGIN_SCHEDULE=4      # programada por horario
uint8 ORIGIN_SYSTEM=5        # interna (ir a cargar)
uint8 origin
string request_id            # vacío si no vino de una orden
string requested_by          # person_id; vacío en DETECTION y SYSTEM

string[] target_person_ids
string target_location

uint8 priority               # la fija el manager, no el solicitante
bool interruptible           # ¿puede pausarse por algo más urgente?
float32 max_duration_s       # 0.0 = sin límite; para bailes y charlas
builtin_interfaces/Time deadline

bool report_on_failure       # enviar informe si no encuentra a alguien
string report_to             # person_id que recibe el informe
uint8 PRIORITY_EMERGENCY=1   # caída, petición de ayuda
uint8 PRIORITY_CARE=2        # tareas ordenadas por personal
uint8 PRIORITY_SOCIAL=3      # peticiones simples de pacientes
uint8 PRIORITY_BACKGROUND=4  # ir a cargar, rondas sin urgencia
uint8 priority
uvix_interface/KeyValue[] parameters

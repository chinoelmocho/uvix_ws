# msg/MissionSpec.msg
# Definición completa de una misión.
# La prioridad la fija el mission_manager, nunca el solicitante.

# Catálogo de tipos; el manager rechaza otros con CODE_UNKNOWN_MISSION_TYPE
string TYPE_ATTEND_FALL="attend_fall"
string TYPE_ATTEND_HELP_REQUEST="attend_help_request"
string TYPE_DISPENSE_VITAMINS="dispense_vitamins"
string TYPE_DELIVER_ITEM="deliver_item"
string TYPE_REMINDER_ROUND="reminder_round"
string TYPE_DANCE="dance"
string TYPE_CHAT="chat"
string TYPE_GO_CHARGE="go_charge"

string mission_id            # lo asigna el manager; vacío en la petición
string mission_type          # una de las constantes TYPE_
string description

uint8 ORIGIN_UNKNOWN=0
uint8 ORIGIN_STAFF=1         # orden de un encargado
uint8 ORIGIN_PATIENT=2       # petición de un paciente
uint8 ORIGIN_DETECTION=3     # el robot detectó algo (caída)
uint8 ORIGIN_SCHEDULE=4      # programada por horario
uint8 ORIGIN_SYSTEM=5        # interna (ir a cargar)
uint8 origin
string request_id            # vincula con IdentityVerification; vacío si no vino de una orden
string requested_by          # person_id DECLARADO; el manager lo compara con la
                             # verificación (GetRequestIdentity). Vacío en DETECTION,
                             # SCHEDULE y SYSTEM. El rol se consulta con GetPerson.

string[] target_person_ids
string target_location

uint8 PRIORITY_UNSET=0       # valor en la petición; el manager lo sobrescribe
uint8 PRIORITY_EMERGENCY=1   # caída, petición de ayuda, batería crítica
uint8 PRIORITY_CARE=2        # tareas ordenadas por personal
uint8 PRIORITY_SOCIAL=3      # peticiones simples de pacientes
uint8 PRIORITY_BACKGROUND=4  # ir a cargar, rondas sin urgencia
uint8 priority

bool interruptible           # ¿puede pausarse por algo más urgente?
float32 max_duration_s       # 0.0 = sin límite; para bailes y charlas
builtin_interfaces/Time start_time  # cero = empezar ya; hora para ORIGIN_SCHEDULE
builtin_interfaces/Time deadline    # cero = sin plazo

bool report_on_failure       # enviar informe si no encuentra a alguien
string report_to             # person_id que recibe el informe

uvix_interfaces/KeyValue[] parameters

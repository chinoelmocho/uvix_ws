# msg/ClarificationRequest.msg
# La respuesta del usuario llega como un nuevo UserCommand con el mismo session_id.
std_msgs/Header header
string request_id          # orden que se quiere aclarar
string session_id

uint8 REASON_UNKNOWN=0
uint8 REASON_AMBIGUOUS=1
uint8 REASON_MISSING_PARAMETER=2
uint8 REASON_LOW_CONFIDENCE=3
uint8 REASON_CONFIRMATION=4
uint8 reason

string question            # texto para el usuario
string missing_key         # parámetro que falta; vacío si no aplica
string[] options           # vacío si la respuesta es libre
float32 timeout_s          # tiempo máximo de espera

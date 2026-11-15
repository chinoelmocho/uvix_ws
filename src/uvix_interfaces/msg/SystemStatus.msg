std_msgs/Header header

uint8 STATE_UNKNOWN=0
uint8 STATE_BOOTING=1
uint8 STATE_SELF_CHECK=2
uint8 STATE_READY=3
uint8 STATE_DEGRADED=4         # funciona con limitaciones
uint8 STATE_ERROR=5
uint8 STATE_SHUTTING_DOWN=6
uint8 state

string[] failed_components     # vacío si todo está bien
string detail

# msg/CommandEvent.msg
std_msgs/Header header
string event_id            # siempre presente
string request_id
string mission_id          # vacío si aún no hay misión
string source              # nodo que emite el evento

uint8 STATE_UNKNOWN=0
uint8 STATE_RECEIVED=1
uint8 STATE_INTERPRETED=2
uint8 STATE_NEEDS_CLARIFICATION=3
uint8 STATE_REGISTERED=4
uint8 STATE_REJECTED=5
uint8 STATE_EXECUTING=6
uint8 STATE_COMPLETED=7
uint8 STATE_FAILED=8
uint8 STATE_CANCELED=9
uint8 state

uint16 code                # mismos códigos que RegisterMission
string detail

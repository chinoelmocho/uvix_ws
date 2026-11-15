# msg/RobotActivity.msg
std_msgs/Header header

uint8 MODE_IDLE=0
uint8 MODE_MISSION=1           # tarea de cuidado (prioridad 2)
uint8 MODE_SOCIAL=2            # baile, charla (prioridad 3)
uint8 MODE_EMERGENCY=3         # atendiendo una emergencia (prioridad 1)
uint8 MODE_CHARGING=4          # yendo a cargar o cargando
uint8 mode

string mission_id              # vacío si no hay misión
string mission_type            # constantes TYPE_ de MissionSpec
string target_person_id        # vacío si no aplica

uint8 ACTIVITY_NONE=0
uint8 ACTIVITY_NAVIGATING=1
uint8 ACTIVITY_SEARCHING_PERSON=2
uint8 ACTIVITY_IDENTIFYING=3
uint8 ACTIVITY_CONVERSING=4
uint8 ACTIVITY_WAITING=5
uint8 ACTIVITY_DOCKING=6
uint8 ACTIVITY_DANCING=7
uint8 ACTIVITY_DISPENSING=8
uint8 ACTIVITY_DELIVERING=9
uint8 ACTIVITY_CHARGING=10
uint8 ACTIVITY_ATTENDING_EMERGENCY=11
uint8 activity

string description

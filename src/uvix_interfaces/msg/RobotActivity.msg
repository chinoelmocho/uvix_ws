std_msgs/Header header
uint8 mode                 # constantes de SystemStatus

string mission_id          # vacío si no hay misión
string mission_type        # "deliver_medication", "reminder_round"
string target_person_id    # vacío si no aplica

uint8 ACTIVITY_NONE=0
uint8 ACTIVITY_NAVIGATING=1
uint8 ACTIVITY_SEARCHING_PERSON=2
uint8 ACTIVITY_IDENTIFYING=3
uint8 ACTIVITY_CONVERSING=4
uint8 ACTIVITY_WAITING=5
uint8 ACTIVITY_DOCKING=6
uint8 activity

string description      

# msg/PowerStatus.msg
std_msgs/Header header
sensor_msgs/BatteryState[] batteries
uint32[] charge_cycles         # uno por batería
float32 total_percentage       # 0.0 a 1.0
float32 estimated_runtime_s    # -1.0 si se desconoce

uint8 LEVEL_UNKNOWN=0
uint8 LEVEL_OK=1
uint8 LEVEL_LOW=2              # conviene ir a cargar
uint8 LEVEL_CRITICAL=3         # ir a cargar ya
uint8 level

bool docked
bool charging
bool needs_charge
bool needs_replacement         # por ciclos o salud

std_msgs/Header header
string alert_id
uint8 LEVEL_INFO=0           # informe de misión
uint8 LEVEL_WARNING=1        # paciente no encontrado
uint8 LEVEL_EMERGENCY=2      # caída, petición de ayuda
uint8 level
string mission_id            # vacío si no viene de una misión
string about_person_id       # de quién trata; vacío si no aplica
string notify_person_id      # a quién avisar
string location
string text

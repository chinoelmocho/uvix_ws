# Datos consultables de una persona registrada.
# No contiene imágenes, plantillas faciales ni verificaciones de identidad.

string person_id
string display_name

uint8 ROLE_UNKNOWN=0
uint8 ROLE_PATIENT=1
uint8 ROLE_STAFF=2
uint8 ROLE_ADMIN=3
uint8 role

# Una persona desactivada conserva su registro,
# pero no puede autorizar nuevas operaciones.
bool active

# Preferencias de interacción; no conceden permisos.
uvix_interfaces/KeyValue[] preferences

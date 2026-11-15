# msg/IdentityVerification.msg
# Resultado de verificar QUIÉN hizo una petición.
# Lo emite SOLO el componente de identificación (fuente confiable),
# nunca el command_interpreter ni el solicitante.
#
#   person_id        -> ¿qué persona se está identificando?
#   identity_status  -> ¿se verificó que realmente es esa persona?
#   (el rol NO va aquí: se consulta en el registro con GetPerson)

std_msgs/Header header         # stamp = momento de la verificación
string request_id              # petición a la que corresponde
string person_id               # vacío si IDENTITY_UNKNOWN

uint8 IDENTITY_UNKNOWN=0       # no se reconoce a nadie registrado
uint8 IDENTITY_CANDIDATE=1     # hipótesis; no basta para autorizar
uint8 IDENTITY_VERIFIED=2      # confirmado por el componente confiable
uint8 identity_status

uint8 METHOD_NONE=0
uint8 METHOD_FACE=1
uint8 METHOD_VOICE=2
uint8 METHOD_FACE_AND_VOICE=3
uint8 METHOD_BADGE=4           # tarjeta / NFC del personal
uint8 method
float32 confidence             # 0.0 a 1.0

string track_id                # seguimiento visual usado; vacío si no aplica
string verifier                # nodo que hizo la verificación
builtin_interfaces/Time valid_until  # después de esto ya no sirve para autorizar

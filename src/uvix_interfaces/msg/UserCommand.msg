# msg/UserCommand.msg
std_msgs/Header header

string request_id          # siempre presente
string session_id          # vacío si no hay conversación en curso
string utterance_id        # solo si llegó por voz

uint8 MODALITY_UNKNOWN=0
uint8 MODALITY_TEXT=1
uint8 MODALITY_VOICE=2
uint8 MODALITY_GESTURE=3
uint8 modality

string raw_text            # tal como llegó
string text                # normalizado
string language            # "es", "en"; vacío si se desconoce
float32 confidence         # 0.0 a 1.0; -1.0 si no aplica

uint8 IDENTITY_UNKNOWN=0
uint8 IDENTITY_CANDIDATE=1
uint8 IDENTITY_VERIFIED=2
uint8 identity_status
string person_id           # vacío si UNKNOWN
string track_id            # vacío si no hay seguimiento visual

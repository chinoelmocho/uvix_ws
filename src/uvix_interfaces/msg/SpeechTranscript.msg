# One recognized utterance. Empty text is valid only for non-success statuses.
uint8 RECOGNIZED=1
uint8 NO_SPEECH=2
uint8 UNAVAILABLE=3
uint8 ERROR=4
std_msgs/Header header
string utterance_id
string source_id
string text
string language
float32 confidence
uint8 status
bool audio_available

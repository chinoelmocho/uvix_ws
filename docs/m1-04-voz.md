# M1-04: contratos y proveedor sintético de voz

## Contratos ROS

- `uvix_interfaces/msg/SpeechTranscript`: una frase, identificada por `utterance_id`, con cabecera temporal, idioma, confianza, estado y declaración de disponibilidad de audio.
- `uvix_interfaces/action/Listen`: petición acotada por timeout y fin de frase; estados de feedback, resultados para frase, silencio, timeout, backend ausente y error. Cancelar la acción cancela la escucha en curso.
- `uvix_interfaces/action/Speak`: salida TTS cancelable, con progreso y declaración explícita cuando el backend no produjo audio.

La escucha y el habla usan un solo turno de audio: el coordinador no debe aceptar una segunda acción mientras la primera esté activa. `request_id` correlaciona una operación y `utterance_id` permite deduplicar una frase reconocida; consumidores descartan IDs ya procesados. El adaptador de micrófono debe declarar frecuencia de muestreo, canales, codificación, VAD y cómo detecta el fin de frase. Esos detalles quedan en parámetros/documentación del proveedor y no se inventa captura de audio en fixtures.

## Proveedor de prueba

El nodo de prueba `fake_voice_provider` expone `audio/listen` y `audio/speak`. `listen_scenario` acepta `recognized`, `silence`, `timeout`, `backend_unavailable` y `error`; ambas acciones aceptan cancelación y el nodo rechaza una segunda operación mientras la primera siga activa. Los resultados llevan IDs y `audio_available=false`; no afirman haber escuchado ni reproducido audio real. No se añade un motor ASR/TTS ni una dependencia de modelo.

## Hardware y adaptación

El objetivo `Listen` declara dispositivo/micrófono, frecuencia de muestreo, canales, codificación, duración de bloque, VAD, timeout total y silencio de cierre de frase. El adaptador debe validar valores admitidos por el dispositivo; una configuración no soportada produce error de backend, no una falsa transcripción. El transporte de ROS conserva el timestamp de recepción/captura y el ID de sesión de audio. El coordinador arbitra escucha y habla para mantener half-duplex.

Para arrancar el fixture: `ros2 launch uvix_audio fake_voice.launch.py listen_scenario:=recognized`. El fixture no requiere dispositivo de audio.

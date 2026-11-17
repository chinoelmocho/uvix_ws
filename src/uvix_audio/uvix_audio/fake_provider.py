"""Deterministic half-duplex voice fixtures for contract-level tests."""

from dataclasses import dataclass
from enum import Enum


class ListenResult(str, Enum):
    RECOGNIZED = 'recognized'
    SILENCE = 'silence'
    TIMEOUT = 'timeout'
    BACKEND_UNAVAILABLE = 'backend_unavailable'
    ERROR = 'error'


@dataclass(frozen=True)
class Transcript:
    utterance_id: str
    text: str
    language: str
    confidence: float
    status: ListenResult
    audio_available: bool = False


class FakeVoiceProvider:
    """Return queued outcomes; model the single active listen/speak turn."""

    def __init__(self, outcomes=None):
        self.outcomes = list(outcomes or ())
        self.active_operation = None
        self._seen_utterances = set()

    def _begin(self, operation):
        if self.active_operation is not None:
            raise RuntimeError('half-duplex operation already active')
        self.active_operation = operation

    def finish(self):
        self.active_operation = None

    def cancel(self):
        if self.active_operation is None:
            return False
        self.active_operation = None
        return True

    def begin_listening(self, request_id):
        self._begin(('listen', request_id))

    def begin_speaking(self, request_id):
        self._begin(('speak', request_id))

    def listen(self, request_id, language='es', timeout_s=8.0,
               phrase_end_silence_s=0.8):
        if timeout_s <= 0 or phrase_end_silence_s <= 0:
            raise ValueError('timeouts must be positive')
        self.begin_listening(request_id)
        result = self.outcomes.pop(0) if self.outcomes else (ListenResult.TIMEOUT, '')
        status, text = result
        transcript = None
        if status == ListenResult.RECOGNIZED:
            transcript = Transcript(f'{request_id}:utterance', text, language,
                                    1.0, status, audio_available=False)
        self.finish()
        return status, transcript

    def accept_once(self, transcript):
        if transcript is None or transcript.utterance_id in self._seen_utterances:
            return False
        self._seen_utterances.add(transcript.utterance_id)
        return True

    def speak(self, request_id, text, language='es'):
        if not text.strip():
            raise ValueError('text must not be empty')
        self.begin_speaking(request_id)
        self.finish()
        return {'completed': True, 'audio_available': False,
                'request_id': request_id, 'language': language}

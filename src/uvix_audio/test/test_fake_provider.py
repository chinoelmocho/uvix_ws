import unittest

from uvix_audio.fake_provider import FakeVoiceProvider, ListenResult


class FakeVoiceProviderTest(unittest.TestCase):
    def test_recognized_phrase_has_id_and_declares_no_audio(self):
        provider = FakeVoiceProvider([(ListenResult.RECOGNIZED, 'Buenos días')])
        status, transcript = provider.listen('req-1')
        self.assertEqual(status, ListenResult.RECOGNIZED)
        self.assertEqual(transcript.text, 'Buenos días')
        self.assertTrue(transcript.utterance_id)
        self.assertFalse(transcript.audio_available)

    def test_silence_timeout_unavailable_and_error(self):
        cases = [ListenResult.SILENCE, ListenResult.TIMEOUT,
                 ListenResult.BACKEND_UNAVAILABLE, ListenResult.ERROR]
        for case in cases:
            with self.subTest(case=case):
                status, transcript = FakeVoiceProvider([(case, '')]).listen('r')
                self.assertEqual(status, case)
                self.assertIsNone(transcript)

    def test_duplicate_utterance_is_accepted_once(self):
        provider = FakeVoiceProvider([(ListenResult.RECOGNIZED, 'Hola')])
        _status, transcript = provider.listen('req-2')
        self.assertTrue(provider.accept_once(transcript))
        self.assertFalse(provider.accept_once(transcript))

    def test_half_duplex_and_cancel(self):
        provider = FakeVoiceProvider()
        provider.begin_listening('r1')
        with self.assertRaises(RuntimeError):
            provider.speak('r2', 'Hola')
        self.assertTrue(provider.cancel())
        self.assertFalse(provider.cancel())
        self.assertFalse(provider.speak('r3', 'Hola')['audio_available'])


if __name__ == '__main__':
    unittest.main()

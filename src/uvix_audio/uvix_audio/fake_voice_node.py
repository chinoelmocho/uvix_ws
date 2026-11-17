"""ROS actions that simulate speech without accessing microphone or speakers."""

import threading
import time
import uuid

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from uvix_interfaces.action import Listen, Speak
from uvix_interfaces.msg import SpeechTranscript


class FakeVoiceNode(Node):
    def __init__(self):
        super().__init__('fake_voice_provider')
        self.declare_parameter('listen_scenario', 'recognized')
        self.declare_parameter('phrase_text', 'Buenos días, ¿cómo está?')
        self.declare_parameter('speak_duration_s', 1.0)
        self.listen_scenario = str(self.get_parameter('listen_scenario').value)
        self.phrase_text = str(self.get_parameter('phrase_text').value)
        self.speak_duration = float(self.get_parameter('speak_duration_s').value)
        if self.listen_scenario not in (
                'recognized', 'silence', 'timeout', 'backend_unavailable', 'error'):
            raise ValueError('listen_scenario is not a supported fixture')
        if self.speak_duration < 0.0:
            raise ValueError('speak_duration_s must be nonnegative')

        self._active_lock = threading.Lock()
        self._active_request = None
        self._callback_group = ReentrantCallbackGroup()
        self.listen_server = ActionServer(
            self, Listen, 'audio/listen', execute_callback=self._listen,
            goal_callback=self._goal, cancel_callback=self._cancel,
            callback_group=self._callback_group)
        self.speak_server = ActionServer(
            self, Speak, 'audio/speak', execute_callback=self._speak,
            goal_callback=self._goal, cancel_callback=self._cancel,
            callback_group=self._callback_group)
        self.get_logger().info(
            'Proveedor sintético listo; no captura micrófono ni reproduce audio')

    def _goal(self, request):
        if hasattr(request, 'timeout_sec'):
            if (request.timeout_sec <= 0.0 or
                    request.phrase_end_silence_sec <= 0.0 or
                    request.sample_rate_hz == 0 or request.channels == 0 or
                    request.frame_duration_ms == 0 or not request.encoding):
                return GoalResponse.REJECT
        elif not request.text.strip():
            return GoalResponse.REJECT
        with self._active_lock:
            if self._active_request is not None:
                return GoalResponse.REJECT
            self._active_request = request
            return GoalResponse.ACCEPT

    @staticmethod
    def _cancel(_goal_handle):
        return CancelResponse.ACCEPT

    def _release(self):
        with self._active_lock:
            self._active_request = None

    def _wait(self, goal_handle, duration_s, feedback=None):
        end_time = time.monotonic() + max(0.0, duration_s)
        while time.monotonic() < end_time:
            if goal_handle.is_cancel_requested:
                return False
            if feedback is not None:
                feedback()
            time.sleep(min(0.05, max(0.0, end_time - time.monotonic())))
        return not goal_handle.is_cancel_requested

    def _listen(self, goal_handle):
        result = Listen.Result()
        request = goal_handle.request
        scenario = self.listen_scenario
        try:
            if scenario == 'backend_unavailable':
                result.result_code = Listen.Result.RESULT_BACKEND_UNAVAILABLE
                result.detail = 'Fixture: backend de reconocimiento no disponible'
                goal_handle.succeed()
                return result
            if scenario == 'error':
                result.result_code = Listen.Result.RESULT_ERROR
                result.detail = 'Fixture: error de reconocimiento'
                goal_handle.succeed()
                return result

            if scenario == 'timeout':
                wait_s = request.timeout_sec
            elif scenario == 'silence':
                wait_s = request.phrase_end_silence_sec
            else:
                wait_s = min(0.25, request.timeout_sec)

            if not self._wait(goal_handle, wait_s):
                result.result_code = Listen.Result.RESULT_CANCELED
                result.detail = 'Escucha cancelada'
                goal_handle.canceled()
                return result
            if scenario == 'timeout':
                result.result_code = Listen.Result.RESULT_TIMEOUT
                result.detail = 'Fixture: timeout sin frase'
                goal_handle.succeed()
                return result
            if scenario == 'silence':
                result.result_code = Listen.Result.RESULT_SILENCE
                result.detail = 'Fixture: no se detectó voz'
                goal_handle.succeed()
                return result

            transcript = SpeechTranscript()
            transcript.header.stamp = self.get_clock().now().to_msg()
            transcript.utterance_id = str(uuid.uuid4())
            transcript.source_id = 'synthetic_fake'
            transcript.text = self.phrase_text
            transcript.language = request.language or 'es'
            transcript.confidence = 1.0
            transcript.status = SpeechTranscript.RECOGNIZED
            transcript.audio_available = False
            result.result_code = Listen.Result.RESULT_RECOGNIZED
            result.transcript = transcript
            result.detail = 'Fixture sintético; no se capturó audio'
            goal_handle.succeed()
            return result
        finally:
            self._release()

    def _speak(self, goal_handle):
        result = Speak.Result()
        started = time.monotonic()

        def publish_feedback():
            feedback = Speak.Feedback()
            feedback.progress = min(
                1.0, (time.monotonic() - started) / max(self.speak_duration, 0.001))
            goal_handle.publish_feedback(feedback)

        try:
            if not self._wait(goal_handle, self.speak_duration, publish_feedback):
                result.result_code = Speak.Result.RESULT_CANCELED
                result.detail = 'Habla cancelada'
                result.audio_available = False
                goal_handle.canceled()
                return result
            result.result_code = Speak.Result.RESULT_COMPLETED
            result.detail = 'Fixture completado; no se reprodujo audio'
            result.audio_available = False
            goal_handle.succeed()
            return result
        finally:
            self._release()


def main(args=None):
    rclpy.init(args=args)
    node = FakeVoiceNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        executor.shutdown()
        executor.remove_node(node)
        node.destroy_node()
        rclpy.shutdown()

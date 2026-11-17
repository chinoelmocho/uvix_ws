"""Explicitly synthetic visual observations used to validate M1-03 contracts."""

import uuid

from geometry_msgs.msg import Point
from builtin_interfaces.msg import Duration
from std_msgs.msg import Header
from uvix_interfaces.msg import (
    BodyKeypoint,
    BodyPose,
    BodyPoseArray,
    FaceMatch,
    FaceMatchArray,
    GestureEvent,
    ImageBox,
    PeopleObservations,
    PersonObservation,
)


SCENARIOS = ('known', 'unknown', 'partial_pose', 'gesture', 'low_quality', 'empty')


def _person(track_id, confidence=0.97):
    person = PersonObservation()
    person.track_id = track_id
    person.bounding_box = ImageBox(
        center_x_px=320.0, center_y_px=240.0, width_px=100.0, height_px=200.0)
    person.detection_confidence = confidence
    person.has_position_3d = False
    person.position_m = Point()
    person.position_confidence = 0.0
    return person


def _pose(track_id, partial=False):
    pose = BodyPose()
    pose.track_id = track_id
    pose.coordinate_space = BodyPose.COORDINATES_PIXELS_2D
    pose.quality = 0.72 if partial else 0.96
    pose.keypoints = [
        BodyKeypoint(name='nose', x=320.0, y=120.0, z=0.0,
                     visibility=0.93, present=True),
        BodyKeypoint(name='left_ankle', x=0.0, y=0.0, z=0.0,
                     visibility=0.0, present=False if partial else True),
    ]
    return pose


def build_fixture(scenario, stamp, tracker_session_id='fixture-session'):
    """Return person, pose, face and gesture messages for one test case."""
    if scenario not in SCENARIOS:
        raise ValueError(f'Unknown scenario: {scenario}')
    header = Header(stamp=stamp, frame_id='camera_color_optical_frame')
    people = PeopleObservations(
        header=header, camera_id='camera_color', source_id='synthetic_fixture',
        tracker_session_id=tracker_session_id, valid_for=Duration(sec=1))
    poses = BodyPoseArray(
        header=header, camera_id='camera_color', source_id='synthetic_fixture',
        tracker_session_id=tracker_session_id, valid_for=Duration(sec=1))
    faces = FaceMatchArray(
        header=header, camera_id='camera_color', source_id='synthetic_fixture',
        tracker_session_id=tracker_session_id, valid_for=Duration(sec=1))
    gesture = None

    if scenario == 'known':
        people.people = [_person('track-01')]
        poses.poses = [_pose('track-01')]
        match = FaceMatch(track_id='track-01', face_observation_id='face-01',
                          person_id='resident-01', status=FaceMatch.KNOWN,
                          match_confidence=0.93, face_quality=0.91)
        faces.matches = [match]
    elif scenario == 'unknown':
        people.people = [_person('track-02')]
        faces.matches = [FaceMatch(
            track_id='track-02', face_observation_id='face-02', person_id='',
            status=FaceMatch.UNKNOWN, match_confidence=0.0, face_quality=0.86)]
    elif scenario == 'partial_pose':
        people.people = [_person('track-03')]
        poses.poses = [_pose('track-03', partial=True)]
    elif scenario == 'gesture':
        people.people = [_person('track-04')]
        gesture = GestureEvent(
            header=header, event_id=str(uuid.uuid4()), source_id='synthetic_fixture',
            tracker_session_id=tracker_session_id, track_id='track-04',
            gesture=GestureEvent.HAND_RAISED, quality=0.9,
            deduplication_key=f'{tracker_session_id}:track-04:HAND_RAISED')
        gesture.persistence.sec = 0
        gesture.persistence.nanosec = 500_000_000
        gesture.valid_for.sec = 1
    elif scenario == 'low_quality':
        people.people = [_person('track-05', confidence=0.31)]
        faces.matches = [FaceMatch(
            track_id='track-05', face_observation_id='face-05', person_id='',
            status=FaceMatch.INSUFFICIENT_QUALITY, match_confidence=0.0,
            face_quality=0.18)]

    return people, poses, faces, gesture


class GestureEventGate:
    """Require sustained detection and emit once until the gesture is released."""

    def __init__(self, minimum_persistence_s=0.5):
        if minimum_persistence_s < 0.0:
            raise ValueError('minimum_persistence_s must be nonnegative')
        self.minimum_persistence_s = float(minimum_persistence_s)
        self._since = {}
        self._emitted = set()

    def observe(self, tracker_session_id, track_id, gesture, detected, now_s):
        key = (tracker_session_id, track_id, int(gesture))
        if not detected:
            self._since.pop(key, None)
            self._emitted.discard(key)
            return False
        self._since.setdefault(key, float(now_s))
        if float(now_s) - self._since[key] < self.minimum_persistence_s:
            return False
        if key in self._emitted:
            return False
        self._emitted.add(key)
        return True

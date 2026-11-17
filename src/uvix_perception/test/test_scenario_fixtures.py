from builtin_interfaces.msg import Time
from uvix_interfaces.msg import BodyPose, FaceMatch, GestureEvent

from uvix_perception.scenario_fixtures import SCENARIOS, GestureEventGate, build_fixture


def _fixture(name):
    return build_fixture(name, Time(sec=10, nanosec=250_000_000), 'session-test')


def test_known_person_is_linked_by_track_without_granting_permissions():
    people, poses, faces, gesture = _fixture('known')
    assert len(people.people) == 1
    assert people.people[0].track_id == faces.matches[0].track_id == 'track-01'
    assert faces.matches[0].status == FaceMatch.KNOWN
    assert faces.matches[0].person_id == 'resident-01'
    assert people.people[0].has_position_3d is False
    assert gesture is None


def test_unknown_identity_remains_unassociated():
    people, _poses, faces, _gesture = _fixture('unknown')
    assert people.people[0].track_id == 'track-02'
    assert faces.matches[0].status == FaceMatch.UNKNOWN
    assert faces.matches[0].person_id == ''


def test_partial_pose_declares_pixel_coordinates_and_missing_joint():
    _people, poses, _faces, _gesture = _fixture('partial_pose')
    pose = poses.poses[0]
    assert pose.coordinate_space == BodyPose.COORDINATES_PIXELS_2D
    assert pose.keypoints[0].present is True
    assert pose.keypoints[1].present is False


def test_gesture_is_an_event_with_session_track_and_persistence():
    _people, _poses, _faces, gesture = _fixture('gesture')
    assert gesture.event_id
    assert gesture.tracker_session_id == 'session-test'
    assert gesture.track_id == 'track-04'
    assert gesture.gesture == GestureEvent.HAND_RAISED
    assert gesture.persistence.sec == 0
    assert gesture.persistence.nanosec == 500_000_000
    assert gesture.valid_for.sec == 1


def test_low_quality_does_not_claim_a_match_and_empty_case_is_explicit():
    people, _poses, faces, _gesture = _fixture('low_quality')
    assert people.people[0].detection_confidence < 0.5
    assert faces.matches[0].status == FaceMatch.INSUFFICIENT_QUALITY
    assert faces.matches[0].person_id == ''
    empty_people, empty_poses, empty_faces, empty_gesture = _fixture('empty')
    assert not empty_people.people and not empty_poses.poses and not empty_faces.matches
    assert empty_gesture is None
    assert len(SCENARIOS) == 6


def test_gesture_gate_waits_then_deduplicates_until_release():
    gate = GestureEventGate(minimum_persistence_s=0.5)
    assert not gate.observe('session-1', 'track-1', GestureEvent.HAND_RAISED, True, 1.0)
    assert not gate.observe('session-1', 'track-1', GestureEvent.HAND_RAISED, True, 1.4)
    assert gate.observe('session-1', 'track-1', GestureEvent.HAND_RAISED, True, 1.5)
    assert not gate.observe('session-1', 'track-1', GestureEvent.HAND_RAISED, True, 2.0)
    assert not gate.observe('session-1', 'track-1', GestureEvent.HAND_RAISED, False, 2.1)
    assert not gate.observe('session-1', 'track-1', GestureEvent.HAND_RAISED, True, 2.2)
    assert gate.observe('session-1', 'track-1', GestureEvent.HAND_RAISED, True, 2.7)
    # Reused tracker IDs in a new session do not inherit prior deduplication.
    assert not gate.observe('session-2', 'track-1', GestureEvent.HAND_RAISED, True, 3.0)
    assert gate.observe('session-2', 'track-1', GestureEvent.HAND_RAISED, True, 3.5)

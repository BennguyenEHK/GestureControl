from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import cv2
import mediapipe as mp

@dataclass
class HandData:
    landmarks: List[Tuple[float, float, float]]
    handedness: str
    fingertip_positions: Dict[int, Tuple[float, float, float]]
    gesture_type: str
    tapped_finger: Optional[int]
    is_thumb_index_pinched: bool = False

class TapDetector:

    PINCH_THRESHOLD = 0.055

    def __init__(self, cooldown_frames=5):
        self.cooldown_frames = cooldown_frames
        self.cooldown_remaining = 0

    def update_cooldowns(self):
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1

    def detect(self, index_pos, middle_pos):
        if self.cooldown_remaining > 0:
            return False
        index_x, index_y, index_z = index_pos
        middle_x, middle_y, middle_z = middle_pos
        distance = ((index_x - middle_x) ** 2 + (index_y - middle_y) ** 2) ** 0.5
        avg_z = (index_z + middle_z) / 2
        depth_scale = 1.0 - (avg_z * 1.5)
        adjusted_threshold = self.PINCH_THRESHOLD * depth_scale
        if distance < adjusted_threshold:
            print(f"TAP DETECTED! (distance: {distance:.3f}, threshold: {adjusted_threshold:.3f}, depth: {avg_z:.3f})")
            self.cooldown_remaining = self.cooldown_frames
            return True
        return False

class GestureTracker:

    FINGERTIP_INDICES = [4, 8, 12]

    def __init__(self, max_num_hands=2):
        self.max_num_hands = max_num_hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        self.tap_detectors = [TapDetector() for _ in range(max_num_hands)]

    def process(self, frame) -> Tuple[List[HandData], int]:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        for detector in self.tap_detectors:
            detector.update_cooldowns()
        hand_data_list = []
        hand_count = 0
        if results.multi_hand_landmarks:
            hand_count = len(results.multi_hand_landmarks)
            for hand_idx, (hand_landmarks, handedness) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness)
            ):
                landmarks = []
                for landmark in hand_landmarks.landmark:
                    landmarks.append((landmark.x, landmark.y, landmark.z))
                fingertip_positions = {}
                for idx in self.FINGERTIP_INDICES:
                    landmark = hand_landmarks.landmark[idx]
                    fingertip_positions[idx] = (landmark.x, landmark.y, landmark.z)
                tapped_finger = None
                index_pos = fingertip_positions[8]
                middle_pos = fingertip_positions[12]
                if self.tap_detectors[hand_idx].detect(index_pos, middle_pos):
                    tapped_finger = 8
                is_thumb_index_pinched = False
                if 4 in fingertip_positions and 8 in fingertip_positions:
                    thumb_pos = fingertip_positions[4]
                    index_pos = fingertip_positions[8]
                    thumb_x, thumb_y, thumb_z = thumb_pos
                    index_x, index_y, index_z = index_pos
                    distance = ((thumb_x - index_x) ** 2 + (thumb_y - index_y) ** 2) ** 0.5
                    avg_z = (thumb_z + index_z) / 2
                    depth_scale = 1.0 - (avg_z * 1.5)
                    adjusted_threshold = 0.3 * depth_scale
                    print(f"distance between thumb and index: {distance:.2f} and threshold: {adjusted_threshold:.2f}")
                    is_thumb_index_pinched = distance < adjusted_threshold
                is_c_sign = self._detect_C_sign(landmarks)
                if is_c_sign:
                    gesture_type = "c_sign"
                elif tapped_finger is not None:
                    gesture_type = "tap"
                else:
                    gesture_type = "none"
                hand_label = handedness.classification[0].label
                hand_data = HandData(
                    landmarks=landmarks,
                    handedness=hand_label,
                    fingertip_positions=fingertip_positions,
                    gesture_type=gesture_type,
                    tapped_finger=tapped_finger,
                    is_thumb_index_pinched=is_thumb_index_pinched
                )
                hand_data_list.append(hand_data)
        return hand_data_list, hand_count

    def _detect_C_sign(self, landmarks: List[Tuple[float, float, float]]) -> bool:
        thumb_tip_x = landmarks[4][0]
        wrist_x = landmarks[0][0]
        thumb_distance = abs(thumb_tip_x - wrist_x)
        if thumb_distance < 0.15:
            return False
        finger_checks = [
            (8, 5, 6),
            (12, 9, 10),
            (16, 13, 14),
            (20, 17, 18)
        ]
        for tip_idx, mcp_idx, pip_idx in finger_checks:
            tip_y = landmarks[tip_idx][1]
            mcp_y = landmarks[mcp_idx][1]
            pip_y = landmarks[pip_idx][1]
            if tip_y >= mcp_y:
                return False
            if tip_y < pip_y - 0.05:
                return False
        return True

    def cleanup(self):
        if self.hands:
            self.hands.close()

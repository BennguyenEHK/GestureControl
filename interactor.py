from dataclasses import dataclass
from typing import Set, List, Optional
import time
import pyautogui
from gesture_tracker import HandData

@dataclass
class KeyboardOverlayInfo:
    x_offset: int
    y_offset: int
    scale: float
    width: int
    height: int

class MouseSmoother:

    def __init__(self, smoothing_factor=0.3, deadzone=0.01):
        self.smoothing_factor = smoothing_factor
        self.deadzone = deadzone
        self.smoothed_x = None
        self.smoothed_y = None

    def smooth(self, raw_x, raw_y):
        if self.smoothed_x is None:
            self.smoothed_x = raw_x
            self.smoothed_y = raw_y
            return raw_x, raw_y
        delta_x = raw_x - self.smoothed_x
        delta_y = raw_y - self.smoothed_y
        if abs(delta_x) < self.deadzone:
            delta_x = 0
        if abs(delta_y) < self.deadzone:
            delta_y = 0
        self.smoothed_x += self.smoothing_factor * delta_x
        self.smoothed_y += self.smoothing_factor * delta_y
        return self.smoothed_x, self.smoothed_y

class Interactor:

    MODE_KEYBOARD = "keyboard"
    MODE_MOUSE = "mouse"
    MODE_NONE = "none"
    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720
    KEY_PRESS_COOLDOWN_MS = 200

    def __init__(self, keyboard, mouse_smoothing=0.6, mouse_deadzone=0.015,
                 mouse_input_min=0.15, mouse_input_max=0.85, mouse_debug_coords=False):
        self.keyboard = keyboard
        self.mode = self.MODE_NONE
        self.previous_mode = self.MODE_NONE
        self.last_key_press_time = {}
        self.mouse_smoother = MouseSmoother(
            smoothing_factor=mouse_smoothing,
            deadzone=mouse_deadzone
        )
        self.mouse_input_min = mouse_input_min
        self.mouse_input_max = mouse_input_max
        self.mouse_debug_coords = mouse_debug_coords

    def update(
        self,
        hand_data_list: List[HandData],
        overlay_info: KeyboardOverlayInfo,
        current_time_ms: float
    ) -> tuple:
        hand_count = len(hand_data_list)
        self.previous_mode = self.mode
        self.mode = self._detect_mode(hand_count)
        if self.mode == self.MODE_MOUSE and self.previous_mode != self.MODE_MOUSE:
            self._recenter_mouse()
        highlighted_keys = set()
        tapped_keys = set()
        if self.mode == self.MODE_KEYBOARD:
            highlighted_keys, tapped_keys = self._handle_keyboard_mode(
                hand_data_list, overlay_info, current_time_ms
            )
        elif self.mode == self.MODE_MOUSE:
            self._handle_mouse_mode(hand_data_list)
        return highlighted_keys, tapped_keys

    def _detect_mode(self, hand_count: int) -> str:
        if hand_count == 0:
            return self.MODE_NONE
        elif hand_count == 1:
            return self.MODE_MOUSE
        else:
            return self.MODE_KEYBOARD

    def _handle_keyboard_mode(
        self,
        hand_data_list: List[HandData],
        overlay_info: KeyboardOverlayInfo,
        current_time_ms: float
    ) -> tuple:
        highlighted_keys = set()
        tapped_keys = set()
        for hand_data in hand_data_list:
            if 8 in hand_data.fingertip_positions:
                norm_x, norm_y = hand_data.fingertip_positions[8][:2]
                kb_x, kb_y = self._transform_coordinates(
                    norm_x, norm_y, overlay_info
                )
                if kb_x is None or kb_y is None:
                    continue
                key = self.keyboard.get_key_at_position(kb_x, kb_y)
                if key:
                    highlighted_keys.add(key)
                    if hand_data.tapped_finger == 8:
                        tapped_keys.add(key)
                        self._type_key(key, current_time_ms)
        return highlighted_keys, tapped_keys

    def _handle_mouse_mode(self, hand_data_list: List[HandData]):
        if not hand_data_list:
            return
        hand_data = hand_data_list[0]
        if hand_data.tapped_finger == 8:
            pyautogui.leftClick()
            print("Left-click detected (index finger tap)")
        if not hand_data.is_thumb_index_pinched:
            return
        if 8 in hand_data.fingertip_positions:
            index_x, index_y, index_z = hand_data.fingertip_positions[8]
            norm_x, norm_y = index_x, index_y

            expanded_x = (norm_x - self.mouse_input_min) / (self.mouse_input_max - self.mouse_input_min)
            expanded_y = (norm_y - self.mouse_input_min) / (self.mouse_input_max - self.mouse_input_min)

            expanded_x = max(0.0, min(1.0, expanded_x))
            expanded_y = max(0.0, min(1.0, expanded_y))

            smooth_x, smooth_y = self.mouse_smoother.smooth(expanded_x, expanded_y)

            screen_w, screen_h = pyautogui.size()
            screen_x = smooth_x * screen_w
            screen_y = smooth_y * screen_h

            if self.mouse_debug_coords:
                print(f"[MOUSE DEBUG] PINCHED | Raw: ({norm_x:.3f}, {norm_y:.3f}, z={index_z:.3f}) | "
                      f"Expanded: ({expanded_x:.3f}, {expanded_y:.3f}) | "
                      f"Smoothed: ({smooth_x:.3f}, {smooth_y:.3f}) | "
                      f"Screen: ({screen_x:.0f}, {screen_y:.0f})")

            pyautogui.moveTo(screen_x, screen_y)

    def _recenter_mouse(self):
        screen_w, screen_h = pyautogui.size()
        pyautogui.moveTo(screen_w // 2, screen_h // 2, duration=0)

    def _transform_coordinates(
        self,
        normalized_x: float,
        normalized_y: float,
        overlay_info: KeyboardOverlayInfo
    ) -> tuple:
        pixel_x = int(normalized_x * self.CAMERA_WIDTH)
        pixel_y = int(normalized_y * self.CAMERA_HEIGHT)
        if not (overlay_info.x_offset <= pixel_x <= overlay_info.x_offset + overlay_info.width):
            return None, None
        if not (overlay_info.y_offset <= pixel_y <= overlay_info.y_offset + overlay_info.height):
            return None, None
        kb_x = int((pixel_x - overlay_info.x_offset) / overlay_info.scale)
        kb_y = int((pixel_y - overlay_info.y_offset) / overlay_info.scale)
        return kb_x, kb_y

    def _type_key(self, key: str, current_time_ms: float):
        if key in self.last_key_press_time:
            time_since_last_press = current_time_ms - self.last_key_press_time[key]
            if time_since_last_press < self.KEY_PRESS_COOLDOWN_MS:
                return
        key_mapping = {
            'SPACE': 'space',
            'BACKSPACE': 'backspace',
            'ENTER': 'enter',
            ';': 'semicolon',
            ',': 'comma',
            '.': 'period',
            '/': 'slash'
        }
        pyautogui_key = key_mapping.get(key, key.lower())
        try:
            pyautogui.press(pyautogui_key)
            self.last_key_press_time[key] = current_time_ms
            print(f"Typed: {key}")
        except Exception as e:
            print(f"Error typing key '{key}': {e}")

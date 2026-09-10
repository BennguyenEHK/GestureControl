import cv2
import numpy as np

class Keyboard:

    LAYOUT = [
        ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
        ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
        ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';'],
        ['Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/'],
        ['SPACE', 'BACKSPACE', 'ENTER']
    ]
    KEY_WIDTH = 80
    KEY_HEIGHT = 80
    KEY_MARGIN = 8
    KEY_PADDING = 10
    SPECIAL_KEYS = ['SPACE', 'BACKSPACE', 'ENTER']
    CAMERA_INDEX = 0
    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720
    WINDOW_NAME = "Virtual Keyboard on Camera"
    BACKGROUND_COLOR = (30, 30, 30)
    KEYBOARD_SCALE = 0.95
    KEYBOARD_ALPHA = 0.85
    KEY_COLOR = (80, 80, 80)
    KEY_BORDER_COLOR = (180, 180, 180)
    KEY_TEXT_COLOR = (255, 255, 255)
    HIGHLIGHT_COLOR = (100, 200, 255)
    TAP_COLOR = (0, 255, 0)
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 0.8
    FONT_THICKNESS = 2
    BORDER_THICKNESS = 2

    def __init__(self):
        self.key_positions = {}
        self._calculate_key_positions()
        self._create_canvas()

    def _calculate_key_positions(self):
        y_pos = self.KEY_MARGIN
        max_width = 0
        for row_idx, row in enumerate(self.LAYOUT):
            x_pos = self.KEY_MARGIN
            for key in row:
                if key in self.SPECIAL_KEYS:
                    key_width = (self.KEY_WIDTH * 2) + self.KEY_MARGIN
                else:
                    key_width = self.KEY_WIDTH
                self.key_positions[key] = (x_pos, y_pos, key_width, self.KEY_HEIGHT)
                x_pos += key_width + self.KEY_MARGIN
            max_width = max(max_width, x_pos)
            y_pos += self.KEY_HEIGHT + self.KEY_MARGIN
        self.keyboard_width = max_width
        self.keyboard_height = y_pos

    def _create_canvas(self):
        self.canvas = np.zeros(
            (self.keyboard_height + self.KEY_MARGIN,
             self.keyboard_width + self.KEY_MARGIN,
             3),
            dtype=np.uint8
        )
        self.canvas[:] = self.BACKGROUND_COLOR

    def draw_keyboard(self, highlighted_keys=None, tapped_keys=None):
        if isinstance(highlighted_keys, str):
            highlighted_keys = {highlighted_keys}
        elif highlighted_keys is None:
            highlighted_keys = set()
        if isinstance(tapped_keys, str):
            tapped_keys = {tapped_keys}
        elif tapped_keys is None:
            tapped_keys = set()
        img = self.canvas.copy()
        for key, (x, y, w, h) in self.key_positions.items():
            if key in tapped_keys:
                color = self.TAP_COLOR
            elif key in highlighted_keys:
                color = self.HIGHLIGHT_COLOR
            else:
                color = self.KEY_COLOR
            cv2.rectangle(img, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(img, (x, y), (x + w, y + h), self.KEY_BORDER_COLOR, self.BORDER_THICKNESS)
            text = key
            (text_width, text_height), baseline = cv2.getTextSize(
                text, self.FONT, self.FONT_SCALE, self.FONT_THICKNESS
            )
            text_x = x + (w - text_width) // 2
            text_y = y + (h + text_height) // 2
            cv2.putText(
                img, text, (text_x, text_y),
                self.FONT, self.FONT_SCALE,
                self.KEY_TEXT_COLOR, self.FONT_THICKNESS
            )
        return img

    def overlay_on_frame(self, frame, highlighted_keys=None, tapped_keys=None):
        frame_h, frame_w = frame.shape[:2]
        keyboard_img = self.draw_keyboard(highlighted_keys, tapped_keys)
        kb_h, kb_w = keyboard_img.shape[:2]
        max_kb_width = int(frame_w * self.KEYBOARD_SCALE)
        scale = max_kb_width / kb_w
        new_kb_w = int(kb_w * scale)
        new_kb_h = int(kb_h * scale)
        if new_kb_h > frame_h - 20:
            scale = (frame_h - 20) / kb_h
            new_kb_w = int(kb_w * scale)
            new_kb_h = int(kb_h * scale)
        keyboard_img = cv2.resize(keyboard_img, (new_kb_w, new_kb_h))
        x_offset = (frame_w - new_kb_w) // 2
        y_offset = frame_h - new_kb_h - 10
        x_offset = max(0, min(x_offset, frame_w - new_kb_w))
        y_offset = max(0, min(y_offset, frame_h - new_kb_h))
        overlay = frame.copy()
        overlay[y_offset:y_offset + new_kb_h, x_offset:x_offset + new_kb_w] = keyboard_img
        cv2.addWeighted(overlay, self.KEYBOARD_ALPHA, frame, 1 - self.KEYBOARD_ALPHA, 0, frame)
        return frame

    def get_dimensions(self):
        return (self.keyboard_width, self.keyboard_height)

    def get_key_at_position(self, x, y):
        for key, (kx, ky, kw, kh) in self.key_positions.items():
            if kx <= x <= kx + kw and ky <= y <= ky + kh:
                return key
        return None

    def get_overlay_info(self, frame_width, frame_height):
        from interactor import KeyboardOverlayInfo
        kb_h, kb_w = self.keyboard_height, self.keyboard_width
        max_kb_width = int(frame_width * self.KEYBOARD_SCALE)
        scale = max_kb_width / kb_w
        new_kb_w = int(kb_w * scale)
        new_kb_h = int(kb_h * scale)
        if new_kb_h > frame_height - 20:
            scale = (frame_height - 20) / kb_h
            new_kb_w = int(kb_w * scale)
            new_kb_h = int(kb_h * scale)
        x_offset = (frame_width - new_kb_w) // 2
        y_offset = frame_height - new_kb_h - 10
        x_offset = max(0, min(x_offset, frame_width - new_kb_w))
        y_offset = max(0, min(y_offset, frame_height - new_kb_h))
        return KeyboardOverlayInfo(
            x_offset=x_offset,
            y_offset=y_offset,
            scale=scale,
            width=new_kb_w,
            height=new_kb_h
        )

    def show_keyboard_window(self, window_name, highlighted_keys=None, tapped_keys=None, screen_w=1920, screen_h=1080):
        keyboard_img = self.draw_keyboard(highlighted_keys, tapped_keys)
        mini_scale = 0.6
        kb_h, kb_w = keyboard_img.shape[:2]
        mini_w = int(kb_w * mini_scale)
        mini_h = int(kb_h * mini_scale)
        mini_keyboard = cv2.resize(keyboard_img, (mini_w, mini_h))
        cv2.imshow(window_name, mini_keyboard)
        return mini_w, mini_h

    def cleanup(self):
        pass

def main():
    print("=" * 60)
    print("DEPRECATED: Standalone keyboard demo")
    print("=" * 60)
    print("\nThis standalone demo is no longer available.")
    print("The Keyboard class is now a component in the gesture control system.")
    print("\nTo run the gesture-controlled virtual keyboard:")
    print("  python main.py")
    print("\nFeatures:")
    print("  - Hand tracking with MediaPipe")
    print("  - Tap gesture detection")
    print("  - 2 hands: Keyboard mode (tap on keys to type)")
    print("  - 1 hand: Mouse mode (thumb controls mouse)")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user (Ctrl+C)")
        print("Cleaning up...")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()

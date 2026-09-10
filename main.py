import cv2
import time
import ctypes
from keyboard import Keyboard
from gesture_tracker import GestureTracker
from interactor import Interactor
from settings import Settings

class FPSCalculator:

    def __init__(self, window_size=30):
        self.window_size = window_size
        self.frame_times = []
        self.last_time = time.time()

    def update(self) -> float:
        current_time = time.time()
        delta_time = current_time - self.last_time
        self.last_time = current_time
        self.frame_times.append(delta_time)
        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)
        if len(self.frame_times) > 0:
            avg_time = sum(self.frame_times) / len(self.frame_times)
            if avg_time > 0:
                return 1.0 / avg_time
        return 0.0

class GestureControlApp:

    CAMERA_INDEX = 0
    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720
    WINDOW_NAME = "Gesture-Controlled Virtual Keyboard"
    KEYBOARD_WINDOW_NAME = "Virtual Keyboard (Mouse Mode)"
    HUD_FONT = cv2.FONT_HERSHEY_SIMPLEX
    HUD_FONT_SCALE = 0.7
    HUD_FONT_THICKNESS = 2
    HUD_COLOR = (0, 255, 0)
    HUD_BG_COLOR = (0, 0, 0)

    def __init__(self, settings=None):
        print("=" * 60)
        print("Gesture-Controlled Virtual Keyboard")
        print("=" * 60)
        print("\nInitializing components...")
        self.settings = settings if settings else Settings()
        camera_index = self.settings.get('camera_index', self.CAMERA_INDEX)
        camera_width = self.settings.get('camera_width', self.CAMERA_WIDTH)
        camera_height = self.settings.get('camera_height', self.CAMERA_HEIGHT)
        self.camera = cv2.VideoCapture(camera_index)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
        if not self.camera.isOpened():
            raise RuntimeError(
                f"Failed to open camera {self.CAMERA_INDEX}. "
                "Check camera connection and permissions."
            )
        print(f"  Camera initialized: {self.CAMERA_WIDTH}x{self.CAMERA_HEIGHT}")
        self.keyboard = Keyboard()
        print(f"  Keyboard initialized: {len(self.keyboard.key_positions)} keys")
        max_hands = self.settings.get('max_hands', 2)
        self.gesture_tracker = GestureTracker(max_num_hands=max_hands)
        print(f"  GestureTracker initialized with MediaPipe (max hands: {max_hands})")
        mouse_smoothing = self.settings.get('mouse_smoothing', 0.45)
        mouse_deadzone = self.settings.get('mouse_deadzone', 0.015)
        mouse_input_min = self.settings.get('mouse_input_min', 0.15)
        mouse_input_max = self.settings.get('mouse_input_max', 0.85)
        mouse_debug_coords = self.settings.get('mouse_debug_coords', False)
        self.interactor = Interactor(
            self.keyboard,
            mouse_smoothing=mouse_smoothing,
            mouse_deadzone=mouse_deadzone,
            mouse_input_min=mouse_input_min,
            mouse_input_max=mouse_input_max,
            mouse_debug_coords=mouse_debug_coords
        )
        print(f"  Interactor initialized with PyAutoGUI")
        print(f"    Mouse smoothing: {mouse_smoothing}, deadzone: {mouse_deadzone}")
        print(f"    Input range: [{mouse_input_min}, {mouse_input_max}], debug: {mouse_debug_coords}")
        self.fps_calculator = FPSCalculator()
        self.running = False
        self.keyboard_window_active = False
        print("\nInitialization complete!")
        print("\nControls:")
        print("  - 2 hands detected: Keyboard mode (tap on keys with index finger)")
        print("  - 1 hand detected: Mouse mode (index finger controls mouse)")
        print("    -> Keyboard window appears at bottom-right corner")
        print("  - C hand sign (1 hand only): Exit program")
        print("=" * 60)

    def setup_window(self):
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        try:
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            x = (screen_w - self.CAMERA_WIDTH) // 2
            y = (screen_h - self.CAMERA_HEIGHT) // 2
            time.sleep(0.1)
            hwnd = user32.FindWindowW(None, self.WINDOW_NAME)
            if hwnd:
                user32.MoveWindow(hwnd, x, y, self.CAMERA_WIDTH, self.CAMERA_HEIGHT, True)
                print(f"\nWindow centered at ({x}, {y})")
            else:
                print("\nWarning: Could not center window (handle not found)")
        except Exception as e:
            print(f"\nWarning: Could not center window: {e}")
            print("Window will appear at default position")

    def run(self):
        self.running = True
        self.setup_window()
        print("\nStarting main loop...")
        print("Keyboard ready for gesture control!\n")
        while self.running:
            success, frame = self.camera.read()
            if not success:
                print("Error: Failed to capture camera frame")
                break
            frame = cv2.flip(frame, 1)
            frame = self._process_frame(frame)
            cv2.imshow(self.WINDOW_NAME, frame)
            cv2.waitKey(1)
        self.cleanup()

    def _process_frame(self, frame):
        hand_data_list, hand_count = self.gesture_tracker.process(frame)
        if hand_count == 1:
            for hand_data in hand_data_list:
                if hand_data.gesture_type == "c_sign":
                    print("\nC sign detected! Exiting...")
                    self.running = False
                    break
        overlay_info = self.keyboard.get_overlay_info(
            self.CAMERA_WIDTH, self.CAMERA_HEIGHT
        )
        current_time_ms = time.time() * 1000
        highlighted_keys, tapped_keys = self.interactor.update(
            hand_data_list, overlay_info, current_time_ms
        )
        if self.interactor.mode == self.interactor.MODE_KEYBOARD:
            frame = self.keyboard.overlay_on_frame(frame, highlighted_keys, tapped_keys)
            kb_w, kb_h = self.keyboard.show_keyboard_window(
                self.KEYBOARD_WINDOW_NAME,
                highlighted_keys,
                tapped_keys
            )
            if not self.keyboard_window_active:
                self._position_keyboard_window(kb_w, kb_h)
                self.keyboard_window_active = True
        else:
            if self.keyboard_window_active:
                cv2.destroyWindow(self.KEYBOARD_WINDOW_NAME)
                self.keyboard_window_active = False
        fps = self.fps_calculator.update()
        frame = self._draw_hud(frame, hand_count, self.interactor.mode, fps)
        return frame

    def _draw_hud(self, frame, hand_count, mode, fps):
        lines = [
            f"Mode: {mode.upper()}",
            f"Hands: {hand_count}",
            f"FPS: {fps:.1f}"
        ]
        y_offset = 30
        for line in lines:
            (text_w, text_h), baseline = cv2.getTextSize(
                line, self.HUD_FONT, self.HUD_FONT_SCALE, self.HUD_FONT_THICKNESS
            )
            cv2.rectangle(
                frame,
                (10, y_offset - text_h - 5),
                (10 + text_w + 10, y_offset + 5),
                self.HUD_BG_COLOR,
                -1
            )
            cv2.putText(
                frame,
                line,
                (15, y_offset),
                self.HUD_FONT,
                self.HUD_FONT_SCALE,
                self.HUD_COLOR,
                self.HUD_FONT_THICKNESS
            )
            y_offset += text_h + 15
        return frame

    def _position_keyboard_window(self, kb_w, kb_h):
        try:
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            margin = 10
            x = screen_w - kb_w - margin
            y = screen_h - kb_h - margin - 40
            time.sleep(0.05)
            hwnd = user32.FindWindowW(None, self.KEYBOARD_WINDOW_NAME)
            if hwnd:
                user32.MoveWindow(hwnd, x, y, kb_w, kb_h, True)
                print(f"  Keyboard window positioned at bottom-right ({x}, {y})")
            else:
                print("  Warning: Could not position keyboard window (handle not found)")
        except Exception as e:
            print(f"  Warning: Could not position keyboard window: {e}")

    def cleanup(self):
        print("\nCleaning up...")
        if self.camera is not None and self.camera.isOpened():
            self.camera.release()
            print("  Camera released")
        self.gesture_tracker.cleanup()
        print("  GestureTracker cleaned up")
        cv2.destroyAllWindows()
        print("  Windows closed")
        print("\nGesture-Controlled Virtual Keyboard stopped.")
        print("=" * 60)

def show_menu():
    print("\n" + "=" * 60)
    print("GESTURE-CONTROLLED VIRTUAL KEYBOARD - MAIN MENU")
    print("=" * 60)
    print("\n1. Start Gesture Control System")
    print("2. Configure Settings (User Input)")
    print("3. View Current Settings")
    print("4. Reset to Default Settings")
    print("5. About")
    print("6. Exit")
    print("\n" + "=" * 60)
    choice = input("Enter your choice (1-6): ").strip()
    return choice

def configure_settings(settings):
    print("\n" + "=" * 60)
    print("CONFIGURE SETTINGS")
    print("=" * 60)
    print("Press Enter to keep current value\n")
    current = settings.get_all()
    user_name = input(f"Enter your name [{current['user_name']}]: ").strip()
    if user_name:
        settings.set('user_name', user_name)
    camera_index = input(f"Camera device ID [{current['camera_index']}]: ").strip()
    if camera_index.isdigit():
        settings.set('camera_index', int(camera_index))
    print("\nCamera Resolution:")
    width = input(f"  Width [{current['camera_width']}]: ").strip()
    if width.isdigit():
        settings.set('camera_width', int(width))
    height = input(f"  Height [{current['camera_height']}]: ").strip()
    if height.isdigit():
        settings.set('camera_height', int(height))
    kb_scale = input(f"Keyboard scale (0.1-1.0) [{current['keyboard_scale']}]: ").strip()
    try:
        scale_val = float(kb_scale)
        if 0.1 <= scale_val <= 1.0:
            settings.set('keyboard_scale', scale_val)
    except ValueError:
        pass
    mouse_smooth = input(f"Mouse smoothing (0.0-1.0) [{current['mouse_smoothing']}]: ").strip()
    try:
        smooth_val = float(mouse_smooth)
        if 0.0 <= smooth_val <= 1.0:
            settings.set('mouse_smoothing', smooth_val)
    except ValueError:
        pass
    max_hands = input(f"Max hands to track (1 or 2) [{current['max_hands']}]: ").strip()
    if max_hands in ['1', '2']:
        settings.set('max_hands', int(max_hands))
    print("\nSaving settings to file...")
    if settings.save_settings():
        print("[OK] Configuration saved successfully!")
    else:
        print("[ERROR] Failed to save configuration")
    input("\nPress Enter to continue...")

def view_settings(settings):
    settings.display_settings()
    input("\nPress Enter to continue...")

def reset_settings(settings):
    print("\n[!] Reset all settings to defaults?")
    confirm = input("Type 'yes' to confirm: ").strip().lower()
    if confirm == 'yes':
        settings.settings = Settings.DEFAULT_SETTINGS.copy()
        if settings.save_settings():
            print("[OK] Settings reset to defaults and saved!")
        else:
            print("[ERROR] Failed to save default settings")
    else:
        print("Reset cancelled.")
    input("\nPress Enter to continue...")

def show_about():
    print("\n" + "=" * 60)
    print("ABOUT - Gesture-Controlled Virtual Keyboard")
    print("=" * 60)
    print("\nVersion: 2.0")
    print("Author: Your Name")
    print("\nFeatures:")
    print("  [*] Real-time hand tracking (MediaPipe)")
    print("  [*] Gesture recognition (tap, pinch, C sign)")
    print("  [*] Dual mode: Keyboard (2 hands) & Mouse (1 hand)")
    print("  [*] Settings persistence (JSON file I/O)")
    print("  [*] Customizable preferences")
    print("\nControls:")
    print("  - 2 hands: Keyboard mode (tap to type)")
    print("  - 1 hand: Mouse mode (index finger controls cursor)")
    print("  - C sign: Exit application")
    print("=" * 60)
    input("\nPress Enter to continue...")

def main():
    settings = Settings()
    print("\nLoading user preferences...")
    settings.load_settings()
    while True:
        choice = show_menu()
        if choice == '1':
            try:
                print("\n" + "=" * 60)
                print("Starting gesture control system...")
                print("User:", settings.get('user_name', 'Guest'))
                print("=" * 60)
                app = GestureControlApp(settings)
                app.run()
            except RuntimeError as e:
                print(f"\nError: {e}")
                print("=" * 60)
                input("Press Enter to continue...")
            except Exception as e:
                print(f"\nUnexpected error: {e}")
                import traceback
                traceback.print_exc()
                print("=" * 60)
                input("Press Enter to continue...")
        elif choice == '2':
            configure_settings(settings)
        elif choice == '3':
            view_settings(settings)
        elif choice == '4':
            reset_settings(settings)
        elif choice == '5':
            show_about()
        elif choice == '6':
            print("\n" + "=" * 60)
            print("Thank you for using Gesture Control!")
            print(f"Goodbye, {settings.get('user_name', 'Guest')}!")
            print("=" * 60)
            break
        else:
            print("\n[ERROR] Invalid choice! Please enter 1-6.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user (Ctrl+C)")
        print("Cleaning up...")
        cv2.destroyAllWindows()

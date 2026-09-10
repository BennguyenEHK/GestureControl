import json
import os

class Settings:

    DEFAULT_SETTINGS = {
        "camera_index": 0,
        "camera_width": 1280,
        "camera_height": 720,
        "keyboard_scale": 0.95,
        "keyboard_alpha": 0.85,
        "mouse_smoothing": 0.45,
        "mouse_deadzone": 0.015,
        "mouse_input_min": 0.15,
        "mouse_input_max": 0.85,
        "mouse_debug_coords": False,
        "max_hands": 2,
        "user_name": "Guest"
    }

    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.settings = self.DEFAULT_SETTINGS.copy()

    def load_settings(self):
        if not os.path.exists(self.filename):
            print(f"[!] No settings file found ({self.filename})")
            print("    Using default settings...")
            return self.settings
        try:
            with open(self.filename, 'r') as f:
                loaded_settings = json.load(f)
            self.settings.update(loaded_settings)
            print(f"[OK] Settings loaded from '{self.filename}'")
            print(f"     User: {self.settings.get('user_name', 'Unknown')}")
            return self.settings
        except json.JSONDecodeError as e:
            print(f"[ERROR] Error parsing settings file: {e}")
            print("        Using default settings...")
            return self.settings
        except Exception as e:
            print(f"[ERROR] Error loading settings: {e}")
            print("        Using default settings...")
            return self.settings

    def save_settings(self, settings_dict=None):
        if settings_dict is not None:
            self.settings = settings_dict
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print(f"[OK] Settings saved to '{self.filename}'")
            return True
        except Exception as e:
            print(f"[ERROR] Error saving settings: {e}")
            return False

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value

    def get_all(self):
        return self.settings.copy()

    def display_settings(self):
        print("\n" + "=" * 60)
        print("CURRENT SETTINGS")
        print("=" * 60)
        for key, value in self.settings.items():
            formatted_key = key.replace('_', ' ').title()
            print(f"  {formatted_key:<20}: {value}")
        print("=" * 60)

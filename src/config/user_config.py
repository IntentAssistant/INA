import os
import json
import getpass
from .constants import (
    CONFIG_DIR,
    USER_CONFIG_FILE,
    DEFAULT_FOCUS_SOUND,
    DEFAULT_DISTRACT_SOUND,
)


class UserConfig:
    def __init__(self):
        # Expand the config directory path
        self.config_dir = os.path.expanduser(CONFIG_DIR)
        self.config_file = os.path.join(self.config_dir, USER_CONFIG_FILE)
        self._ensure_config_dir()
        self.settings = self.load_settings()

    def _ensure_config_dir(self):
        """Create config directory if not exists"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)

    def load_settings(self):
        """Load settings from config file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {}

    def save_settings(self):
        """Save settings to config file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_setting(self, key, default=None):
        """Get setting value"""
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        """Set setting value"""
        self.settings[key] = value
        self.save_settings()

    def get_user_info(self):
        """Get user information"""
        return {
            "name": self.get_setting(
                "name", ""
            ),  # No default name, must be set manually
            "device_name": self.get_setting("device_name", "mac_os_device"),
            "password": self.get_setting("password", ""),  # Password field
        }

    def set_user_info(self, name=None, device_name=None, password=None):
        """Set user information"""
        if name is not None:
            self.set_setting("name", name)
        if device_name is not None:
            self.set_setting("device_name", device_name)
        if password is not None:
            self.set_setting("password", password)

    def update_settings(self, settings):
        """Update multiple settings at once"""
        if "settings" not in self.settings:
            self.settings["settings"] = {}
        self.settings["settings"].update(settings)
        self.save_settings()

    def get_settings(self):
        """Get all settings"""
        return self.settings.get("settings", {})

    def get_sound_settings(self):
        """Get sound settings"""
        if "sound_settings" not in self.settings:
            # Initialize default sound settings
            self.settings["sound_settings"] = {
                "focus_sound": DEFAULT_FOCUS_SOUND,  # For focused state (0) - good_*.mp3
                "distract_sound": DEFAULT_DISTRACT_SOUND,  # For distracted state (1) - focus_*.mp3
            }
            self.save_settings()

        # Handle legacy settings format
        sound_settings = self.settings.get("sound_settings", {})
        if "good_sound" in sound_settings and "distract_sound" not in sound_settings:
            # Migrate from old naming to new naming
            print("Migrating sound settings from legacy format...")
            sound_settings["focus_sound"] = sound_settings.pop(
                "good_sound", DEFAULT_FOCUS_SOUND
            )
            sound_settings["distract_sound"] = sound_settings.pop(
                "focus_sound", DEFAULT_DISTRACT_SOUND
            )
            self.settings["sound_settings"] = sound_settings
            self.save_settings()

        # Remove deprecated settings
        if "good_sound" in self.settings.get("sound_settings", {}):
            print("Removing deprecated sound settings...")
            self.settings["sound_settings"].pop("good_sound", None)
            self.save_settings()

        return self.settings.get("sound_settings", {})

    def set_sound_settings(self, focus_sound=None, distract_sound=None):
        """Set sound settings"""
        if "sound_settings" not in self.settings:
            self.settings["sound_settings"] = {
                "focus_sound": DEFAULT_FOCUS_SOUND,  # For focused state (0) - good_*.mp3
                "distract_sound": DEFAULT_DISTRACT_SOUND,  # For distracted state (1) - focus_*.mp3
            }

        if focus_sound is not None:
            self.settings["sound_settings"]["focus_sound"] = focus_sound
        if distract_sound is not None:
            self.settings["sound_settings"]["distract_sound"] = distract_sound

        self.save_settings()

    # App mode methods removed (experimental feature deprecated)

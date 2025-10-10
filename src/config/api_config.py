"""
API Configuration for direct LLM integration
Supports both OpenAI GPT and Google Gemini APIs
"""

import os
import json
from enum import Enum
from typing import Optional, Dict, Any, List
from google import genai


class LLMProvider(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"


# Default provider
DEFAULT_LLM_PROVIDER = LLMProvider.OPENAI

# API Configuration
API_CONFIG = {
    "openai": {
        "display_name": "OpenAI GPT",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "models": {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "custom": "Other (Enter manually)",
        },
        "default_model": "gpt-4o",
        "max_tokens": 500,
        "temperature": 0.3,
    },
    "gemini": {
        "display_name": "Google Gemini",
        "api_key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": {
            "gemini-2.5-pro": "Gemini 2.5 Pro",
            "gemini-2.5-flash": "Gemini 2.5 Flash",
            "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
            "gemini-2.0-flash": "Gemini 2.0 Flash",
            "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
            "custom": "Other (Enter manually)",
        },
        "default_model": "gemini-2.5-flash",
        "max_tokens": 500,
        "temperature": 0.3,
    },
}

# Image processing settings for API calls
IMAGE_CONFIG = {
    "max_size_mb": 4,  # Maximum image size for API calls
    "jpeg_quality": 85,  # JPEG compression quality
    "max_dimension": 1024,  # Maximum width/height for resizing
}


class APIConfigManager:
    """Manages API configuration with file-based storage"""

    def __init__(self, config_dir: str = "~/.intention_app"):
        self.config_dir = os.path.expanduser(config_dir)
        self.config_file = os.path.join(self.config_dir, "api_config.json")
        self._ensure_config_dir()
        self._config = self._load_config()
        if self._ensure_defaults():
            self._save_config()

    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        os.makedirs(self.config_dir, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[API_CONFIG] Error loading config: {e}")

        # Return default config if file doesn't exist or is corrupted
        return {"provider": DEFAULT_LLM_PROVIDER.value, "api_keys": {}, "models": {}}

    def _ensure_defaults(self) -> bool:
        """Ensure required keys exist; returns True if config was modified"""
        changed = False
        if "provider" not in self._config:
            self._config["provider"] = DEFAULT_LLM_PROVIDER.value
            changed = True
        if "api_keys" not in self._config:
            self._config["api_keys"] = {}
            changed = True
        if "models" not in self._config:
            self._config["models"] = {}
            changed = True
        debug_cfg = self._config.get("debug")
        if not isinstance(debug_cfg, dict):
            self._config["debug"] = {"save_images": False}
            changed = True
        else:
            if "save_images" not in debug_cfg:
                debug_cfg["save_images"] = False
                changed = True
        if "exclude_dashboard_from_capture" not in self._config:
            self._config["exclude_dashboard_from_capture"] = True
            changed = True
        return changed

    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[API_CONFIG] Error saving config: {e}")

    def set_api_key(self, provider: LLMProvider, api_key: str):
        """Set API key for a provider"""
        self._config["api_keys"][provider.value] = api_key
        self._save_config()

    def get_api_key(self, provider: LLMProvider) -> str:
        """Get API key for a provider (file first, then environment)"""
        # Try file-based config first
        api_key = self._config["api_keys"].get(provider.value, "")
        if api_key:
            return api_key

        # Fallback to environment variable
        env_var = API_CONFIG[provider.value]["api_key_env"]
        return os.getenv(env_var, "")

    def set_model(self, provider: LLMProvider, model: str):
        """Set model for a provider"""
        self._config["models"][provider.value] = model
        self._save_config()

    def get_model(self, provider: LLMProvider) -> str:
        """Get model for a provider"""
        return self._config["models"].get(
            provider.value, API_CONFIG[provider.value]["default_model"]
        )

    def set_provider(self, provider: LLMProvider):
        """Set the active provider"""
        self._config["provider"] = provider.value
        self._save_config()

    def get_provider(self) -> LLMProvider:
        """Get the active provider"""
        try:
            return LLMProvider(self._config["provider"])
        except (ValueError, KeyError):
            return DEFAULT_LLM_PROVIDER

    def is_api_configured(self, provider: LLMProvider) -> bool:
        """Check if API is properly configured"""
        api_key = self.get_api_key(provider)
        return bool(api_key and api_key.strip())

    def get_configured_providers(self) -> list[LLMProvider]:
        """Get list of configured providers"""
        configured = []
        for provider in LLMProvider:
            if self.is_api_configured(provider):
                configured.append(provider)
        return configured

    def get_model_config(self, provider: LLMProvider) -> dict:
        """Get model configuration for the specified provider"""
        config = API_CONFIG[provider.value].copy()
        config["model"] = self.get_model(provider)
        return config

    def set_selected_display(self, display_index: int):
        """Set the selected display index"""
        self._config["selected_display"] = display_index
        self._save_config()

    def get_selected_display(self) -> int:
        """Get the selected display index (default: 0 for primary display)"""
        return self._config.get("selected_display", 0)

    def set_sound_enabled(self, enabled: bool):
        """Set whether notification sounds are enabled"""
        self._config["sound_enabled"] = enabled
        self._save_config()

    def get_sound_enabled(self) -> bool:
        """Get whether notification sounds are enabled (default: True)"""
        return self._config.get("sound_enabled", True)

    def set_on_task_sound(self, sound_file: str):
        """Set the sound file for on-task notifications"""
        self._config["on_task_sound"] = sound_file
        self._save_config()

    def get_on_task_sound(self) -> str:
        """Get the on-task sound file (default: on_task_1.mp3)"""
        return self._config.get("on_task_sound", "on_task_1.mp3")

    def set_off_task_sound(self, sound_file: str):
        """Set the sound file for off-task notifications"""
        self._config["off_task_sound"] = sound_file
        self._save_config()

    def get_off_task_sound(self) -> str:
        """Get the off-task sound file (default: off_task_1.mp3)"""
        return self._config.get("off_task_sound", "off_task_1.mp3")

    def set_notification_enabled(self, enabled: bool):
        """Set whether notifications are enabled"""
        self._config["notification_enabled"] = enabled
        self._save_config()

    def get_notification_enabled(self) -> bool:
        """Get whether notifications are enabled (default: True)"""
        return self._config.get("notification_enabled", True)

    def set_float_on_top(self, enabled: bool):
        """Set whether dashboard floats on top"""
        self._config["float_on_top"] = enabled
        self._save_config()

    def get_float_on_top(self) -> bool:
        """Get whether dashboard floats on top (default: True)"""
        return self._config.get("float_on_top", True)

    def set_exclude_dashboard_from_capture(self, enabled: bool):
        """Set whether the dashboard is excluded from screen capture"""
        self._config["exclude_dashboard_from_capture"] = bool(enabled)
        self._save_config()

    def get_exclude_dashboard_from_capture(self) -> bool:
        """Get whether the dashboard is excluded from screen capture (default: True)"""
        return bool(self._config.get("exclude_dashboard_from_capture", True))

    def set_debug_save_images(self, enabled: bool):
        """Enable or disable saving debug screenshots"""
        debug_cfg = self._config.setdefault("debug", {})
        debug_cfg["save_images"] = bool(enabled)
        self._save_config()

    def get_debug_save_images(self) -> bool:
        """Return whether debug screenshots should be saved"""
        debug_cfg = self._config.get("debug", {})
        return bool(debug_cfg.get("save_images", False))


# Global instance
_api_config_manager = None


def fetch_available_gemini_models(api_key: str) -> Dict[str, str]:
    """
    Fetch available Gemini models from the API (new SDK)

    Args:
        api_key: Gemini API key

    Returns:
        Dict mapping model IDs to display names
    """
    client = None
    try:
        if not api_key:
            print("[API_CONFIG] No Gemini API key provided - using default model list")
            return API_CONFIG["gemini"]["models"]

        os.environ["GOOGLE_API_KEY"] = api_key
        client = genai.Client(api_key=api_key)
        models = {}

        print("[API_CONFIG] Fetching available Gemini models...")
        print("[API_CONFIG] ==================== ALL MODELS ====================")

        all_gemini_models = []
        models_response = client.models.list()

        for model in models_response:
            model_id = model.name.replace("models/", "")

            # Print ALL models for debugging
            print(f"[API_CONFIG] Model: {model_id}")
            print(f"  - Full name: {model.name}")

            # Exclude image/video generation models (imagen, veo, etc.)
            if any(
                exclude in model_id.lower()
                for exclude in ["imagen", "veo", "image", "video"]
            ):
                print(f"  ❌ Skipped: Image/video generation model")
                continue

            # Only include gemini-* models
            if not model_id.startswith("gemini"):
                print(f"  ❌ Skipped: Not a gemini model")
                continue

            # Exclude audio/voice/TTS/special feature models (only keep VLM)
            exclude_keywords = [
                "lite",  # Lite versions
                "audio",  # Audio models
                "voice",  # Voice models
                "tts",  # Text-to-speech
                "thinking",  # Thinking models (show reasoning)
                "dialog",  # Dialog-specific models
                "live",  # Live/streaming models
                "native",  # Native audio/video
                "preview",  # Preview/experimental versions
            ]

            if any(keyword in model_id.lower() for keyword in exclude_keywords):
                excluded_reason = next(
                    kw for kw in exclude_keywords if kw in model_id.lower()
                )
                print(
                    f"  ❌ Skipped: Contains '{excluded_reason}' (not a standard VLM)"
                )
                continue

            all_gemini_models.append(model_id)
            print(f"  ✅ Added to list")

        print(
            "[API_CONFIG] ==================== PROCESSING MODELS ===================="
        )

        # Process all gemini models
        for model_id in all_gemini_models:
            # Create a friendly display name
            display_name = model_id.replace("gemini-", "Gemini ")
            display_name = display_name.replace("-", " ").title()

            # Add markers based on version
            if "2.5-pro" in model_id:
                display_name += " (Most Capable)"
            elif "2.5-flash" in model_id:
                display_name += " (Fast & Latest)"
            elif "2.0-flash" in model_id:
                display_name += " (Recommended)"
            elif "exp" in model_id:
                display_name += " (Experimental)"
            elif "1.5-pro" in model_id:
                display_name += " (Stable)"

            models[model_id] = display_name
            print(f"[API_CONFIG] ✅ {model_id} -> {display_name}")

        # Sort by version (2.5 > 2.0 > exp > 1.5)
        sorted_models = {}
        for prefix in [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]:
            for model_id, name in sorted(models.items()):
                if model_id.startswith(prefix) and model_id not in sorted_models:
                    sorted_models[model_id] = name

        print(f"[API_CONFIG] Total models found: {len(sorted_models)}")
        return sorted_models if sorted_models else API_CONFIG["gemini"]["models"]

    except Exception as e:
        print(f"[API_CONFIG] Failed to fetch Gemini models: {e}")
        import traceback

        traceback.print_exc()
        return API_CONFIG["gemini"]["models"]
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def fetch_available_openai_models(api_key: str) -> Dict[str, str]:
    """
    Fetch available OpenAI models from the API

    Args:
        api_key: OpenAI API key

    Returns:
        Dict mapping model IDs to display names
    """
    try:
        import requests

        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            "https://api.openai.com/v1/models", headers=headers, timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            models = {}

            # Filter to only GPT-4 and GPT-4o models
            for model in data.get("data", []):
                model_id = model["id"]
                if model_id.startswith("gpt-4"):
                    if model_id in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4"]:
                        display_name = API_CONFIG["openai"]["models"].get(
                            model_id, model_id.upper()
                        )
                        models[model_id] = display_name

            return models if models else API_CONFIG["openai"]["models"]
        else:
            return API_CONFIG["openai"]["models"]

    except Exception as e:
        print(f"[API_CONFIG] Failed to fetch OpenAI models: {e}")
        return API_CONFIG["openai"]["models"]


def get_api_config_manager() -> APIConfigManager:
    """Get the global API configuration manager"""
    global _api_config_manager
    if _api_config_manager is None:
        _api_config_manager = APIConfigManager()
    return _api_config_manager


def is_api_configured(provider: LLMProvider) -> bool:
    """Check if API is properly configured"""
    return get_api_config_manager().is_api_configured(provider)

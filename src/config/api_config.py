"""
API Configuration for direct LLM integration
Supports both OpenAI GPT and Google Gemini APIs
"""

import os
import json
from enum import Enum
from typing import Optional, Dict, Any


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
            "gpt-4o": "GPT-4o (Latest, Recommended)",
            "gpt-4o-mini": "GPT-4o Mini (Faster, Cheaper)",
            "gpt-4-turbo": "GPT-4 Turbo (Previous)",
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
            "gemini-2.5-pro": "Gemini 2.5 Pro (Most Capable)",
            "gemini-2.5-flash": "Gemini 2.5 Flash",
            "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
            "gemini-2.0-flash": "Gemini 2.0 Flash (Recommended)",
            "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
        },
        "default_model": "gemini-2.0-flash",
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


# Global instance
_api_config_manager = None


def get_api_config_manager() -> APIConfigManager:
    """Get the global API configuration manager"""
    global _api_config_manager
    if _api_config_manager is None:
        _api_config_manager = APIConfigManager()
    return _api_config_manager


# Legacy functions for backward compatibility
def get_api_key(provider: LLMProvider) -> str:
    """Get API key from configuration manager"""
    return get_api_config_manager().get_api_key(provider)


def get_model_config(provider: LLMProvider) -> dict:
    """Get model configuration for the specified provider"""
    return get_api_config_manager().get_model_config(provider)


def is_api_configured(provider: LLMProvider) -> bool:
    """Check if API is properly configured"""
    return get_api_config_manager().is_api_configured(provider)

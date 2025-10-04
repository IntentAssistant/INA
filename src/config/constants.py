# App Version - Change this when releasing a new version
APP_VERSION = "1.0.1"

# API Settings - Direct LLM Integration
# Configure API keys via the UI (Settings > User Settings > Configure API Settings)
# Or set environment variables:
# export OPENAI_API_KEY="your-openai-api-key"
# export GEMINI_API_KEY="your-gemini-api-key"

# Storage Settings - Images no longer stored locally
# Only configuration and session data are stored
DEFAULT_STORAGE_DIR = "~/AIM_Data"
CONFIG_DIR = "~/.intention_app"
USER_CONFIG_FILE = "user_config.json"
PROMPT_CONFIG_FILE = "prompt_config.json"

# Sound Settings
DEFAULT_FOCUS_SOUND = "good_1.mp3"  # For focused state (0) - focused
DEFAULT_DISTRACT_SOUND = "focus_1.mp3"  # For distracted state (1) - distracted

# Capture Settings
CAPTURE_INTERVAL = 2
IMAGE_QUALITY = 85  # JPEG compression quality (0-100)
IMAGE_SCALE = (
    3  # Screen capture downscaling factor (e.g., 3 means 1/3 of original size)
)

# LLM Settings

LLM_INVOKE_INTERVAL = 2
LLM_ANALYSIS_IMAGE_COUNT = 1  # Always analyze only 1 image (most recent)
LLM_INTERVAL = 2
MAX_CONCURRENT_ANALYSIS_THREADS = 4  # Maximum number of concurrent LLM analysis threads


# UI Settings
WINDOW_MIN_WIDTH = 300
WINDOW_MIN_HEIGHT = 300
PROMPT_WINDOW_WIDTH = 600
PROMPT_WINDOW_HEIGHT = 400

# Messages
APP_START_MESSAGE = "Click the intention app icon in the menu bar to use"
SETTINGS_REQUIRED_MESSAGE = "User ID is required to participate in the study"

# Notification Settings
NOTIFICATION_ENABLED = True  # Enable/disable notifications

DEFAULT_TONE = "neutral"

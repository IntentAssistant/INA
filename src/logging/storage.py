import os
import json
import sys
from datetime import datetime
from PIL import Image
from ..config.constants import DEFAULT_STORAGE_DIR


class LocalStorage:
    def __init__(self):
        self.setup_storage_directory()
        self.user_name = "unknown"
        self.task_name = "N/A (no_task)"
        self.task_start_time = None  # 시간 추가
        # Ensure all required files exist after directory setup
        self.ensure_required_files()

    def setup_storage_directory(self):
        """Setup storage directory structure for app data (no image storage)"""
        # Use the DEFAULT_STORAGE_DIR from constants (mode-specific directory)
        base_storage_dir = os.path.expanduser(DEFAULT_STORAGE_DIR)

        # Create the base storage directory structure (no screenshots dir)
        self.app_data_dir = base_storage_dir

        # Create subdirectories for intention data only
        self.intention_history_dir = os.path.join(
            self.app_data_dir, "intention_history"
        )
        self.clarification_data_dir = os.path.join(
            self.app_data_dir, "clarification_data"
        )
        self.session_data_dir = os.path.join(self.app_data_dir, "session_data")
        self.debug_image_dir = os.path.join(self.app_data_dir, "debug_analysis_images")

        # Ensure all required directories exist (no screenshots)
        os.makedirs(self.app_data_dir, exist_ok=True)
        os.makedirs(self.intention_history_dir, exist_ok=True)
        os.makedirs(self.clarification_data_dir, exist_ok=True)
        os.makedirs(self.session_data_dir, exist_ok=True)
        os.makedirs(self.debug_image_dir, exist_ok=True)

        # Only print directory info once during app initialization
        print(f"[STORAGE] Data directory: {self.app_data_dir}")
        print(
            f"[STORAGE] Images are no longer stored locally - processed in memory only"
        )

        # Set storage_dir to session data directory
        self.storage_dir = self.session_data_dir

    def ensure_required_files(self):
        """Ensure all required files exist with proper initial content"""
        try:
            # Create intention history file if it doesn't exist
            history_file = os.path.join(
                self.intention_history_dir, "intention_history.json"
            )
            if not os.path.exists(history_file):
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                print(f"[STORAGE] Created intention history file: {history_file}")

            # Create sample clarification data structure if directory is empty
            if not os.listdir(self.clarification_data_dir):
                # Create a sample clarification file to establish the structure
                sample_clarification = {
                    "sample": True,
                    "message": "This is a sample clarification file created during initialization",
                    "timestamp": datetime.now().isoformat(),
                }
                sample_file = os.path.join(
                    self.clarification_data_dir, "sample_clarification.json"
                )
                with open(sample_file, "w", encoding="utf-8") as f:
                    json.dump(sample_clarification, f, ensure_ascii=False, indent=2)
                print(f"[STORAGE] Created sample clarification file: {sample_file}")

            print(
                "[STORAGE] All required files and directories initialized successfully"
            )

        except Exception as e:
            print(f"[ERROR] Failed to create required files: {e}")

    def set_user_name(self, name):
        self.user_name = name if name else "unknown"

    def set_current_task(self, task, session_id=None):
        """Set current task name and session ID"""
        self.task_name = task if task else "N/A (no_task)"

        if session_id:
            # Use provided session_id directly
            self.task_start_time = session_id
            print(f"[STORAGE] Using provided session_id: {session_id}")
        else:
            # Fallback: generate timestamp (for backward compatibility)
            self.task_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"[STORAGE] Generated new timestamp: {self.task_start_time}")

        session_dir = self.get_capture_dir()
        os.makedirs(session_dir, exist_ok=True)
        print(f"[STORAGE] Session data directory: {session_dir}")

    def get_capture_dir(self):
        """Return the directory path for storing captures"""
        if not ("N/A (no_task)" in self.task_name) and self.task_start_time:
            return os.path.join(
                self.storage_dir, f"{self.task_name}_{self.task_start_time}"
            )
        return self.storage_dir

    def get_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_debug_image_dir(self):
        """Return the directory used for storing debug screenshots"""
        os.makedirs(self.debug_image_dir, exist_ok=True)
        return self.debug_image_dir

    def save_image(self, image):
        """Deprecated: Images are no longer saved locally"""
        print("[STORAGE] Image saving disabled - images processed in memory only")
        return None, None

    def save_llm_result(self, result: dict):
        """Append full LLM result to a JSON log file - simple version without rotation"""
        entry = {
            "timestamp": self.get_timestamp(),
            "result": result,  # Save the full result object
        }

        save_dir = self.get_capture_dir()
        result_path = os.path.join(save_dir, "_llm_results.json")

        # Load existing if any
        if os.path.exists(result_path):
            try:
                with open(result_path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = []
        else:
            data = []

        data.append(entry)

        # Save updated log
        with open(result_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_intention_history_dir(self):
        """Return the directory path for storing intention history"""
        return self.intention_history_dir

    def get_clarification_data_dir(self):
        """Return the directory path for storing clarification data"""
        return self.clarification_data_dir

    def save_reflection_data(self, reflection_data: dict):
        """Save reflection data to a JSON log file - simple version without rotation"""
        entry = {"timestamp": self.get_timestamp(), "reflection": reflection_data}

        save_dir = self.get_capture_dir()
        reflection_path = os.path.join(save_dir, "_reflections.json")

        # Load existing if any
        if os.path.exists(reflection_path):
            try:
                with open(reflection_path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = []
        else:
            data = []

        data.append(entry)

        # Save updated log
        with open(reflection_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"[STORAGE] Reflection data saved to {reflection_path}")

    def save_feedback(self, feedback_data: dict):
        """Save user feedback to a JSON log file"""
        entry = {"timestamp": self.get_timestamp(), "feedback": feedback_data}

        save_dir = self.get_capture_dir()
        feedback_path = os.path.join(save_dir, "_feedbacks.json")

        # Load existing if any
        if os.path.exists(feedback_path):
            try:
                with open(feedback_path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = []
        else:
            data = []

        data.append(entry)

        # Save updated log
        with open(feedback_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"[STORAGE] Feedback saved to {feedback_path}")

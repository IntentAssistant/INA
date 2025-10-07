"""
LLM client functionality for the dashboard
Handles API communication with the LLM service
"""

import json
import os
import requests
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from ..config.language import get_text

# Import LocalStorage to get proper directory paths
from ..logging.storage import LocalStorage

# Import prompt functions from the new prompts module
from ..config.prompts import format_clarification_prompt, format_augmentation_prompt

# Import direct LLM client
from ..utils.direct_llm_client import get_configured_client


class ClarificationManager:
    """Manages the 2-turn clarification process"""

    def __init__(self, dashboard):
        # Use LocalStorage to get the proper directory path
        self.storage = LocalStorage()
        self.reset()
        self.dashboard = dashboard

    def reset(self):
        """Reset the clarification process"""
        self.stated_intention = ""
        self.qa_pairs = []
        self.current_turn = 0
        self.max_turns = 2
        self.is_complete = False

    def start_clarification(self, intention):
        """Start a new clarification process"""
        self.reset()
        self.stated_intention = intention
        return self.get_next_question_prompt()

    def add_qa_pair(self, question, answer):
        """Add a question-answer pair"""
        self.qa_pairs.append((question, answer))
        self.current_turn += 1

        if self.current_turn >= self.max_turns:
            self.is_complete = True
            return None
        else:
            return self.get_next_question_prompt()

    def get_next_question_prompt(self):
        """Generate prompt for the next clarification question"""
        first_qa = self.qa_pairs[0] if len(self.qa_pairs) > 0 else ("", "")
        second_qa = self.qa_pairs[1] if len(self.qa_pairs) > 1 else ("", "")

        # Prepare QA strings separately to avoid f-string backslash issues
        first_qa_str = f"Q: {first_qa[0]}\nA: {first_qa[1]}" if first_qa[0] else ""
        second_qa_str = f"Q: {second_qa[0]}\nA: {second_qa[1]}" if second_qa[0] else ""

        # Use the new prompt formatting function
        return format_clarification_prompt(
            stated_intention=self.stated_intention,
            first_qa=first_qa_str,
            second_qa=second_qa_str,
        )

    def get_augmentation_prompt(self):
        """Generate prompt for intention augmentation after clarification is complete"""
        # Prepare clarification block separately to avoid f-string backslash issues
        clarification_block = "\n\n".join([f"Q: {q}\nA: {a}" for q, a in self.qa_pairs])

        # Use the new prompt formatting function
        return format_augmentation_prompt(
            stated_intention=self.stated_intention,
            clarification_block=clarification_block,
        )

    def save_results(self, augmented_intentions=None):
        """Save clarification results to JSON file"""
        # Prepare clarification block separately to avoid f-string backslash issues
        clarification_block = "\n\n".join([f"Q: {q}\nA: {a}" for q, a in self.qa_pairs])

        result = {
            "stated_intention": self.stated_intention,
            "clarification_QAs": clarification_block,
            "qa_pairs": self.qa_pairs,
            "timestamp": datetime.now().isoformat(),
        }

        if augmented_intentions:
            result["augmented_intentions"] = augmented_intentions

        # Save to clarification_data directory with session-based filename
        # Get session_id from dashboard if available
        session_id = None
        if hasattr(self, "dashboard") and self.dashboard:
            session_id = getattr(self.dashboard, "current_session_start_time", None)

        if session_id:
            # Use session_id for unique filename
            filename = f"{session_id}_clarification.json"
            print(f"[CLARIFICATION] Saving with session_id: {session_id}")
        else:
            # Fallback to old method if session_id not available
            clean_task_name = "".join(
                c for c in self.stated_intention if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            clean_task_name = clean_task_name.replace(" ", "_")
            filename = f"{clean_task_name}_clarification.json"
            print(f"[CLARIFICATION] Fallback: Saving with task name: {clean_task_name}")

        filepath = os.path.join(self.storage.get_clarification_data_dir(), filename)

        try:
            # Create directory if it doesn't exist
            os.makedirs(self.storage.get_clarification_data_dir(), exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

            print(f"[CLARIFICATION] Saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"[CLARIFICATION] Error saving results: {e}")
            return None


class ClarificationThread(QThread):
    """Thread for handling LLM API calls for clarification"""

    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt, dashboard=None, parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.dashboard = dashboard
        self.setObjectName(f"ClarificationThread_{id(self)}")
        # Add thread termination flag
        self._is_stopping = False
        # Add timeout for network requests
        self._request_timeout = 30  # 30 seconds for clarification
        self.llm_client = None

    def __del__(self):
        """Safe destructor to prevent crash during garbage collection"""
        try:
            if self.isRunning():
                self.terminate()
                self.wait(100)  # Short wait
        except:
            pass  # Ignore any errors during destruction

    def safe_quit(self):
        """Safe method to quit the thread"""
        try:
            print(f"[CLARIFICATION_THREAD] Safely quitting thread")
            self._is_stopping = True

            # Clean up LLM client if any
            if hasattr(self, "llm_client") and self.llm_client:
                self.llm_client = None

            if self.isRunning():
                # Try graceful quit first
                self.quit()
                if not self.wait(1000):  # Wait 1 second for graceful quit
                    print(
                        f"[CLARIFICATION_THREAD] Graceful quit failed, using terminate"
                    )
                    self.terminate()
                    if not self.wait(1000):  # Wait another second for terminate
                        print(
                            f"[CLARIFICATION_THREAD] Thread did not terminate gracefully"
                        )
                    else:
                        print(f"[CLARIFICATION_THREAD] Thread terminated successfully")
                else:
                    print(f"[CLARIFICATION_THREAD] Thread quit gracefully")

            self.deleteLater()
        except Exception as e:
            print(f"[CLARIFICATION_THREAD] Error in safe_quit: {e}")

    def run(self):
        try:
            # Check for thread termination request
            if self._is_stopping:
                print("Clarification thread termination requested before starting")
                return

            # Get configured LLM client
            try:
                self.llm_client = get_configured_client()
                if not self.llm_client:
                    self.error_occurred.emit(
                        "No LLM API configured. Please set OPENAI_API_KEY or GEMINI_API_KEY environment variable."
                    )
                    return
            except Exception as e:
                self.error_occurred.emit(f"Failed to initialize LLM client: {str(e)}")
                return

            # Simple request logging
            if "augment" in self.prompt.lower() or "variation" in self.prompt.lower():
                print("[CLARIFICATION] Requesting augmentation")
            elif hasattr(self.dashboard, "llm_client") and hasattr(
                self.dashboard.llm_client, "clarification_manager"
            ):
                step = self.dashboard.llm_client.clarification_manager.current_turn + 1
                print(f"[CLARIFICATION] Question {step}/2")
            else:
                print("[CLARIFICATION] Starting clarification")

            print(f"[CLARIFICATION] Using provider: {self.llm_client.provider.value}")

            # Check termination before API request
            if self._is_stopping:
                print("Clarification thread termination requested before API call")
                return

            # Prepare context for clarification
            context = {
                "user_id": "local_user",
                "session_id": (
                    getattr(
                        self.dashboard,
                        "current_session_start_time",
                        "intention_session",
                    )
                    if self.dashboard
                    else "intention_session"
                ),
                "task_name": (
                    getattr(self.dashboard, "current_task", "Clarification")
                    if self.dashboard
                    else "Clarification"
                ),
                "intention": (
                    getattr(self.dashboard, "current_task", "Clarification chat")
                    if self.dashboard
                    else "Clarification chat"
                ),
                "device_name": "mac_os_device",
            }

            # Get clarification question using direct LLM API
            ai_response = self.llm_client.get_clarification_question(
                prompt=self.prompt, context=context
            )

            # Check for thread termination request
            if self._is_stopping:
                print("Clarification thread termination requested after API call")
                return

            print(f"[CLARIFICATION] Response: {ai_response}")
            self.response_received.emit(ai_response)

        except Exception as e:
            if not self._is_stopping:  # Only emit error signal if not terminating
                error_msg = f"Unexpected error: {str(e)}"
                print(f"[CLARIFICATION] Error: {error_msg}")
                self.error_occurred.emit(error_msg)
            else:
                print(
                    f"[CLARIFICATION_THREAD] Thread stopped, suppressing error: {str(e)}"
                )


class LLMClient:
    """Manages LLM API communication for the dashboard"""

    def __init__(self, parent_dashboard):
        self.dashboard = parent_dashboard
        self.clarification_thread = None
        self.clarification_manager = ClarificationManager(dashboard=parent_dashboard)

    def request_initial_clarification(self, prompt):
        """Request clarification question from LLM API using the provided prompt"""

        # Show loading message with animation
        self.dashboard.add_clarification_message(get_text("loading"), is_user=False)

        # Create and start clarification thread
        self.clarification_thread = ClarificationThread(
            prompt=prompt, dashboard=self.dashboard, parent=self.dashboard
        )

        # Connect signals
        self.clarification_thread.response_received.connect(
            self.dashboard.on_clarification_question_received
        )
        self.clarification_thread.error_occurred.connect(
            self.dashboard.on_clarification_error
        )

        # Start the thread
        self.clarification_thread.start()

    def send_clarification_message(self, message, conversation_history):
        """Send clarification message to LLM API (deprecated - use new cycle methods)"""

        # Show loading message with animation
        self.dashboard.add_clarification_message(get_text("loading"), is_user=False)

        # Create and start clarification thread
        self.clarification_thread = ClarificationThread(
            prompt=message, dashboard=self.dashboard, parent=self.dashboard
        )

        # Connect signals
        self.clarification_thread.response_received.connect(
            self.dashboard.on_clarification_question_received
        )
        self.clarification_thread.error_occurred.connect(
            self.dashboard.on_clarification_error
        )

        # Start the thread
        self.clarification_thread.start()

    def request_augmentation(self):
        """Request intention augmentation after clarification is complete"""
        if not self.clarification_manager.is_complete:
            print("[CLARIFICATION] Not yet complete, cannot request augmentation")
            return

        augmentation_prompt = self.clarification_manager.get_augmentation_prompt()

        # Show loading message with animation
        self.dashboard.add_clarification_message(get_text("loading"), is_user=False)

        # Create and start clarification thread for augmentation
        self.clarification_thread = ClarificationThread(
            prompt=augmentation_prompt, dashboard=self.dashboard, parent=self.dashboard
        )

        # Connect signals
        self.clarification_thread.response_received.connect(
            self.dashboard.on_augmentation_received
        )
        self.clarification_thread.error_occurred.connect(
            self.dashboard.on_clarification_error
        )

        # Start the thread
        self.clarification_thread.start()

    def cleanup(self):
        """Clean up any running threads - Enhanced for safe shutdown"""
        print("[LLM_CLIENT] Cleaning up clarification threads...")
        if self.clarification_thread and self.clarification_thread.isRunning():
            print("[LLM_CLIENT] Safely quitting clarification thread...")
            self.clarification_thread.safe_quit()
            if not self.clarification_thread.wait(2000):  # Wait up to 2 seconds
                print("[LLM_CLIENT] Clarification thread did not terminate gracefully")
                self.clarification_thread.terminate()
                self.clarification_thread.wait(1000)
            self.clarification_thread = None
        print("[LLM_CLIENT] Clarification cleanup complete")

    def start_clarification_cycle(self, intention):
        """Start a new clarification cycle"""
        prompt = self.clarification_manager.start_clarification(intention)
        self.request_initial_clarification(prompt)

    def add_user_answer(self, answer):
        """Add user answer and get next question or complete the cycle"""
        # Get the last question from the conversation
        last_question = self.dashboard.get_last_ai_message()

        if last_question:
            # Add the Q&A pair and get next prompt
            next_prompt = self.clarification_manager.add_qa_pair(last_question, answer)

            if next_prompt:
                # Continue with next question

                self.request_initial_clarification(next_prompt)
            else:
                # Clarification complete, request augmentation

                self.request_augmentation()
        else:
            pass  # No previous AI message found - continue silently

    def handle_clarification_completion(self):
        """Handle the completion of the clarification process"""
        self.dashboard.add_clarification_message(
            get_text("clarification_complete"), is_user=False
        )
        self.request_augmentation()

    def get_augmentation_prompt(self):
        """Get the augmentation prompt for the current clarification cycle"""
        return self.clarification_manager.get_augmentation_prompt()

    def save_results(self, augmented_intentions=None):
        """Save clarification results to JSON file"""
        return self.clarification_manager.save_results(augmented_intentions)

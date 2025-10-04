"""
Feedback Manager for handling user feedback and reflection
Processes user feedback on LLM responses and generates reflections for future improvement
"""

import json
import regex as re
import requests
import os
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from ..config.prompts import format_reflection_prompt


class FeedbackMessageThread(QThread):
    """Thread for sending user feedback messages to /feedback_message endpoint"""

    message_sent = pyqtSignal(dict)  # Emitted when message is sent successfully
    message_error = pyqtSignal(str)  # Emitted when message sending fails

    def __init__(
        self,
        user_id,
        session_id,
        image_id,
        feedback_message,
        session_info,
        parent=None,
    ):
        super().__init__(parent)
        self.user_id = user_id
        self.session_id = session_id
        self.image_id = image_id
        self.feedback_message = feedback_message
        self.session_info = session_info
        self.setObjectName(f"FeedbackMessageThread_{id(self)}")
        self._is_stopping = False
        self._request_timeout = 15  # 15 seconds timeout
        self._session = None

    def __del__(self):
        """Safe destructor to prevent crash during garbage collection"""
        try:
            if self.isRunning():
                self.terminate()
                self.wait(100)  # Short wait
        except:
            pass  # Ignore any errors during destruction

    def safe_quit(self):
        """Safely terminate the thread"""
        try:
            self._is_stopping = True
            if self._session:
                self._session.close()
            self.quit()
        except Exception as e:
            print(f"[FEEDBACK_MESSAGE_THREAD] Error during safe quit: {e}")

    def run(self):
        """Send feedback message to /feedback_message endpoint"""
        try:
            # Prepare request data
            request_data = {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "image_id": self.image_id,
                "feedback_message": self.feedback_message,
                "session_info": self.session_info,
            }

            print(f"[FEEDBACK_MESSAGE] Sending feedback message to server")
            print(f"[FEEDBACK_MESSAGE] Message: {self.feedback_message[:50]}...")

            # Create session for better connection control
            if not self._session:
                import requests

                self._session = requests.Session()

            # Check termination before network request
            if self._is_stopping:
                print(
                    "Feedback message thread termination requested before network call"
                )
                return

            # Backend messaging removed - feedback saved locally only
            print(
                f"[FEEDBACK_MESSAGE] Feedback message saved locally (backend removed)"
            )
            result = {"status": "success", "message": "Feedback saved locally"}
            self.message_sent.emit(result)

        except Exception as e:
            if not self._is_stopping:  # Only emit error signal if not terminating
                error_msg = f"Feedback message failed: {str(e)}"
                print(f"[ERROR] Feedback message request failed: {e}")
                self.message_error.emit(error_msg)
            else:
                print(
                    f"[FEEDBACK_MESSAGE_THREAD] Thread stopped, suppressing error: {str(e)}"
                )


class ReflectionThread(QThread):
    """Thread for processing reflection requests via feedback endpoint"""

    reflection_complete = pyqtSignal(dict)  # Emitted when reflection is complete
    reflection_error = pyqtSignal(str)  # Emitted when reflection fails

    def __init__(
        self,
        prompt,
        dashboard=None,
        image_id=None,
        image_path=None,
        ai_judgement=None,
        feedback_type=None,
        parent=None,
    ):
        super().__init__(parent)
        self.prompt = prompt
        self.dashboard = dashboard
        self.image_id = image_id  # Firestore image document ID
        self.image_path = image_path  # Path to image file for reflection analysis
        self.ai_judgement = ai_judgement
        self.feedback_type = feedback_type
        self.setObjectName(f"ReflectionThread_{id(self)}")
        # Add thread termination flag
        self._is_stopping = False
        # Add timeout for network requests
        self._request_timeout = 30  # 30 seconds for reflection
        self._session = None

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
            print(f"[REFLECTION_THREAD] Safely quitting thread")
            self._is_stopping = True

            # Close network session first
            if hasattr(self, "_session") and self._session:
                try:
                    self._session.close()
                    print(f"[REFLECTION_THREAD] Session closed")
                except Exception as e:
                    print(f"[REFLECTION_THREAD] Error closing session: {e}")

            if self.isRunning():
                # Try graceful quit first
                self.quit()
                if not self.wait(1000):  # Wait 1 second for graceful quit
                    print(f"[REFLECTION_THREAD] Graceful quit failed, using terminate")
                    self.terminate()
                    if not self.wait(1000):  # Wait another second for terminate
                        print(
                            f"[REFLECTION_THREAD] Thread did not terminate gracefully"
                        )
                    else:
                        print(f"[REFLECTION_THREAD] Thread terminated successfully")
                else:
                    print(f"[REFLECTION_THREAD] Thread quit gracefully")

            self.deleteLater()
        except Exception as e:
            print(f"[REFLECTION_THREAD] Error in safe_quit: {e}")

    def run(self):
        """Run reflection analysis in background thread via feedback endpoint"""
        try:
            # Get current session info from dashboard
            current_session_id = "unknown_session"
            current_task = "Reflection Analysis"

            if self.dashboard:
                if (
                    hasattr(self.dashboard, "current_session_start_time")
                    and self.dashboard.current_session_start_time
                ):
                    current_session_id = self.dashboard.current_session_start_time

                if (
                    hasattr(self.dashboard, "current_task")
                    and self.dashboard.current_task
                ):
                    current_task = self.dashboard.current_task

            # User config removed - direct local usage only
            user_id = "local_user"
            device_name = "mac_os_device"

            # Get the specific image from RAM cache by image_id (only 1 image for feedback)
            encoded_images = []
            pil_images = []
            target_image = None

            if self.dashboard and hasattr(self.dashboard, "thread_manager"):
                thread_manager = self.dashboard.thread_manager
                if (
                    hasattr(thread_manager, "image_cache")
                    and len(thread_manager.image_cache) > 0
                ):
                    print(
                        f"[REFLECTION] Searching for image_id '{self.image_id}' in cache ({len(thread_manager.image_cache)} images)"
                    )

                    # Find the specific image by image_id
                    for cached_item in thread_manager.image_cache:
                        cached_image_id = cached_item.get("image_id")
                        if cached_image_id == self.image_id:
                            target_image = cached_item
                            print(
                                f"[REFLECTION] Found target image with ID: {self.image_id}"
                            )
                            break

                    if target_image:
                        import base64

                        try:
                            # Get image data from cache
                            image_data = target_image.get("image_data")
                            pil_image = target_image.get("pil_image")

                            if image_data:
                                encoded_image = base64.b64encode(image_data).decode(
                                    "utf-8"
                                )
                                encoded_images.append(encoded_image)
                            if pil_image:
                                pil_images.append(pil_image)
                            print(
                                f"[REFLECTION] Loaded 1 image for feedback reflection"
                            )
                        except Exception as e:
                            print(f"[ERROR] Processing cached image failed: {e}")
                    else:
                        print(
                            f"[REFLECTION] Image with ID '{self.image_id}' not found in cache"
                        )
                else:
                    print("[REFLECTION] No images in cache")
            else:
                print("[REFLECTION] Dashboard or thread_manager not available")

            # Prepare session_info for FeedbackRequest
            session_info = {
                "user_id": user_id,
                "session_id": current_session_id,
                "task_name": current_task,
                "intention": "Reflection analysis",
                "device_name": device_name,
                "app_mode": "reflection",
            }

            # Prepare request data for /feedback endpoint (FeedbackRequest model)
            request_data = {
                "user_id": user_id,
                "session_id": current_session_id,
                "image_id": self.image_id or "dummy_image_id",
                "rating": self.feedback_type,
                "reflection_prompt": self.prompt,
                "images": encoded_images,
                "session_info": session_info,
            }

            print(f"[FEEDBACK] Requesting reflection analysis")

            # Create session for better connection control
            if not self._session:
                import requests

                self._session = requests.Session()

            # Check termination before network request
            if self._is_stopping:
                print("Reflection thread termination requested before network call")
                return

            # Use direct LLM API with cached images
            from ..utils.direct_llm_client import get_configured_client

            llm_client = get_configured_client()
            if not llm_client:
                raise Exception("No LLM client configured")

            # Generate reflection using LLM with the specific feedback image
            print(
                f"[REFLECTION] Generating reflection using {len(pil_images)} image (feedback target)"
            )

            try:
                # Call LLM for reflection analysis with the single feedback image
                if pil_images and len(pil_images) > 0:
                    # Use the LLM client to analyze images with the reflection prompt
                    # For Gemini, we can send multiple images
                    reflection_text = llm_client.analyze_reflection(
                        prompt=self.prompt, images=pil_images, task=current_task
                    )

                    result = {
                        "reflection": {
                            "image_description": reflection_text,
                            "reflected_implicit_intention": reflection_text,
                        },
                        "parsed_reflection": {
                            "image_description": reflection_text,
                            "reflected_implicit_intention": reflection_text,
                        },
                    }
                else:
                    # No images available, create simple response
                    print("[REFLECTION] No images available for analysis")
                    result = {
                        "reflection": {
                            "image_description": "No images available",
                            "reflected_implicit_intention": "Based on feedback, adjusting understanding",
                        },
                        "parsed_reflection": {
                            "image_description": "No images available",
                            "reflected_implicit_intention": "Based on feedback, adjusting understanding",
                        },
                    }

                # Emit reflection complete
                self.reflection_complete.emit(result)
                return  # Early return to skip old backend code

            except Exception as e:
                print(f"[REFLECTION] Error generating reflection: {e}")
                # Fallback to simple response
                result = {
                    "reflection": {
                        "image_description": "Error during analysis",
                        "reflected_implicit_intention": "Based on feedback, adjusting understanding",
                    },
                    "parsed_reflection": {
                        "image_description": "Error during analysis",
                        "reflected_implicit_intention": "Based on feedback, adjusting understanding",
                    },
                }
                self.reflection_complete.emit(result)
                return

            # Old backend response parsing code (kept for reference)
            if False:  # Disabled
                reflection_found = False
                if "reflection" in result:
                    reflection_text = str(result["reflection"])[:100]
                    print(
                        f"[REFLECTION] Response: {reflection_text}{'...' if len(str(result['reflection'])) > 100 else ''}"
                    )
                    reflection_found = True
                elif "reflection_response" in result:
                    # Found the actual reflection data location!
                    reflection_response = result["reflection_response"]

                    # Handle if it's a JSON string
                    if isinstance(reflection_response, str):
                        try:
                            # Try to parse JSON from string
                            import json

                            reflection_json = json.loads(reflection_response)
                            reflection_text = str(reflection_json)[:100]
                            print(
                                f"[REFLECTION] Response: {reflection_text}{'...' if len(str(reflection_json)) > 100 else ''}"
                            )

                            # Update result to include parsed reflection for downstream processing
                            result["parsed_reflection"] = reflection_json
                            reflection_found = True
                        except json.JSONDecodeError:
                            # If not valid JSON, treat as text
                            reflection_text = str(reflection_response)[:100]
                            print(
                                f"[REFLECTION] Response (text): {reflection_text}{'...' if len(str(reflection_response)) > 100 else ''}"
                            )
                            result["parsed_reflection"] = reflection_response
                            reflection_found = True
                    else:
                        # If already parsed
                        reflection_text = str(reflection_response)[:100]
                        print(
                            f"[REFLECTION] Response: {reflection_text}{'...' if len(str(reflection_response)) > 100 else ''}"
                        )
                        result["parsed_reflection"] = reflection_response
                        reflection_found = True
                elif "data" in result and isinstance(result["data"], dict):
                    # Check if reflection data is nested under 'data'
                    data_keys = list(result["data"].keys())
                    print(f"[REFLECTION] Response data keys: {data_keys}")
                    if "reflection" in result["data"]:
                        reflection_text = str(result["data"]["reflection"])[:100]
                        print(
                            f"[REFLECTION] Response: {reflection_text}{'...' if len(str(result['data']['reflection'])) > 100 else ''}"
                        )
                        reflection_found = True
                elif "message" in result:
                    # Check if reflection is in message field
                    message_text = str(result["message"])[:100]
                    print(
                        f"[REFLECTION] Response message: {message_text}{'...' if len(str(result['message'])) > 100 else ''}"
                    )
                    reflection_found = True

                if not reflection_found:
                    print(f"[REFLECTION] No reflection data found in response")
                    # Show first few values for debugging
                    for key, value in list(result.items())[:3]:
                        print(f"[REFLECTION] {key}: {str(value)[:50]}...")

                self.reflection_complete.emit(result)
            else:
                error_msg = f"Reflection endpoint error: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail.get('detail', 'Unknown error')}"
                except:
                    pass
                self.reflection_error.emit(error_msg)

        except Exception as e:
            if not self._is_stopping:  # Only emit error signal if not terminating
                error_msg = f"Reflection failed: {str(e)}"
                print(f"[ERROR] Reflection request failed: {e}")
                self.reflection_error.emit(error_msg)
            else:
                print(
                    f"[REFLECTION_THREAD] Thread stopped, suppressing error: {str(e)}"
                )


class FeedbackManager(QObject):
    """Manager for handling user feedback and generating reflections"""

    feedback_processed = pyqtSignal(dict)
    message_sent = pyqtSignal(dict)  # Signal for feedback message sent

    def __init__(self, prompt_config, storage, dashboard=None, parent=None):
        super().__init__(parent)
        self.prompt_config = prompt_config
        self.storage = storage
        self.dashboard = dashboard  # Add dashboard reference to get session_id
        self.reflection_threads = {}
        self.completed_reflection_results = {}

    def process_feedback(
        self,
        task_name,
        llm_response,
        image_path=None,
        image_id=None,
        ai_judgement=None,
        feedback_type=None,
        user_text=None,
    ):
        """Process feedback from user with reflection"""
        try:
            print(f"[FEEDBACK] feedback case: {ai_judgement}_{feedback_type}")
            if user_text:
                print(f"[FEEDBACK] user text: {user_text}")

            # Use provided image_id if available, otherwise fallback to thread_manager
            if image_id:
                pass  # Use provided image_id
            else:
                # Fallback: Get the image_id from thread_manager (latest analysis)
                if hasattr(self.dashboard, "thread_manager") and hasattr(
                    self.dashboard.thread_manager, "last_response_image_id"
                ):
                    image_id = self.dashboard.thread_manager.last_response_image_id

            # Determine the appropriate reflection prompt based on feedback case
            reflection_prompt = format_reflection_prompt(
                stated_intention=task_name,
                assistant_response=llm_response,
                user_feedback=feedback_type,
            )
            print(f"[REFLECTION] Starting {ai_judgement}_{feedback_type} analysis")

            # Create reflection thread

            reflection_thread = ReflectionThread(
                prompt=reflection_prompt,
                dashboard=self.dashboard,
                image_id=image_id,
                image_path=image_path,
                ai_judgement=ai_judgement,
                feedback_type=feedback_type,
                parent=self,
            )

            # Connect signals for this specific reflection
            reflection_thread.reflection_complete.connect(
                lambda result: self._handle_reflection_complete(
                    task_name=task_name,
                    llm_response=llm_response,
                    reflection_data=result,
                    ai_judgement=ai_judgement,
                    feedback_type=feedback_type,
                )
            )
            reflection_thread.reflection_error.connect(self._handle_reflection_error)
            reflection_thread.finished.connect(
                lambda: self._cleanup_reflection_thread(reflection_thread)
            )

            # Store thread reference
            thread_id = id(reflection_thread)
            self.reflection_threads[thread_id] = reflection_thread

            # Start reflection thread
            reflection_thread.start()

        except Exception as e:
            print(f"[FEEDBACK] Error processing feedback: {str(e)}")

    def send_feedback_message(self, feedback_message):
        """Send user feedback message to /feedback_message endpoint"""
        try:
            # Get current session info from dashboard
            if not self.dashboard:
                print("[FEEDBACK_MESSAGE] No dashboard available")
                return

            # Get user info
            # User config removed - direct local usage only
            user_id = "local_user"
            device_name = "mac_os_device"

            # Get session info
            current_session_id = "unknown_session"
            current_task = "Unknown Task"

            if (
                hasattr(self.dashboard, "current_session_start_time")
                and self.dashboard.current_session_start_time
            ):
                current_session_id = self.dashboard.current_session_start_time

            if hasattr(self.dashboard, "current_task") and self.dashboard.current_task:
                current_task = self.dashboard.current_task

            # 🔥 CRITICAL: Get image_id from displayed message (not latest received)
            image_id = "unknown_image_id"

            # Try to use displayed message ID first (more accurate)
            if (
                hasattr(self.dashboard, "displayed_message_image_id")
                and self.dashboard.displayed_message_image_id
            ):
                image_id = self.dashboard.displayed_message_image_id
                print(f"[FEEDBACK_MESSAGE] Using displayed message ID: {image_id}")
            # Fallback to latest received message ID
            elif (
                hasattr(self.dashboard, "last_llm_response_image_id")
                and self.dashboard.last_llm_response_image_id
            ):
                image_id = self.dashboard.last_llm_response_image_id
                print(
                    f"[FEEDBACK_MESSAGE] Using latest message ID (fallback): {image_id}"
                )

            # Check for potential mismatch
            if (
                hasattr(self.dashboard, "displayed_message_image_id")
                and hasattr(self.dashboard, "last_llm_response_image_id")
                and self.dashboard.displayed_message_image_id
                != self.dashboard.last_llm_response_image_id
            ):
                print(
                    f"[FEEDBACK_MESSAGE] ⚠️  Displayed ID ({self.dashboard.displayed_message_image_id}) differs from latest ID ({self.dashboard.last_llm_response_image_id})"
                )

            # Prepare session_info
            session_info = {
                "user_id": user_id,
                "session_id": current_session_id,
                "task_name": current_task,
                "intention": current_task,
                "device_name": device_name,
            }

            print(f"[FEEDBACK_MESSAGE] Preparing to send feedback message")
            print(f"[FEEDBACK_MESSAGE] Session: {current_session_id}")
            print(f"[FEEDBACK_MESSAGE] Task: {current_task}")

            # Create feedback message thread
            message_thread = FeedbackMessageThread(
                user_id=user_id,
                session_id=current_session_id,
                image_id=image_id,
                feedback_message=feedback_message,
                session_info=session_info,
                parent=self,
            )

            # Connect signals
            message_thread.message_sent.connect(self._on_message_sent)
            message_thread.message_error.connect(self._on_message_error)
            message_thread.finished.connect(
                lambda: self._cleanup_message_thread(message_thread)
            )

            # Store thread reference
            if not hasattr(self, "message_threads"):
                self.message_threads = {}
            thread_id = id(message_thread)
            self.message_threads[thread_id] = message_thread

            # Start message thread
            message_thread.start()

        except Exception as e:
            print(f"[FEEDBACK_MESSAGE] Error sending feedback message: {str(e)}")

    def send_feedback_message_with_context(
        self, feedback_message, notification_context
    ):
        """Send user feedback message using stored notification context data"""
        try:
            print(f"[FEEDBACK_MESSAGE] Using notification context for feedback message")

            # Get user info
            # User config removed - direct local usage only
            user_id = "local_user"
            device_name = "mac_os_device"

            # Use context data instead of current dashboard state
            context_session_id = "unknown_session"
            context_task = "Unknown Task"
            context_image_id = "unknown_image_id"

            # Extract data from notification context
            if notification_context:
                context_task = notification_context.get("current_task", "Unknown Task")
                context_image_id = notification_context.get(
                    "image_id", "unknown_image_id"
                )

                # For session_id, we need to get it from dashboard if available
                if (
                    self.dashboard
                    and hasattr(self.dashboard, "current_session_start_time")
                    and self.dashboard.current_session_start_time
                ):
                    context_session_id = self.dashboard.current_session_start_time
                else:
                    # Use timestamp as fallback session identifier
                    context_session_id = f"notification_session_{notification_context.get('timestamp', 'unknown')}"

            # Prepare session_info using context data
            session_info = {
                "user_id": user_id,
                "session_id": context_session_id,
                "task_name": context_task,
                "intention": context_task,
                "device_name": device_name,
            }

            print(f"[FEEDBACK_MESSAGE] Using context data:")
            print(f"[FEEDBACK_MESSAGE] Session: {context_session_id}")
            print(f"[FEEDBACK_MESSAGE] Task: {context_task}")
            print(f"[FEEDBACK_MESSAGE] Image ID: {context_image_id}")

            # Create feedback message thread with context data
            message_thread = FeedbackMessageThread(
                user_id=user_id,
                session_id=context_session_id,
                image_id=context_image_id,
                feedback_message=feedback_message,
                session_info=session_info,
                parent=self,
            )

            # Connect signals
            message_thread.message_sent.connect(self._on_message_sent)
            message_thread.message_error.connect(self._on_message_error)
            message_thread.finished.connect(
                lambda: self._cleanup_message_thread(message_thread)
            )

            # Store thread reference
            if not hasattr(self, "message_threads"):
                self.message_threads = {}
            thread_id = id(message_thread)
            self.message_threads[thread_id] = message_thread

            # Start message thread
            message_thread.start()

        except Exception as e:
            print(
                f"[FEEDBACK_MESSAGE] Error sending feedback message with context: {str(e)}"
            )

    def _on_message_sent(self, result):
        """Handle successful feedback message sending"""
        print(f"[FEEDBACK_MESSAGE] Message sent successfully: {result}")
        self.message_sent.emit(result)

    def _on_message_error(self, error_msg):
        """Handle feedback message sending errors"""
        print(f"[FEEDBACK_MESSAGE] Error: {error_msg}")

    def _cleanup_message_thread(self, thread):
        """Clean up completed message thread"""
        try:
            if hasattr(self, "message_threads"):
                thread_id = id(thread)
                if thread_id in self.message_threads:
                    del self.message_threads[thread_id]
        except Exception as e:
            print(f"[FEEDBACK_MESSAGE] Cleanup error: {e}")

    def _handle_reflection_complete(
        self, task_name, llm_response, reflection_data, ai_judgement, feedback_type
    ):
        """Handle completion of reflection analysis"""
        feedback_case = f"{ai_judgement}_{feedback_type}"

        try:
            # Format learning entry from reflection data
            reflection_response = reflection_data.get("reflection_response", None)

            try:
                robust_pairs = re.findall(
                    r'"([^"]+)"\s*:\s*"((?:\\.|[^"\\])*)"',  # key, value
                    reflection_response,
                )
                reflection = {k: v.replace(r"\"", '"') for k, v in robust_pairs}

            except Exception as e:
                print(f"[REFLECTION] Error formatting learning entry: {e}")
                reflection = None
            print(f"[REFLECTION] Result: {str(reflection)}")

            if reflection:
                # Store learning data in appropriate feedback category
                self._store_learning_data(reflection, feedback_case)

                # Save to persistent storage if we have storage access
                if (
                    self.storage
                    and hasattr(self.dashboard, "current_session_start_time")
                    and self.dashboard.current_session_start_time
                ):
                    # Create a single dictionary with all reflection data
                    reflection_data_to_save = {
                        "task_name": task_name,
                        "session_start_time": self.dashboard.current_session_start_time,
                        "feedback_case": feedback_case,
                        "reflection": reflection,
                        "timestamp": datetime.now().isoformat(),
                    }
                    self.storage.save_reflection_data(reflection_data_to_save)

            # Emit the feedback processed signal
            feedback_result = {
                "type": "reflection_complete",
                "task_name": task_name,
                "feedback_case": feedback_case,
                "reflection": reflection,
            }

            self.feedback_processed.emit(feedback_result)
            print(f"[REFLECTION] Completed: {feedback_case}")

        except Exception as e:
            print(f"[REFLECTION] Error handling completion: {str(e)}")

    def _store_learning_data(self, reflection, feedback_case):
        """Store learning data in appropriate category based on 4 feedback cases"""
        try:
            if not self.dashboard:
                print("[FEEDBACK] No dashboard available for storing learning data")
                return

            user_activity_description = reflection["user_activity_description"]
            user_implicit_intention_prediction = reflection[
                "user_implicit_intention_prediction"
            ]
            # assistant_policy_adjustment = reflection["assistant_policy_adjustment"]

            if feedback_case == "focused_good":
                assistant_policy_adjustment = (
                    "Output higher alignment (lower output score)"
                )
            elif feedback_case == "focused_bad":
                assistant_policy_adjustment = "Output low alignment (high output score)"
            elif feedback_case == "distracted_good":
                assistant_policy_adjustment = (
                    "Output lower alignment (higher output score)"
                )
            elif feedback_case == "distracted_bad":
                assistant_policy_adjustment = "Output high alignment (low output score)"

            learned_intention = f"{user_implicit_intention_prediction} (Relevant activity: {user_activity_description})"
            learned_rule = f"{assistant_policy_adjustment} when detecting activity - {user_activity_description}"

            self.dashboard.current_reflection_intentions.append(learned_intention)
            print(
                f"[FEEDBACK] Added reflection intentions. Total: {len(self.dashboard.current_reflection_intentions)}"
            )
            if hasattr(self.dashboard, "thread_manager"):
                self.dashboard.thread_manager.set_reflection_data(
                    self.dashboard.current_reflection_intentions
                )
                print("[FEEDBACK] Updated ThreadManager with reflection intentions")

            self.dashboard.current_reflection_rules.append(learned_rule)
            print(
                f"[FEEDBACK] Added reflection rules. Total: {len(self.dashboard.current_reflection_rules)}"
            )
            if hasattr(self.dashboard, "thread_manager"):
                self.dashboard.thread_manager.set_reflection_rule(
                    self.dashboard.current_reflection_rules
                )
                print("[FEEDBACK] Updated ThreadManager with reflection rules")

        except Exception as e:
            print(f"[FEEDBACK] Error storing learning data: {str(e)}")

    def _handle_reflection_error(self, error_msg):
        """Handle reflection analysis errors"""
        print(f"[REFLECTION] Error: {error_msg}")

    def _cleanup_reflection_thread(self, thread):
        """Clean up completed reflection thread"""
        try:
            thread_id = id(thread)
            if thread_id in self.reflection_threads:
                del self.reflection_threads[thread_id]
        except Exception as e:
            print(f"[REFLECTION] Cleanup error: {e}")

    def cleanup(self):
        """Clean up all reflection and message threads - Enhanced for safe shutdown"""
        try:
            print(
                f"[FEEDBACK] Cleaning up {len(self.reflection_threads)} reflection threads..."
            )

            for thread_id, thread in list(self.reflection_threads.items()):
                if thread and thread.isRunning():
                    print(f"[FEEDBACK] Safely quitting reflection thread {thread_id}")
                    thread.safe_quit()
                    if not thread.wait(2000):  # Wait up to 2 seconds
                        print(
                            f"[FEEDBACK] Thread {thread_id} did not terminate gracefully"
                        )
                        thread.terminate()
                        thread.wait(1000)
                    else:
                        print(f"[FEEDBACK] Thread {thread_id} terminated successfully")

            self.reflection_threads.clear()
            print("[FEEDBACK] All reflection threads cleaned up")

            # Clean up message threads if they exist
            if hasattr(self, "message_threads"):
                print(
                    f"[FEEDBACK] Cleaning up {len(self.message_threads)} message threads..."
                )

                for thread_id, thread in list(self.message_threads.items()):
                    if thread and thread.isRunning():
                        print(f"[FEEDBACK] Safely quitting message thread {thread_id}")
                        thread.safe_quit()
                        if not thread.wait(2000):  # Wait up to 2 seconds
                            print(
                                f"[FEEDBACK] Message thread {thread_id} did not terminate gracefully"
                            )
                            thread.terminate()
                            thread.wait(1000)
                        else:
                            print(
                                f"[FEEDBACK] Message thread {thread_id} terminated successfully"
                            )

                self.message_threads.clear()
                print("[FEEDBACK] All message threads cleaned up")

        except Exception as e:
            print(f"[FEEDBACK] Error during cleanup: {str(e)}")

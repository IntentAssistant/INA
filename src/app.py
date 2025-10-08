import os
import sys
import rumps
import logging
import time
import regex as re

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication, QDialog

from .ui.dialogs import Dialogs
from .ui.dashboard import Dashboard
from .ui.notification import NotificationManager

from .config.constants import *
from .config.prompt_config import PromptConfig

from .manager import ThreadManager

from .logging.storage import LocalStorage

from .utils.launch_at_login import ensure_login_item
from .config.api_config import get_api_config_manager, API_CONFIG

# Hide IMK related logs
logging.getLogger().setLevel(logging.ERROR)
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"


class IntentionalComputingApp(rumps.App):
    def __init__(self):
        # Print app version and config info
        print(f"\n=== Intentional Computing v{APP_VERSION} ===")
        print(f"Config directory: {CONFIG_DIR}")
        print(f"Storage directory: {DEFAULT_STORAGE_DIR}")

        # Initialize rumps app with minimal visibility
        super().__init__(
            "INA", icon=None, quit_button=None
        )  # Empty name to hide from menu bar

        # Initialize storage (no user config needed - local only)
        self.storage = LocalStorage()

        # Initialize notification system
        self.notifications = NotificationManager()

        # Initialize dashboard
        self.dashboard = None

        # Initialize manager
        self.manager = None

        # Initialize notification context storage
        self.notification_context = {}

        # Add notification flag for next LLM analysis
        self.next_analysis_has_notification = False

        # Initialize state tracking variables
        self.reset_state_tracking()

        # Initialize timers
        self.capture_timer = QTimer()
        self.llm_timer = QTimer()

        # Connect timer signals
        self.capture_timer.timeout.connect(self.do_capture)
        self.llm_timer.timeout.connect(self.invoke_llm)

        # Initialize other variables
        self.current_message = None
        self.last_server_message = None

        # Initialize icons first
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        self.default_icon = os.path.join(assets_dir, "icon.png")
        # Recording icon removed - not needed

        # Initialize PyQt application FIRST
        self.qt_app = QApplication.instance()
        if self.qt_app is None:
            self.qt_app = QApplication(sys.argv)

        # Connect aboutToQuit signal for safe thread cleanup
        self.qt_app.aboutToQuit.connect(self._safe_shutdown)

        # Set up display change monitoring AFTER QApplication is ready
        print("[INIT] Setting up display monitoring...")
        print(f"[INIT] QApplication instance: {self.qt_app}")
        print(f"[INIT] Initial screen count: {len(self.qt_app.screens())}")

        # Connect screen change signals
        self.qt_app.screenAdded.connect(self._on_screen_added)
        self.qt_app.screenRemoved.connect(self._on_screen_removed)
        print("[INIT] Display monitoring signals connected")

        # Check initial setup
        self.check_initial_setup()

        # Check API configuration
        self.check_api_configuration()

        # Check display count after QApplication is ready
        self._check_display_count()
        self.prompt_config = PromptConfig(self.storage)  # Pass storage to prompt_config

        # Load display selection from settings
        api_manager = get_api_config_manager()
        selected_display = api_manager.get_selected_display()
        print(f"[APP] Loaded display selection from settings: {selected_display}")

        # Create ThreadManager first
        self.manager = ThreadManager(
            self.storage,
            self.prompt_config,
            None,  # Dashboard will be set later
            selected_display=selected_display,
        )

        # Now create Dashboard with required arguments
        self.dashboard = Dashboard(self.manager, self.storage)

        # Set dashboard reference in manager
        self.manager.dashboard = self.dashboard

        # Show dashboard
        self.dashboard.show()

        # Store notification context for feedback
        self.notification_context = {}

        self.reset_state_tracking()
        self.check_initial_setup()

        # Connect dashboard signals
        self.dashboard.capture_started.connect(self._handle_capture_start)
        self.dashboard.capture_stopped.connect(self._handle_capture_stop)
        # play_sound_requested signal removed - sound functionality disabled

        # Show startup notification
        Dialogs.show_notification(
            f"IntentionalComputing v{APP_VERSION}",
            "App started",
            APP_START_MESSAGE,
        )

        # Run a test capture at startup to request screen capture permissions
        try:
            print("[INIT] Requesting screen capture permissions...")
            # Execute after 1 second (when UI is fully loaded)
            QTimer.singleShot(1000, self._perform_test_capture)
        except Exception as e:
            print(f"[ERROR] Failed to setup initial capture: {e}")

        # Setup auto-login after app is fully initialized
        QTimer.singleShot(2000, self._setup_auto_login)

    def _perform_test_capture(self):
        """Performs a test screen capture to request permissions when app starts"""
        try:
            from PyQt6.QtWidgets import QApplication

            # Capture from the main display (result won't be saved)
            screens = QApplication.screens()
            if screens:
                screen = screens[0]  # Use main screen
                screenshot = screen.grabWindow(0)
                print("[INIT] Screen capture permissions granted")

                # Delete capture result immediately (only used in memory)
                del screenshot

                # Run garbage collection
                import gc

                gc.collect()
            else:
                print("[ERROR] No screens available for test capture")
        except Exception as e:
            print(f"[ERROR] Test capture failed: {e}")

    def _check_display_count(self):
        """Check displays and automatically select the primary one"""
        try:
            screens = QApplication.screens()
            display_count = len(screens)

            # Always use the first display (primary)
            if display_count >= 1:
                screen = screens[0]
                geometry = screen.geometry()
                name = screen.name() or "Primary Display"
                resolution = f"{geometry.width()}x{geometry.height()}"

                print(f"[INIT] Display count: {display_count}")
                print(f"[INIT] Using primary display: {name} ({resolution})")

                # Always use first display
                # Only set manager's selected_display if manager exists
                if hasattr(self, "manager") and self.manager is not None:
                    self.manager.selected_display = 0
                    print("[INIT] Manager display setting updated")
                else:
                    print(
                        "[INIT] Manager not yet initialized, display setting saved to config"
                    )

                # Show all connected displays for info
                if display_count > 1:
                    print(f"[INIT] Multiple displays detected ({display_count}):")
                    for i, scr in enumerate(screens):
                        geo = scr.geometry()
                        nm = scr.name() or f"Display {i+1}"
                        res = f"{geo.width()}x{geo.height()}"
                        print(f"[INIT]   {i}: {nm} ({res})")

        except Exception as e:
            print(f"[ERROR] Display check failed: {e}")
            import traceback

            print(f"[ERROR] Traceback: {traceback.format_exc()}")

    def _on_screen_added(self, screen):
        """Handle when a new screen is connected during runtime"""
        print(f"[DISPLAY] ===== SCREEN ADDED =====")
        print(f"[DISPLAY] Screen added: {screen.name()}")
        print(f"[DISPLAY] Current screen count: {len(QApplication.screens())}")
        print(f"[DISPLAY] Calling _check_display_count_runtime")
        self._check_display_count_runtime("added")
        print(f"[DISPLAY] ===== SCREEN ADDED END =====")

    def _on_screen_removed(self, screen):
        """Handle when a screen is disconnected during runtime"""
        print(f"Screen removed: {screen.name()}")
        # We don't need to check when displays are removed, only when added
        # But let's log the current count for debugging
        screens = QApplication.screens()
        print(f"Remaining displays after removal: {len(screens)}")

    def _check_display_count_runtime(self, change_type):
        """Check display count during runtime - now just logs info"""
        try:
            screens = QApplication.screens()
            display_count = len(screens)

            print(
                f"[DISPLAY] Display {change_type}: Now {display_count} display(s) connected"
            )

            # Just log the displays, don't exit
            if display_count > 1:
                print(f"[DISPLAY] Multiple displays detected ({display_count}):")
                for i, screen in enumerate(screens):
                    geometry = screen.geometry()
                    name = screen.name() or f"Display {i+1}"
                    resolution = f"{geometry.width()}x{geometry.height()}"
                    print(f"[DISPLAY]   {i}: {name} ({resolution})")
                print(f"[DISPLAY] Continuing to use primary display (index 0)")

        except Exception as e:
            print(f"[ERROR] Error checking display count during runtime: {e}")
            import traceback

            print(traceback.format_exc())

    def _force_quit_app(self):
        """Force quit the application"""
        print("Force quitting application...")
        QApplication.quit()
        sys.exit(1)

    def _handle_capture_start(self):
        """Handle capture start event"""
        print("\n=== Handling Capture Start ===")
        self.reset_state_tracking()

        # Start auto capture
        self.manager.start(self.do_capture, self.update_intention_status)

        print("=== Capture Start Handling Complete ===\n")

    def _handle_capture_stop(self):
        """Handle capture stop event"""
        print("\n=== Handling Capture Stop ===")

        # Stop auto capture
        self.manager.stop()

        print("=== Capture Stop Handling Complete ===\n")

    def reset_state_tracking(self):
        """Reset all state tracking variables"""
        self.message_update_flag = 0
        self.consecutive_focus_count = 0
        self.focus_notification_threshold = 15
        self.acquire_threshold = 2  # Need 2 consecutive to change to distracted
        self.release_threshold = 2  # Need 2 consecutive to change to focused
        self.current_state = 0
        self.consecutive_ones = 0
        self.consecutive_zeros = 0
        self.current_message = None
        self.last_server_message = None

    def check_initial_setup(self):
        """Check if initial setup is completed"""
        try:
            # Ensure storage directories exist
            self.storage.setup_storage_directory()

            # User configuration no longer needed - direct local usage only
            print("[INIT] Running in local mode - no user configuration needed")
            return True

        except Exception as e:
            print(f"[ERROR] Initial setup check failed: {e}")
            return False

    def check_api_configuration(self):
        """Check if API is properly configured and show guidance if needed"""
        try:
            api_manager = get_api_config_manager()
            configured_providers = api_manager.get_configured_providers()

            if not configured_providers:
                print("[INIT] No API providers configured")

                # Show API setup guidance dialog after a short delay
                QTimer.singleShot(3000, self._show_api_setup_guidance)
            else:
                active_provider = api_manager.get_provider()
                provider_names = [
                    API_CONFIG[p.value]["display_name"] for p in configured_providers
                ]
                active_name = API_CONFIG[active_provider.value]["display_name"]

                print(
                    f"[INIT] API configured - Active: {active_name}, Available: {', '.join(provider_names)}"
                )

        except Exception as e:
            print(f"[ERROR] API configuration check failed: {e}")

    def _show_api_setup_guidance(self):
        """Show API setup guidance dialog"""
        try:
            from .ui.api_settings_dialog import APISettingsDialog
            from .ui.dialogs import Dialogs

            # Show information dialog first
            from PyQt6.QtWidgets import QMessageBox

            msg = QMessageBox()
            msg.setWindowTitle("API Configuration Required - INA")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("Welcome to INA (Intent Assistant)!")
            msg.setInformativeText(
                "To use INA, you need to configure an AI model provider (OpenAI GPT or Google Gemini).\n\n"
                "Please go to Settings > Models to enter your API key."
            )

            # Add buttons
            configure_btn = msg.addButton(
                "Configure Now", QMessageBox.ButtonRole.AcceptRole
            )
            later_btn = msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)
            msg.setDefaultButton(configure_btn)

            # Style the message box
            msg.setStyleSheet(
                """
                QMessageBox {
                    background-color: #2c2c2c;
                    color: white;
                    border-radius: 12px;
                    border: 1px solid #404040;
                    padding: 20px;
                }
                QMessageBox QLabel {
                    color: white;
                    font-size: 14px;
                    padding: 10px;
                }
                QMessageBox QPushButton {
                    background-color: #3c3c3c;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 8px 20px;
                    font-size: 14px;
                    min-width: 80px;
                    margin: 10px 5px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #4c4c4c;
                }
                QPushButton[text="Configure Now"] {
                    background-color: #2ecc71;
                }
                QPushButton[text="Configure Now"]:hover {
                    background-color: #27ae60;
                }
            """
            )

            # Keep window frame for dragging capability
            msg.setWindowFlags(
                Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
            )

            result = msg.exec()

            if msg.clickedButton() == configure_btn:
                # Open API settings dialog
                dialog = APISettingsDialog()
                dialog.exec()
            else:
                # Show reminder about functionality
                Dialogs.show_notification(
                    "API Configuration",
                    "Setup Reminder",
                    "You can configure API settings anytime from Settings > User Settings > Configure API Settings",
                )

        except Exception as e:
            print(f"[ERROR] Failed to show API setup guidance: {e}")

    def do_capture(self):
        """Execute capture"""
        self.manager.do_activity_capture()

    @rumps.clicked("Settings", "API Settings")
    def show_api_settings(self, _):
        """Handle API settings menu click"""
        from .ui.unified_settings_dialog import UnifiedSettingsDialog

        dialog = UnifiedSettingsDialog(app=self)
        dialog.exec()

    # Display Settings menu removed - single display auto-selection

    # Sound Settings menu removed - sound functionality disabled

    def update_intention_status(self, server_response):
        """Update intention status from server response"""
        try:
            # Get output value and message
            output_raw = float(server_response.get("output", 0))
            # Classify into 3 states: focused (0-0.3), uncertain (0.4-0.6), distracted (0.7-1.0)
            if output_raw < 0.4:
                output = 0  # Focused (on-task)
            elif output_raw >= 0.7:
                output = 1  # Distracted (off-task)
            else:
                output = 2  # Uncertain (no sound)
            # Use 'message' field for user display (fallback to 'reason' for debugging)
            current_message = server_response.get(
                "message", server_response.get("reason", "")
            )
            sentences = re.split(r"(?<=[.!?])\s+", current_message)
            if len(sentences) > 1:
                current_message = "\n".join(sentences)

            # Simple status log
            status = "FOCUSED" if output == 0 else "DISTRACTED"
            print(f"[{status}] Message: {current_message}")
            print(f"[DEBUG] Reason: {server_response.get('reason', 'N/A')}")

            if not current_message:
                current_message = (
                    "Focus: Stay on task!"
                    if output == 0
                    else "Distracted: Return to your goal!"
                )

            # Store server message for later use
            self.last_server_message = current_message

            # 🔥 CRITICAL: Store LLM response for feedback
            # This must happen before updating UI so feedback has correct data
            if self.dashboard and hasattr(
                self.dashboard, "store_llm_response_for_feedback"
            ):
                # Get analyzed image path from manager
                analyzed_image_path = None
                if self.manager and hasattr(self.manager, "last_analyzed_image_path"):
                    analyzed_image_path = self.manager.last_analyzed_image_path

                self.dashboard.store_llm_response_for_feedback(
                    llm_response=server_response,
                    analyzed_image_path=analyzed_image_path,
                )
                print(f"[FEEDBACK] Stored LLM response for potential feedback")

            # Update consecutive counters (more robust against noise)
            if output == 1:  # Distracted state
                self.consecutive_ones += 1
            elif output == 0:  # Focused state
                self.consecutive_zeros += 1
            # output == 2 (uncertain): don't update counters, maintain current state

            # Check if this is the first message
            is_first_message = self.current_message is None

            self.message_update_flag += 1

            # For the first message, set the initial state based on the first output
            if is_first_message:
                self.current_state = output

                # Start sound playback first (async)
                # if self.current_state == 0:  # Now focused state
                #     self.play_sound()
                # else:  # Now distracted state
                #     self.play_sound()

                # Then update the UI
                print(f"[UI] Update intention level on dashboard")
                self.dashboard.update_intention_level(
                    level=self.current_state,
                    message=current_message,
                    raw_value=output_raw,
                )
                self.message_update_flag = 0

                # Show notification
                notification_id = f"intention_status_{int(time.time() * 1000)}"

                # Set notification flag for next LLM analysis
                self.next_analysis_has_notification = True
                if self.manager:
                    self.manager.set_notification_flag(True)

                # Store notification context (same data as dashboard feedback uses)
                context_data = {
                    "ai_judgement": self.current_state,  # 0=focused, 1=distracted
                    "llm_response": getattr(self.dashboard, "last_llm_response", None),
                    "image_path": getattr(self.dashboard, "last_analyzed_image", None),
                    "image_id": getattr(
                        self.dashboard, "last_llm_response_image_id", None
                    ),
                    "current_task": self.dashboard.current_task,
                    "message": current_message,
                    "timestamp": time.time(),
                }
                self._store_notification_context(notification_id, context_data)

                # Show notification with feedback buttons
                self.notifications.show_notification(
                    "Notification",
                    self.dashboard.current_task,
                    current_message,
                    self.current_state,
                    on_good=lambda nid=notification_id: self._handle_notification_feedback(
                        "good", nid
                    ),
                    on_bad=lambda nid=notification_id: self._handle_notification_feedback(
                        "bad", nid
                    ),
                    dashboard=self.dashboard,
                    notification_context=context_data,
                )
                self.current_message = current_message
            else:
                # Handle state transitions for subsequent messages
                state_changed = self._handle_state_transition(output)

                # Update dashboard and show notification only on state change
                if state_changed:
                    # Start sound playback first (async)
                    # if self.current_state == 0:  # Now focused state
                    #     self.play_sound()
                    # else:  # Now distracted state
                    #     self.play_sound()

                    # Show notification
                    notification_id = f"intention_status_{int(time.time() * 1000)}"

                    # Set notification flag for next LLM analysis
                    self.next_analysis_has_notification = True
                    if self.manager:
                        self.manager.set_notification_flag(True)

                    # Store notification context (use displayed message for accurate feedback)
                    context_data = {
                        "ai_judgement": self.current_state,  # 0=focused, 1=distracted
                        "llm_response": getattr(
                            self.dashboard, "displayed_message_response", None
                        )
                        or getattr(self.dashboard, "last_llm_response", None),
                        "image_path": getattr(
                            self.dashboard, "last_analyzed_image", None
                        ),
                        "image_id": getattr(
                            self.dashboard, "displayed_message_image_id", None
                        )
                        or getattr(self.dashboard, "last_llm_response_image_id", None),
                        "current_task": self.dashboard.current_task,
                        "message": current_message,
                        "timestamp": time.time(),
                    }
                    self._store_notification_context(notification_id, context_data)

                    # Show notification with feedback buttons
                    self.notifications.show_notification(
                        "Notification",
                        self.dashboard.current_task,
                        current_message,
                        self.current_state,
                        on_good=lambda nid=notification_id: self._handle_notification_feedback(
                            "good", nid
                        ),
                        on_bad=lambda nid=notification_id: self._handle_notification_feedback(
                            "bad", nid
                        ),
                        dashboard=self.dashboard,
                        notification_context=context_data,
                    )
                    self.current_message = current_message

                    # Update message on dashboard immediately after notification
                    print(f"[UI] Update intention level on dashboard")
                    self.dashboard.update_intention_level(
                        level=self.current_state,
                        message=current_message,
                        raw_value=output_raw,
                    )
                    self.message_update_flag = 0

                # Update message periodically even without state change (every 5+ messages)
                elif self.message_update_flag > 5:
                    print(f"[UI] Update message (periodic update)")
                    self.dashboard.update_intention_level(
                        level=self.current_state,
                        message=current_message,
                        raw_value=output_raw,
                    )
                    self.message_update_flag = 0

            # Handle focus reminders
            self._handle_focus_reminders(output, current_message)

        except Exception as e:
            print(f"[ERROR] {e}")

    def _handle_state_transition(self, output):
        """Handle state transition logic"""
        # No state transition for uncertain output (2)
        if output == 2:
            return False

        # Transition to distracted state when consecutive ones reach threshold
        if self.current_state == 0 and self.consecutive_ones >= self.acquire_threshold:
            self.current_state = 1
            self.consecutive_zeros = 0  # Reset counter on state change
            print(
                f"[STATE] Changed to DISTRACTED (consecutive: {self.consecutive_ones}/{self.acquire_threshold})"
            )
            return True
        # Transition back to focused state when consecutive zeros reach threshold
        elif (
            self.current_state == 1 and self.consecutive_zeros >= self.release_threshold
        ):
            self.current_state = 0
            self.consecutive_ones = 0  # Reset counter on state change
            self.consecutive_focus_count = 1
            print(
                f"[STATE] Changed to FOCUSED (consecutive: {self.consecutive_zeros}/{self.release_threshold})"
            )
            return True
        return False

    def _handle_focus_reminders(self, output, message):
        """Handle reminder logic for distracted state"""
        # Check for distracted state reminders
        if self.current_state == 1 and output == 1:
            self.consecutive_focus_count += 1

            if self.consecutive_focus_count >= self.focus_notification_threshold:
                print(
                    f"[REMINDER] Triggered after {self.consecutive_focus_count} consecutive distracted messages"
                )

                # Ensure we have a valid message for the reminder
                reminder_message = message
                if not reminder_message or reminder_message.strip() == "":
                    reminder_message = "Still distracted! Try to refocus on your task."

                # Start sound playback first (async)
                # self.play_sound()

                # Update the UI
                current_raw_value = getattr(
                    self.dashboard, "current_raw_value", 0.5
                )  # Use existing raw value or neutral default
                self.dashboard.update_intention_level(1, message, current_raw_value)

                # Use the dashboard's current task
                task = self.dashboard.current_task
                if not task or task.strip() == "":
                    task = "your task"

                try:
                    # Show notification with task context
                    notification_id = f"intention_reminder_{int(time.time() * 1000)}"

                    # Set notification flag for next LLM analysis
                    self.next_analysis_has_notification = True
                    if self.manager:
                        self.manager.set_notification_flag(True)

                    # Store notification context (use displayed message for accurate feedback)
                    context_data = {
                        "ai_judgement": 1,  # Always distracted state for reminders
                        "llm_response": getattr(
                            self.dashboard, "displayed_message_response", None
                        )
                        or getattr(self.dashboard, "last_llm_response", None),
                        "image_path": getattr(
                            self.dashboard, "last_analyzed_image", None
                        ),
                        "image_id": getattr(
                            self.dashboard, "displayed_message_image_id", None
                        )
                        or getattr(self.dashboard, "last_llm_response_image_id", None),
                        "current_task": task,
                        "message": reminder_message,
                        "timestamp": time.time(),
                    }
                    self._store_notification_context(notification_id, context_data)

                    # Show notification with feedback buttons
                    self.notifications.show_notification(
                        "Notification",
                        task,
                        reminder_message,
                        1,  # Always distracted state for reminders
                        on_good=lambda nid=notification_id: self._handle_notification_feedback(
                            "good", nid
                        ),
                        on_bad=lambda nid=notification_id: self._handle_notification_feedback(
                            "bad", nid
                        ),
                        dashboard=self.dashboard,
                        notification_context=context_data,
                    )
                except Exception as e:
                    print(f"[ERROR] Notification failed: {e}")

                # Reset counter
                self.consecutive_focus_count = 0
                self.current_message = message

    def play_sound(self):
        """Play notification sound"""
        try:
            # Sound functionality disabled
            return

            # Get current state (0 = focused, 1 = distracted)
            if hasattr(self, "current_state") and self.current_state == 1:
                # Distracted state - use distract sound
                sound_file = sound_settings.get("distract_sound", "focus_1.mp3")
                state_text = "DISTRACTED"
            else:
                # Focused state (default) - use focus sound
                sound_file = sound_settings.get("focus_sound", "good_1.mp3")
                state_text = "FOCUSED"

            # Construct full path - fix the path issue
            sound_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "assets", sound_file
            )

            print(f"[SOUND] Playing {state_text} sound: {sound_file}")

            if os.path.exists(sound_path):
                print(f"[SOUND] Sound file found: {sound_path}")
                # Play sound in background
                threading.Thread(
                    target=self._play_sound_background, args=(sound_path,)
                ).start()
            else:
                print(f"[SOUND] Sound file not found: {sound_path}")

        except Exception as e:
            print(f"[SOUND] Error: {e}")

    def _play_sound_background(self, sound_path):
        """Play sound in background"""
        try:
            # Play sound asynchronously (no UI blocking)
            result = subprocess.run(
                ["afplay", sound_path], capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"[SOUND] Successfully played: {os.path.basename(sound_path)}")
            else:
                print(f"[SOUND] Failed to play: {result.stderr}")
        except Exception as e:
            print(f"[SOUND] Background playback error: {e}")

    def quit(self, _):
        """Quit the application"""
        print("[APP] Manual quit requested...")
        self._safe_shutdown()

    def start_auto_capture(self, capture_callback, analysis_callback):
        """Start auto capture with proper task directory setup"""
        # User config removed - direct local usage only
        if False:  # Disabled - no user validation needed
            from .ui.dialogs import Dialogs

            Dialogs.show_error(
                "Credentials Required",
                "Please enter your assigned User ID and Password in Settings > User Settings before starting.",
            )
            return False

        # Update task directory before starting capture
        if self.dashboard and self.dashboard.current_task:
            self.update_task(self.dashboard.current_task)

        # Start capture process
        self.capture_callback = capture_callback
        self.analysis_callback = analysis_callback

        print("\n=== Starting Auto Capture ===")

        # Start timers
        self.capture_timer.start(CAPTURE_INTERVAL * 1000)
        self.llm_timer.start(LLM_INVOKE_INTERVAL * 1000)
        print("Capture and LLM timers started")

        # Show recording indicator
        self.update_recording_indicator()
        return True

    # Reminder functionality removed (experimental feature)

    # _handle_dashboard_sound_request method removed - sound functionality disabled

    def _handle_notification_feedback(self, feedback_type, notification_id):
        """Handle feedback from notification buttons - connects to dashboard feedback system"""
        try:
            print(
                f"[NOTIFICATION] Feedback received: {feedback_type} for notification: {notification_id}"
            )

            # Get stored notification context
            context = self._get_notification_context(notification_id)
            if not context:
                print(
                    f"[NOTIFICATION] Error: No context found for notification {notification_id}"
                )

                return

            # Use stored context data (same as dashboard feedback logic)
            current_task = context.get("current_task", "Unknown Task")
            ai_judgement_value = context.get("ai_judgement", 1)  # Default to distracted
            ai_judgement = "focused" if ai_judgement_value == 0 else "distracted"

            print(
                f"[NOTIFICATION] Using stored AI judgment: {ai_judgement_value} ({ai_judgement})"
            )
            print(
                f"[NOTIFICATION] Context timestamp: {context.get('timestamp', 'unknown')}"
            )

            print(f"[NOTIFICATION] Processing feedback: {ai_judgement}_{feedback_type}")
            # Get the feedback manager from dashboard
            if self.dashboard and hasattr(self.dashboard, "feedback_manager"):
                feedback_manager = self.dashboard.feedback_manager

                # 🔥 CRITICAL: 버튼 클릭 시점의 dashboard 상태 사용 (메시지 피드백과 일치시키기 위해)
                button_click_image_id = getattr(
                    self.dashboard, "displayed_message_image_id", None
                ) or getattr(self.dashboard, "last_llm_response_image_id", None)
                button_click_response = getattr(
                    self.dashboard, "displayed_message_response", None
                ) or getattr(self.dashboard, "last_llm_response", None)
                button_click_image_path = getattr(
                    self.dashboard, "last_analyzed_image", None
                )

                print(f"[NOTIFICATION] Button click image ID: {button_click_image_id}")
                print(
                    f"[NOTIFICATION] vs Stored context ID: {context.get('image_id', 'None')}"
                )

                if button_click_image_id != context.get("image_id"):
                    print(
                        f"[NOTIFICATION] ⚠️  Using button click ID instead of stored context ID!"
                    )

                # Use button click data instead of stored context data
                last_llm_response = button_click_response
                last_image_path = button_click_image_path
                last_image_id = button_click_image_id

                # Debug logging for data availability
                print(f"[NOTIFICATION] Context data check:")
                print(
                    f"  - llm_response: {'Available' if last_llm_response else 'Missing'}"
                )
                print(
                    f"  - image_path: {'Available' if last_image_path else 'Missing'}"
                )
                print(f"  - image_id: {'Available' if last_image_id else 'Missing'}")

                # Process feedback using the same system as dashboard buttons
                feedback_manager.process_feedback(
                    task_name=current_task,
                    llm_response=(
                        last_llm_response
                        if last_llm_response
                        else "```json"
                        "{"
                        "   'reason': 'No response, which have been processed as output: 0.0 (aligned)'"
                        "   'output': 0.0"
                        "}"
                        "```"
                    ),
                    image_path=last_image_path,
                    ai_judgement=ai_judgement,
                    feedback_type=feedback_type,
                    image_id=last_image_id,
                )
                print(
                    f"[NOTIFICATION] Feedback processed successfully: {ai_judgement}_{feedback_type}"
                )

                # Clean up old contexts
                self._clear_old_notification_contexts()

            else:
                print(
                    "[NOTIFICATION] Error: Dashboard or feedback_manager not available"
                )

        except Exception as e:
            print(f"[NOTIFICATION] Error processing feedback: {e}")
            import traceback

            traceback.print_exc()

    def _store_notification_context(self, notification_id, context_data):
        """Store notification context data for later feedback use"""
        self.notification_context[notification_id] = context_data
        print(
            f"[NOTIFICATION] Stored context for {notification_id}: {list(context_data.keys())}"
        )

    def _get_notification_context(self, notification_id):
        """Get stored notification context data"""
        return self.notification_context.get(notification_id, {})

    def _clear_old_notification_contexts(self):
        """Clear old notification contexts to prevent memory leaks"""
        # Keep last 10 contexts for feedback support
        limit = 10

        if len(self.notification_context) > limit:
            # Remove oldest contexts
            sorted_keys = sorted(self.notification_context.keys())
            contexts_to_remove = len(self.notification_context) - limit
            for key in sorted_keys[:contexts_to_remove]:
                del self.notification_context[key]
            print(
                f"[NOTIFICATION] Cleaned up {contexts_to_remove} old contexts, kept {limit}"
            )

    def invoke_llm(self):
        """Invoke LLM analysis through manager"""
        if self.manager:
            # Pass notification flag to manager and reset it
            has_notification = self.next_analysis_has_notification
            self.next_analysis_has_notification = False

            self.manager.invoke_llm(has_notification=has_notification)

    def _setup_auto_login(self):
        """Setup auto-login after app is fully initialized"""
        try:
            app_name = "INA"
            print(f"[INIT] Setting up auto-login for: {app_name}")
            ensure_login_item(app_name)
        except Exception as e:
            print(f"[ERROR] Failed to setup auto-login: {e}")

    def _safe_shutdown(self):
        """Handle safe shutdown - Enhanced for thread safety"""
        print("[APP] Starting comprehensive safe shutdown...")

        # Set shutdown flag to prevent new threads from starting
        import threading

        shutdown_event = threading.Event()
        shutdown_event.set()

        # Clean up dashboard first (this will clean up all managers)
        if self.dashboard:
            print("[APP] Cleaning up dashboard and all managers...")
            self.dashboard.cleanup()

        # Stop manager second (redundant but safe)
        if self.manager:
            print("[APP] Stopping thread manager...")
            self.manager.stop()

        # Additional cleanup: ensure all QThread objects are properly terminated
        print("[APP] Performing final thread cleanup...")
        self._cleanup_remaining_threads()

        # Wait longer for threads to fully terminate
        from PyQt6.QtCore import QTimer
        import time

        print("[APP] Waiting for threads to complete...")
        time.sleep(1.5)  # Give threads more time to cleanup

        # Force Python GC to run multiple times with delays
        import gc

        print("[APP] Running garbage collection...")
        for i in range(3):
            before_gc = len(gc.get_objects())
            gc.collect()
            after_gc = len(gc.get_objects())
            print(
                f"[APP] GC round {i+1}: {before_gc} -> {after_gc} objects ({before_gc - after_gc} freed)"
            )
            time.sleep(0.2)

        # 🔥 CRITICAL: Final memory usage report for debugging
        import threading

        final_thread_count = threading.active_count()
        final_object_count = len(gc.get_objects())
        print(f"[APP] Final memory state:")
        print(f"[APP]   Active threads: {final_thread_count}")
        print(f"[APP]   Python objects: {final_object_count}")
        print(
            f"[APP]   Notification contexts: {len(getattr(self, 'notification_context', {}))}"
        )

        print("[APP] Safe shutdown complete, quitting Qt application...")

        # Final check for any remaining threads before quitting
        remaining_threads = threading.active_count()
        if remaining_threads > 1:  # Main thread is always counted
            print(f"[APP] Warning: {remaining_threads - 1} threads still active")

        self.qt_app.quit()
        rumps.quit_application()

    def _cleanup_remaining_threads(self):
        """Final cleanup for any remaining QThread objects"""
        try:
            from PyQt6.QtCore import QThread
            import gc

            # Force garbage collection to find all objects
            gc.collect()

            # Find all QThread objects
            thread_objects = []
            for obj in gc.get_objects():
                if isinstance(obj, QThread) and obj.isRunning():
                    thread_objects.append(obj)

            if thread_objects:
                print(
                    f"[APP] Found {len(thread_objects)} running QThread objects, cleaning up..."
                )

                for thread in thread_objects:
                    try:
                        thread_name = getattr(thread, "objectName", lambda: "Unknown")()
                        print(f"[APP] Cleaning up thread: {thread_name}")

                        # Try safe_quit if available
                        if hasattr(thread, "safe_quit"):
                            thread.safe_quit()
                        else:
                            # Fallback to standard cleanup
                            thread.quit()
                            if not thread.wait(2000):
                                print(
                                    f"[APP] Thread {thread_name} did not quit gracefully, terminating..."
                                )
                                thread.terminate()
                                thread.wait(2000)
                            thread.deleteLater()

                    except Exception as e:
                        print(f"[APP] Error cleaning up thread: {e}")

                print("[APP] Final thread cleanup complete")
            else:
                print("[APP] No running QThread objects found")

        except Exception as e:
            print(f"[APP] Error in final thread cleanup: {e}")

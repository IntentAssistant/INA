import io
import os
import sys
import glob
import json
import subprocess
import base64
import requests
import time
from datetime import datetime, timedelta
from PIL import Image


from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject, QBuffer, QIODevice
from PyQt6.QtWidgets import QWidget, QApplication

from .utils.activity import get_frontmost_app, get_browser_url
from .utils.indicator import IndicatorWidget
from .utils.llm_analysis import LLMAnalysisThread

from .logging.storage import LocalStorage
from .config.constants import (
    CAPTURE_INTERVAL,
    LLM_INVOKE_INTERVAL,
    LLM_ANALYSIS_IMAGE_COUNT,
    MAX_CONCURRENT_ANALYSIS_THREADS,
    DEFAULT_STORAGE_DIR,
    IMAGE_QUALITY,
)
from .utils.screen_lock_detector import ScreenLockDetector

# Screen lock detection constants
SCREEN_LOCK_CHECK_INTERVAL = 1  # Check every 1 second for screen lock (fast response)


class ThreadManager(QObject):
    def __init__(
        self,
        storage,
        prompt_config,
        dashboard,
        selected_display=0,
    ):
        super().__init__()
        self.storage = storage if isinstance(storage, LocalStorage) else LocalStorage()
        self.uploader = None  # Cloud upload removed - using direct LLM APIs
        self.prompt_config = prompt_config
        self.dashboard = dashboard
        self.__selected_display = selected_display

        # Add image cache (keep last 10 images in memory for feedback)
        from collections import deque

        self.image_cache = deque(maxlen=10)  # Auto-remove oldest when full

        # Initialize timers
        self.capture_timer = QTimer()
        self.llm_timer = QTimer()
        self.screen_lock_timer = QTimer()  # Timer for screen lock detection

        # State management
        self.is_capturing = False
        self.last_score = None
        self.analysis_callback = None

        # Screen lock detection
        self.screen_lock_detector = ScreenLockDetector()
        self.screen_lock_check_enabled = True

        # Store clarification and reflection data in memory for immediate use
        self.current_clarification_data = None
        # Learning data for feedback system (stored in memory)
        self.current_reflection_data = None
        self.current_reflection_rule = None

        # Store last response image ID for feedback
        self.last_response_image_id = None

        # Storage limit caching for performance
        self.last_storage_check_time = 0
        self.last_storage_check_result = True
        self.storage_check_interval = 300  # 5 minutes in seconds

        # Add notification flag for next LLM analysis
        self.next_analysis_has_notification = False

        # Add image number counter for each session (starts from 1)
        self.current_session_image_num = 0

        # Track previous app state for app change detection
        self.previous_app_name = None
        self.previous_app_domain = None

        # Initialize other components
        self.current_capture_thread = None
        self.analysis_threads = {}
        self.cloud_mode = False
        self.recording_indicator = None
        self.is_running = False
        self.skip_llm = False

        # Initialize screenshot data storage (in memory only)
        self.current_screenshot_data = None
        self.current_capture_metadata = {}

        # Connect timer signals
        self.capture_timer.timeout.connect(self.capture_screen)
        self.llm_timer.timeout.connect(self.do_llm_analysis)
        self.screen_lock_timer.timeout.connect(self._check_screen_lock)

    @property
    def selected_display(self):
        return self.__selected_display

    @selected_display.setter
    def selected_display(self, value):
        if self.__selected_display != value:
            self.__selected_display = value
            # Update recording indicator if it exists
            if self.recording_indicator:
                self.update_recording_indicator()

    def _handle_analysis_result(self, result):
        """Handle completed analysis result"""
        try:
            # Skip processing if ThreadManager is no longer running
            if not self.is_running:
                return

            # Check if result is an error
            output = result.get("output", 0)
            if output == "error":
                print(
                    f"[ERROR] LLM analysis failed: {result.get('reason', 'Unknown error')}"
                )
                return  # Skip processing error results

            # store llm response
            self.storage.save_llm_result(result)

            # Store image_id from backend response for feedback (silent)
            image_id = result.get("image_id", None)
            if image_id:
                self.last_response_image_id = image_id

            # Store LLM response for potential feedback (silent)
            analyzed_image_path = result.get("primary_analyzed_image", None)
            if not analyzed_image_path:
                recent_images = self._get_recent_local_images(1)
                analyzed_image_path = recent_images[0] if recent_images else None

            # Store the response and image for feedback (silent)
            if self.dashboard and hasattr(
                self.dashboard, "store_llm_response_for_feedback"
            ):
                self.dashboard.store_llm_response_for_feedback(
                    result, analyzed_image_path
                )

            # process llm response
            if self.analysis_callback:
                # Handle both numeric and string output
                try:
                    output_value = (
                        float(output)
                        if isinstance(output, (int, float, str)) and output != "error"
                        else 0
                    )
                    self.last_score = 1 if output_value > 0.6 else 0
                    self.analysis_callback(result)
                except (ValueError, TypeError):
                    print(f"[ERROR] Invalid output value: {output}")
                    return

        except Exception as e:
            print(f"[ERROR] {str(e)}")
            import traceback

            traceback.print_exc()

    def start(self, capture_callback, analysis_callback):
        """Start auto capture and analysis"""
        self.capture_callback = capture_callback
        self.analysis_callback = analysis_callback
        self.is_running = True

        # Reset image number counter for new session
        self.current_session_image_num = 0
        print(f"[SESSION] Image counter reset to 0 for new session")

        # Reset app change tracking for new session
        self.previous_app_name = None
        self.previous_app_domain = None
        print(f"[SESSION] App change tracking reset for new session")

        # LLM analysis enabled
        self.skip_llm = False
        print("[INFO] LLM analysis enabled")

        # Update task directory before starting capture
        if self.dashboard and self.dashboard.current_task:
            session_id = getattr(self.dashboard, "current_session_start_time", None)
            self.update_task(self.dashboard.current_task, session_id)

        # Start capture process
        self.capture_timer.start(CAPTURE_INTERVAL * 1000)

        # Start LLM timer for all modes (BASIC and REMINDER handle UI differently in app.py)
        self.llm_timer.start(LLM_INVOKE_INTERVAL * 1000)
        print(f"LLM timer started with interval {LLM_INVOKE_INTERVAL} seconds")

        # Start screen lock detection timer
        if self.screen_lock_check_enabled and self.screen_lock_detector.is_supported:
            self.screen_lock_timer.start(SCREEN_LOCK_CHECK_INTERVAL * 1000)
            print(
                f"[SCREEN_LOCK] Timer started with interval {SCREEN_LOCK_CHECK_INTERVAL} seconds"
            )
        else:
            print("[SCREEN_LOCK] Screen lock detection not supported on this platform")

        # Show recording indicator
        self.update_activity_capturing_indicator()

    def stop(self):
        """Stop automatic capture and analysis"""
        try:
            print("\n=== Stopping Auto Capture ===")

            # Immediately set running flag to false to prevent new analysis processing
            self.is_running = False
            print("ThreadManager is_running set to False")

            # Reset image counter when session ends
            print(
                f"[SESSION] Session ended. Total images analyzed: {self.current_session_image_num}"
            )
            self.current_session_image_num = 0

            # Stop timers first - Stop timers first to prevent new thread creation
            print("Stopping timers...")
            if self.capture_timer.isActive():
                self.capture_timer.stop()
            if self.llm_timer.isActive():
                self.llm_timer.stop()
            if self.screen_lock_timer.isActive():
                self.screen_lock_timer.stop()
                print("[SCREEN_LOCK] Timer stopped")

            # Clean up UI elements - Clean up UI elements first
            if self.recording_indicator:
                print("Removing recording indicator...")
                try:
                    self.recording_indicator.close()
                    self.recording_indicator = None
                except Exception as e:
                    print(f"Error removing recording indicator: {e}")

            # Clean up analysis threads
            print("Preparing thread cleanup...")
            thread_count = len(self.analysis_threads)
            if thread_count > 0:
                print(f"Cleaning up {thread_count} analysis threads...")
                for thread_id, thread in list(self.analysis_threads.items()):
                    try:
                        if thread and thread.isRunning():
                            print(f"Requesting thread {thread_id} to stop...")
                            # Set stopping flag if available
                            if hasattr(thread, "_is_stopping"):
                                thread._is_stopping = True

                            # Disconnect signals to prevent callbacks after cleanup
                            try:
                                thread.analysis_complete.disconnect()
                                thread.analysis_error.disconnect()
                                thread.finished.disconnect()
                            except Exception as e:
                                print(
                                    f"Error disconnecting signals for {thread_id}: {e}"
                                )

                            # Use safe_quit if available
                            if hasattr(thread, "safe_quit"):
                                thread.safe_quit()
                            else:
                                thread.terminate()

                            # Use longer timeout (2s) for proper cleanup
                            if not thread.wait(2000):
                                print(
                                    f"Thread {thread_id} did not stop in time, but continuing cleanup"
                                )
                            else:
                                print(f"Thread {thread_id} stopped successfully")

                        try:
                            thread.deleteLater()
                        except Exception as e:
                            print(f"Error deleting thread {thread_id}: {e}")
                    except Exception as e:
                        print(f"Error stopping thread {thread_id}: {e}")

                # Clear dictionary after processing all threads
                self.analysis_threads.clear()
                print("All analysis threads cleaned up")

                # Force garbage collection after thread cleanup
                import gc

                gc.collect()

            # Clean up capture thread - Finally clean up the capture thread
            if self.current_capture_thread and self.current_capture_thread.isRunning():
                print("Stopping capture thread...")
                try:
                    self.current_capture_thread.terminate()
                    # Use shorter timeout
                    if not self.current_capture_thread.wait(1000):
                        print("Capture thread did not stop in time, but continuing...")
                        # Remove redundant second terminate call
                    else:
                        print("Capture thread stopped successfully")
                except Exception as e:
                    print(f"Error stopping capture thread: {e}")

                self.current_capture_thread = None

            # Reset state and run garbage collection
            self.last_score = None

            # Run garbage collection to clean up resources
            import gc

            gc.collect()

            print("Auto capture stopped successfully")
            return True

        except Exception as e:
            print(f"Error stopping auto capture: {str(e)}")
            import traceback

            print(traceback.format_exc())
            return False

    def capture_screen(self):
        """Capture the selected display (no longer saves to disk, keeps in memory)"""
        if not self.is_running:
            return

        # Check screen lock status before capturing
        if self.screen_lock_detector.is_supported:
            is_locked = self.screen_lock_detector.is_screen_locked()
            if is_locked:
                print("[CAPTURE] Screen is locked - skipping capture")
                return

        # Only log once per session or when display changes
        if not hasattr(self, "_logged_display_info"):
            screens = QApplication.screens()
            if len(screens) == 1:
                print(f"[CAPTURE] Single display environment - using display 0")
            else:
                print(f"[CAPTURE] Using display: {self.selected_display}")
            self._logged_display_info = True

        try:
            screens = QApplication.screens()

            if len(screens) == 1:
                # Single display environment
                screen = screens[0]
                screen_name = screen.name()
                screen_geometry = screen.geometry()
                print(
                    f"Capturing from screen: {screen_name} ({screen_geometry.width()}x{screen_geometry.height()})"
                )

                # Get the screenshot
                screenshot = screen.grabWindow(0)
            else:
                # Multi-display environment
                if self.selected_display < len(screens):
                    screen = screens[self.selected_display]
                    screenshot = screen.grabWindow(0)
                else:
                    print(f"Selected display {self.selected_display} not found")
                    return

            # Convert screenshot to bytes for direct API processing
            # PyQt6 requires QBuffer instead of BytesIO
            byte_array = (
                screenshot.toImage().bits().asstring(screenshot.toImage().sizeInBytes())
            )

            # Use PIL to convert and compress
            from PIL import Image

            pil_image = Image.frombytes(
                "RGBA", (screenshot.width(), screenshot.height()), byte_array
            )

            # Convert to RGB (remove alpha channel)
            if pil_image.mode == "RGBA":
                pil_image = pil_image.convert("RGB")

            # Save to BytesIO using PIL
            buffer = io.BytesIO()
            pil_image.save(buffer, format="JPEG", quality=IMAGE_QUALITY)
            self.current_screenshot_data = buffer.getvalue()

            # Get current frontmost app name for metadata
            frontmost_app = get_frontmost_app()
            url = ""
            if frontmost_app:
                url = get_browser_url(frontmost_app)

            # Store metadata in memory (no file saving)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_capture_metadata = {
                "timestamp": timestamp,
                "frontmost_app": frontmost_app,
                "url": url,
                "image_size": len(self.current_screenshot_data),
            }

            print(
                f"[CAPTURE] Screenshot captured in memory ({len(self.current_screenshot_data)} bytes)"
            )

        except Exception as e:
            print(f"[CAPTURE] Error: {e}")

    def do_llm_analysis(self):
        """Perform LLM analysis on current screenshot (no file system access)"""
        try:
            # Don't analyze if not running
            if not self.is_running:
                return

            # Check screen lock status before analyzing
            if self.screen_lock_detector.is_supported:
                is_locked = self.screen_lock_detector.is_screen_locked()
                if is_locked:
                    print("[LLM_ANALYSIS] Screen is locked - skipping analysis")
                    return

            # Clean up completed threads more aggressively
            completed = []
            for tid, thread in list(self.analysis_threads.items()):
                if not thread.isRunning():
                    completed.append(tid)

            for tid in completed:
                if tid in self.analysis_threads:
                    thread = self.analysis_threads.pop(tid)
                    try:
                        thread.quit()
                        thread.wait(2000)
                        thread.deleteLater()
                    except Exception as e:
                        pass

            # Run garbage collection after cleanup
            import gc

            gc.collect()

            if len(self.analysis_threads) >= MAX_CONCURRENT_ANALYSIS_THREADS:
                return  # Skip if too many threads running

            # Check if we have current screenshot data
            if (
                not hasattr(self, "current_screenshot_data")
                or not self.current_screenshot_data
            ):
                print("[LLM_ANALYSIS] No current screenshot data available")
                return

            # Get current frontmost app info (real-time)
            frontmost_app = get_frontmost_app()
            url = get_browser_url(frontmost_app) if frontmost_app else ""

            # Parse app name and URL
            if " - " in frontmost_app:
                app_name = frontmost_app.split(" - ")[0]
                url = frontmost_app.split(" - ", 1)[1]
            else:
                app_name = frontmost_app
                url = url or ""

            # Detect app change
            app_changed = self._detect_app_change(app_name, url)

            # Get user info and current task (user_config removed)
            user_info = {
                "name": "local_user",
                "device_name": "mac_os_device",
                "current_task": self.dashboard.current_task,
                "notification": self.next_analysis_has_notification,
            }

            # Increment image number for this analysis
            self.current_session_image_num += 1
            user_info["image_num"] = self.current_session_image_num
            print(f"[ANALYSIS] Image #{self.current_session_image_num} being analyzed")

            # Reset notification flag after using it
            self.next_analysis_has_notification = False

            # Add frontmost app info
            frontmost_app_info = {
                "app_name": app_name,
                "url": url,
                "timestamp": self.current_capture_metadata.get("timestamp", ""),
            }
            user_info["frontmost_app"] = frontmost_app_info

            # Add app change flag
            user_info["app_change"] = app_changed

            # Add session_id from dashboard
            if self.dashboard and hasattr(self.dashboard, "current_session_start_time"):
                user_info["session_id"] = self.dashboard.current_session_start_time

            # Add opacity information from dashboard
            if self.dashboard and hasattr(self.dashboard, "current_opacity"):
                user_info["opacity"] = self.dashboard.current_opacity
                print(f"[ANALYSIS] Dashboard opacity: {self.dashboard.current_opacity}")
            else:
                user_info["opacity"] = 1.0  # Default opacity if not available

            # Add dashboard position information for image analysis
            if self.dashboard and hasattr(self.dashboard, "get_dashboard_position"):
                dashboard_position = self.dashboard.get_dashboard_position()
                user_info["dashboard_position"] = dashboard_position
                print(
                    f"[ANALYSIS] Dashboard position: x={dashboard_position['x']}, y={dashboard_position['y']}"
                )
            else:
                user_info["dashboard_position"] = {
                    "x": 0,
                    "y": 0,
                }  # Default position if not available

            # Get formatted prompt with frontmost app context
            prompt = self.get_formatted_prompt(frontmost_app_info)
            if not prompt:
                return

            # Create and start analysis thread with image data instead of file paths
            analysis_thread = LLMAnalysisThread(
                prompt, self.current_screenshot_data, user_info, parent=self
            )
            analysis_thread.analysis_complete.connect(self._handle_analysis_result)
            analysis_thread.analysis_error.connect(self._handle_analysis_error)

            thread_id = id(analysis_thread)
            self.analysis_threads[thread_id] = analysis_thread
            analysis_thread.finished.connect(lambda: self._cleanup_thread(thread_id))
            analysis_thread.start()

        except Exception as e:
            print(f"Error in LLM analysis: {str(e)}")

    def update_task(self, task, session_id=None):
        """Update current task and storage directory with session_id"""
        if task:
            if session_id:
                self.storage.set_current_task(task, session_id)
                print(
                    f"Updated storage task directory to: {task} with session_id: {session_id}"
                )
            else:
                self.storage.set_current_task(task)
                print(f"Updated storage task directory to: {task} (no session_id)")

    def update_activity_capturing_indicator(self):
        """Update activity capturing indicator position and size"""
        if self.recording_indicator:
            # Get new screen geometry
            screens = QApplication.screens()
            if self.selected_display < len(screens):
                screen = screens[self.selected_display]
                geometry = screen.geometry()

                # Remove old indicator
                self.recording_indicator.close()

                # Create new indicator with updated geometry
                self.recording_indicator = IndicatorWidget(geometry)
                self.recording_indicator.show()

    def _handle_analysis_error(self, error_msg):
        """Handle analysis error"""
        print(f"Analysis error: {error_msg}")

    def _extract_domain_from_url(self, url):
        """Extract domain from URL for app change detection"""
        if not url:
            return None

        try:
            # Remove protocol if present
            if url.startswith(("http://", "https://")):
                url = url.split("://", 1)[1]

            # Extract domain (everything before first '/')
            domain = url.split("/")[0]

            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]

            return domain.lower()
        except Exception as e:
            print(f"[APP_CHANGE] Error extracting domain from URL '{url}': {e}")
            return None

    def _detect_app_change(self, current_app_name, current_url):
        """Detect if app name or domain has changed"""
        try:
            # Extract current domain
            current_domain = self._extract_domain_from_url(current_url)

            # Check for app name change
            app_name_changed = (
                self.previous_app_name is not None
                and current_app_name != self.previous_app_name
            )

            # Check for domain change
            domain_changed = (
                self.previous_app_domain is not None
                and current_domain != self.previous_app_domain
            )

            # Determine if there's a change
            app_changed = app_name_changed or domain_changed

            # Debug logging
            if app_changed:
                if app_name_changed:
                    print(
                        f"[APP_CHANGE] App name changed: '{self.previous_app_name}' -> '{current_app_name}'"
                    )
                if domain_changed:
                    print(
                        f"[APP_CHANGE] Domain changed: '{self.previous_app_domain}' -> '{current_domain}'"
                    )

            # Update previous state
            self.previous_app_name = current_app_name
            self.previous_app_domain = current_domain

            return app_changed

        except Exception as e:
            print(f"[APP_CHANGE] Error detecting app change: {e}")
            # Update previous state even on error
            self.previous_app_name = current_app_name
            self.previous_app_domain = self._extract_domain_from_url(current_url)
            return False

    def _get_recent_local_images(self, count):
        """Deprecated: Images are no longer stored locally"""
        print(
            "[WARNING] _get_recent_local_images called but images are no longer stored locally"
        )
        return []

    def _get_realtime_frontmost_app(self, current_image_file=None):
        """Get real-time frontmost app information with proper structure for server"""
        try:
            current_frontmost_raw = get_frontmost_app()

            # Parse app name and URL
            if " - " in current_frontmost_raw:
                app_name = current_frontmost_raw.split(" - ")[0]
                url = current_frontmost_raw.split(" - ", 1)[1]
            else:
                app_name = current_frontmost_raw
                url = get_browser_url(app_name) or ""

            # Create frontmost_app dict with required fields
            frontmost_app = {
                "app_name": app_name,
                "url": url,
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "image_file": current_image_file or "unknown.jpg",
            }

            return frontmost_app, app_name, url

        except Exception as e:
            print(f"[ERROR] Failed to get frontmost app: {e}")
            # Create fallback frontmost_app with required fields for server
            fallback_app = {
                "app_name": "Unknown",
                "url": "",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "image_file": current_image_file or "unknown.jpg",
            }
            return fallback_app, "", ""

    def _get_frontmost_app_info(self, image_paths):
        """Get frontmost app information for given images from metadata"""
        storage_dir = self.storage.get_capture_dir()
        metadata_path = os.path.join(storage_dir, "_metadata.json")

        if not os.path.exists(metadata_path):
            return []

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            frontmost_info = []
            for img_path in image_paths:
                img_filename = os.path.basename(img_path)

                # Find matching metadata entry
                matching_entry = None
                for entry in metadata:
                    if entry.get("image_file") == img_filename:
                        matching_entry = entry
                        break

                if matching_entry:
                    frontmost_app = matching_entry.get("frontmost_app", "Unknown")
                    url = matching_entry.get("url", "")

                    # Parse app name and URL separately
                    if " - " in frontmost_app:
                        app_name = frontmost_app.split(" - ")[0]
                        url_from_app = frontmost_app.split(" - ", 1)[1]
                        # Use URL from entry if available, otherwise from app string
                        final_url = url or url_from_app
                    else:
                        app_name = frontmost_app
                        final_url = url

                    info = {
                        "image_file": img_filename,
                        "app_name": app_name,
                        "url": final_url,
                        "timestamp": matching_entry.get("timestamp", ""),
                    }
                    frontmost_info.append(info)

            return frontmost_info

        except Exception as e:
            return []

    def get_formatted_prompt(self, frontmost_app=None):
        """Get formatted prompt with current task using advanced prompt system (opacity sent separately as JSON field)"""
        try:
            current_task = (
                self.dashboard.current_task
                if self.dashboard.current_task
                else "No task specified"
            )

            # Use memory data if available, otherwise try to load from files
            clarification_intentions = self.current_clarification_data

            # Check learning data (4 types of feedback learnings)
            reflection_intentions = self.current_reflection_data
            reflection_rules = self.current_reflection_rule

            # Get session start time from dashboard
            session_start_time = None
            if self.dashboard and hasattr(self.dashboard, "current_session_start_time"):
                session_start_time = self.dashboard.current_session_start_time

            # Use the new advanced prompt system with clarification and learning context
            # Note: opacity is now sent as separate JSON field, not in prompt text
            prompt = self.prompt_config.get_advanced_prompt(
                task_name=current_task,
                use_clarification=True,  # Enable clarification context
                clarification_intentions=clarification_intentions,  # Pass memory data directly
                use_reflection=True,  # Enable learning context (renamed but same functionality)
                reflection_intentions=reflection_intentions,  # Pass learning data directly
                reflection_rules=reflection_rules,  # Pass reflection rules directly
                use_context=True,  # Enable context instructions
                use_formatted_prediction=False,  # Disable intent prediction for now
                use_probabilistic_score=True,  # Use probabilistic scoring (0.0-1.0)
                session_start_time=session_start_time,  # Pass session start time for file naming
                frontmost_app=frontmost_app,  # Pass frontmost app info
                opacity=None,  # Opacity no longer passed to prompt
            )

            return prompt

        except Exception as e:
            print(f"[ERROR] Failed to generate formatted prompt: {e}")
            # Fallback to basic prompt
            return self.prompt_config.get_prompt()

    def set_cloud_mode(self, enabled):
        """Set cloud mode"""
        self.cloud_mode = enabled

    def update_intervals(self, capture_interval, llm_interval):
        """Update timer intervals"""
        if self.capture_timer.isActive():
            self.capture_timer.setInterval(capture_interval * 1000)
        if self.llm_timer.isActive():
            self.llm_timer.setInterval(llm_interval * 1000)

    def _cleanup_thread(self, thread_id):
        """Clean up finished thread"""
        if thread_id in self.analysis_threads:
            try:
                print(f"\n=== Cleaning up thread {thread_id} ===")
                thread = self.analysis_threads.pop(
                    thread_id
                )  # Remove from dict immediately

                # Disconnect signals
                try:
                    if hasattr(thread, "analysis_complete"):
                        thread.analysis_complete.disconnect()
                    if hasattr(thread, "analysis_error"):
                        thread.analysis_error.disconnect()
                except Exception as e:
                    print(f"Error disconnecting signals: {e}")

                # Only attempt to terminate if thread is still running
                if thread.isRunning():
                    print(f"Thread {thread_id} is still running, terminating...")
                    # Use safe_quit if available
                    if hasattr(thread, "safe_quit"):
                        thread.safe_quit()
                    else:
                        thread.terminate()
                    # Use short timeout (500ms) to prevent deadlocks
                    if not thread.wait(2000):
                        print(
                            f"Thread {thread_id} did not stop in time, but continuing cleanup"
                        )
                    else:
                        print(f"Thread {thread_id} stopped successfully")
                else:
                    print(f"Thread {thread_id} already finished")

                # Call deleteLater with exception handling
                try:
                    if not hasattr(
                        thread, "safe_quit"
                    ):  # Only call deleteLater if we didn't use safe_quit
                        thread.deleteLater()
                except Exception as e:
                    print(f"Error in deleteLater: {e}")

                # Clean up memory with garbage collection
                import gc

                gc.collect()

                print(
                    f"Thread {thread_id} cleanup completed, remaining threads: {len(self.analysis_threads)}"
                )
            except Exception as e:
                print(f"Error cleaning up thread {thread_id}: {e}")
                import traceback

                print(traceback.format_exc())

    def _check_storage_limit(self, max_size_gb):
        """
        Check if the entire screenshots directory is under the size limit
        Uses caching to avoid performance issues on frequent checks

        Args:
            max_size_gb: Maximum size in GB

        Returns:
            bool: True if under limit, False if over limit
        """
        current_time = time.time()

        # Use cached result if check was done recently (within 5 minutes)
        if current_time - self.last_storage_check_time < self.storage_check_interval:
            return self.last_storage_check_result

        try:
            # Use entire screenshots directory, not current session
            screenshots_dir = self.storage.screenshots_dir
            if not os.path.exists(screenshots_dir):
                self.last_storage_check_result = True
                self.last_storage_check_time = current_time
                return True

            # Calculate total size of all image files in entire screenshots directory
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(screenshots_dir):
                for f in filenames:
                    if f.endswith((".png", ".jpg", ".jpeg")):
                        fp = os.path.join(dirpath, f)
                        try:
                            total_size += os.path.getsize(fp)
                        except OSError:
                            # Skip files that can't be accessed
                            continue

            # Convert to GB and check limit
            total_size_gb = total_size / (1024 * 1024 * 1024)
            print(
                f"[STORAGE] Total screenshots storage usage: {total_size_gb:.2f} GB / {max_size_gb} GB"
            )

            # Cache the result
            self.last_storage_check_result = total_size_gb < max_size_gb
            self.last_storage_check_time = current_time

            return self.last_storage_check_result

        except Exception as e:
            print(f"[STORAGE] Error checking storage limit: {e}")
            self.last_storage_check_result = True  # Default to allow capture on error
            self.last_storage_check_time = current_time
            return True

    def _cleanup_old_captures_by_size(self, target_size_gb):
        """
        Clean up old captures from entire screenshots directory to stay under the target size

        Args:
            target_size_gb: Target size in GB to stay under
        """
        try:
            # Use entire screenshots directory, not current session
            screenshots_dir = self.storage.screenshots_dir
            if not os.path.exists(screenshots_dir):
                return

            # Get all image files from entire screenshots directory
            image_files = []
            for dirpath, dirnames, filenames in os.walk(screenshots_dir):
                for f in filenames:
                    if f.endswith((".png", ".jpg", ".jpeg")):
                        fp = os.path.join(dirpath, f)
                        try:
                            image_files.append(
                                (fp, os.path.getmtime(fp), os.path.getsize(fp))
                            )
                        except OSError:
                            # Skip files that can't be accessed
                            continue

            # Sort by modification time (oldest first)
            image_files.sort(key=lambda x: x[1])

            # Calculate current total size
            total_size = sum(file[2] for file in image_files)
            target_size = target_size_gb * 1024 * 1024 * 1024

            # Delete oldest files until we're under the target size
            files_deleted = 0
            bytes_freed = 0

            for file_path, mtime, size in image_files:
                if total_size <= target_size:
                    break

                try:
                    os.remove(file_path)
                    total_size -= size
                    bytes_freed += size
                    files_deleted += 1
                    print(f"Deleted old capture: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")

            print(
                f"Cleanup complete: {files_deleted} files deleted, {bytes_freed / (1024 * 1024):.2f} MB freed"
            )

        except Exception as e:
            print(f"Error during cleanup: {e}")

    def invoke_llm(self, has_notification=False):
        """Invoke LLM with recent captures"""
        if not self.is_running:
            print("Manager not running, skipping LLM invocation")
            return

        try:
            # Get recent images for analysis
            recent_images = self._get_recent_local_images(LLM_ANALYSIS_IMAGE_COUNT)

            if not recent_images:
                print("\n=== No recent images found, skipping analysis ===")
                return

            # Get current task for analysis context
            task = "Unknown"
            if self.dashboard and self.dashboard.current_task:
                task = self.dashboard.current_task

            # Get real-time frontmost app for prompt (more reliable than metadata)
            current_image_file = (
                os.path.basename(recent_images[0]) if recent_images else "unknown.jpg"
            )
            frontmost_app, app_name, url = self._get_realtime_frontmost_app(
                current_image_file
            )

            # Detect app change
            app_changed = self._detect_app_change(app_name, url)

            # Also get metadata-based info for server (backward compatibility)
            frontmost_info = self._get_frontmost_app_info(recent_images)
            if not frontmost_info:
                # Use real-time data if metadata is not available
                frontmost_info = [frontmost_app]

            # Get formatted prompt with frontmost app context and opacity
            # Get formatted prompt (opacity now sent separately as JSON field)
            prompt = self.get_formatted_prompt(frontmost_app).replace(
                "{task_name}", task
            )

            # Create analysis thread with session info
            thread_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

            # Increment image number for this analysis
            self.current_session_image_num += 1

            # Prepare user info with session_id for new backend schema (user_config removed)
            user_info = {
                "name": "local_user",
                "session_id": (
                    getattr(self.dashboard, "current_session_start_time", thread_id)
                    if self.dashboard
                    else thread_id
                ),
                "current_task": task,
                "device_name": "mac_os_device",
                "notification": has_notification,  # Add notification flag
                "image_num": self.current_session_image_num,  # Session-based image counter
                "frontmost_app": frontmost_app,  # Frontmost app info
                "app_change": app_changed,  # App change detection flag
                "opacity": (
                    getattr(self.dashboard, "current_opacity", 1.0)
                    if self.dashboard
                    else 1.0
                ),  # Dashboard opacity
                "dashboard_position": (
                    self.dashboard.get_dashboard_position()
                    if self.dashboard
                    and hasattr(self.dashboard, "get_dashboard_position")
                    else {"x": 0, "y": 0}
                ),  # Dashboard position
            }

            print(f"  - name: {user_info['name']}")
            print(f"  - session_id: {user_info['session_id']}")
            print(f"  - current_task: {user_info['current_task']}")
            print(f"  - device_name: {user_info['device_name']}")
            print(f"  - notification: {user_info['notification']}")
            print(f"  - image_num: {user_info['image_num']}")
            print(f"  - app_change: {user_info['app_change']}")
            print(f"  - opacity: {user_info['opacity']}")
            print(f"  - dashboard_position: {user_info['dashboard_position']}")

            thread = LLMAnalysisThread(
                prompt,
                recent_images,
                user_info,
            )

            # Connect signals
            thread.analysis_complete.connect(self._handle_analysis_result)
            thread.analysis_error.connect(self._handle_analysis_error)
            thread.finished.connect(lambda: self._cleanup_thread(thread_id))

            # Store and start thread
            self.analysis_threads[thread_id] = thread
            thread.start()

            print(f"\n=== LLM Analysis started with {len(recent_images)} images ===")
            print(f"Thread ID: {thread_id}")
            print(f"Task: {task}")
            print(f"Notification: {has_notification}")
            print(f"Using direct LLM API")
        except Exception as e:
            print(f"Error invoking LLM: {str(e)}")
            import traceback

            print(traceback.format_exc())

    def set_clarification_data(self, clarification_data):
        """Set clarification data in memory for immediate use"""
        self.current_clarification_data = clarification_data
        print(
            f"[CLARIFICATION] Received {len(clarification_data)} augmented intentions"
        )

    def clear_clarification_data(self):
        """Clear clarification data from memory"""
        self.current_clarification_data = None
        print("[CLARIFICATION] Clarification data cleared")

    def set_reflection_data(self, reflection_data):
        """Set clarification data in memory for immediate use"""
        self.current_reflection_data = reflection_data
        print(f"[RELFECTION] Received {len(reflection_data)} augmented intentions")

    def clear_reflection_data(self):
        """Clear clarification data from memory"""
        self.current_reflection_data = None
        print("[RELFECTION] Reflection data cleared")

    def set_reflection_rule(self, reflection_rule):
        """Set clarification data in memory for immediate use"""
        self.current_reflection_rule = reflection_rule
        print(f"[RELFECTION] Received {len(reflection_rule)} augmented intentions")

    def clear_reflection_rule(self):
        """Clear reflection rule from memory"""
        self.current_reflection_rule = None
        print("[REFLECTION] Reflection rule cleared")

    def set_notification_flag(self, has_notification):
        """Set notification flag for next LLM analysis"""
        self.next_analysis_has_notification = has_notification
        if has_notification:
            print("[NOTIFICATION] Flag set for next LLM analysis")

    def _check_screen_lock(self):
        """Check if screen is locked and trigger auto-stop if needed"""
        try:
            if not self.is_running:
                return

            # Check if screen is locked
            is_locked = self.screen_lock_detector.is_screen_locked()

            if is_locked is True:
                print("[SCREEN_LOCK] Screen is locked - triggering auto-stop")
                self._trigger_auto_stop()
            elif is_locked is False:
                # Screen is unlocked - continue normal operation
                pass
            else:
                # Could not determine lock status - continue normal operation
                pass

        except Exception as e:
            print(f"[SCREEN_LOCK] Error checking screen lock: {e}")

    def _trigger_auto_stop(self):
        """Trigger automatic session stop due to screen lock or inactivity"""
        try:
            print("[AUTO_STOP] Triggering automatic session stop")

            if not self.dashboard:
                print("[AUTO_STOP] No dashboard available")
                return

            # Check if currently capturing
            if (
                not hasattr(self.dashboard, "is_capturing")
                or not self.dashboard.is_capturing
            ):
                print("[AUTO_STOP] Session is not currently active")
                return

            # Add a flag to indicate this was auto-stopped
            self.dashboard.auto_stopped_due_to_inactivity = True

            # Call toggle_capture to stop the session
            # This will automatically trigger rating dialog
            print("[AUTO_STOP] Calling toggle_capture to stop session")
            self.dashboard.toggle_capture()

        except Exception as e:
            print(f"[AUTO_STOP] Error triggering auto stop: {e}")

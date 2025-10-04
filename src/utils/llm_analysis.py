import io
import os
import sys
import glob
import json
import subprocess
import base64
import requests
from datetime import datetime
from PIL import Image


from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QWidget, QApplication


from ..config.constants import (
    CAPTURE_INTERVAL,
    LLM_INVOKE_INTERVAL,
    LLM_ANALYSIS_IMAGE_COUNT,
    DEFAULT_STORAGE_DIR,
    IMAGE_QUALITY,
)

from .direct_llm_client import get_configured_client


class LLMAnalysisThread(QThread):
    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)

    def __init__(self, prompt, image_data, user_info, parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.image_data = image_data  # Raw image bytes instead of file paths
        self.user_info = user_info
        self.setObjectName(f"LLMThread_{id(self)}")
        # Add thread termination flag
        self._is_stopping = False
        # Add timeout for network requests
        self._request_timeout = 30  # 30 seconds for direct API calls
        self.llm_client = None

    def __del__(self):
        """Safe destructor to prevent crash during garbage collection"""
        try:
            if hasattr(self, "_is_stopping"):
                self._is_stopping = True
            if self.isRunning():
                self.terminate()
                self.wait(100)  # Short wait
        except:
            pass  # Ignore any errors during destruction

    def safe_quit(self):
        """Safe method to quit the thread"""
        try:
            print(f"[LLM_THREAD] Safely quitting thread {self.objectName()}")
            self._is_stopping = True

            # Clean up LLM client if any
            if hasattr(self, "llm_client") and self.llm_client:
                self.llm_client = None

            if self.isRunning():
                # Try graceful quit first
                self.quit()
                if not self.wait(1000):  # Wait 1 second for graceful quit
                    print(
                        f"[LLM_THREAD] Graceful quit failed, using terminate for {self.objectName()}"
                    )
                    self.terminate()
                    if not self.wait(1000):  # Wait another second for terminate
                        print(
                            f"[LLM_THREAD] Thread {self.objectName()} did not terminate gracefully"
                        )
                    else:
                        print(
                            f"[LLM_THREAD] Thread {self.objectName()} terminated successfully"
                        )
                else:
                    print(f"[LLM_THREAD] Thread {self.objectName()} quit gracefully")

            self.deleteLater()
        except Exception as e:
            print(f"[LLM_THREAD] Error in safe_quit: {e}")

    def run(self):
        try:
            # Check for thread termination request
            if self._is_stopping:
                print("Thread termination requested before starting analysis")
                return

            # Get configured LLM client
            try:
                self.llm_client = get_configured_client()
                if not self.llm_client:
                    self.analysis_error.emit(
                        "No LLM API configured. Please set OPENAI_API_KEY or GEMINI_API_KEY environment variable."
                    )
                    return
            except Exception as e:
                self.analysis_error.emit(f"Failed to initialize LLM client: {str(e)}")
                return

            print(
                f"[LLM] Requesting analysis for: {self.user_info.get('current_task', 'No task')}"
            )
            print(f"[LLM] Using provider: {self.llm_client.provider.value}")

            # Check for thread termination request
            if self._is_stopping:
                print("Thread termination requested before analysis")
                return

            # Prepare context for analysis
            context = {
                "current_task": self.user_info.get("current_task", "No task specified"),
                "frontmost_app": self.user_info.get("frontmost_app", {}),
                "session_id": self.user_info.get("session_id", "unknown_session"),
                "user_id": self.user_info.get("name", "default_user"),
                "device_name": self.user_info.get("device_name", "mac_os_device"),
                "notification": self.user_info.get("notification", False),
                "image_num": self.user_info.get("image_num", 1),
                "app_change": self.user_info.get("app_change", False),
                "opacity": self.user_info.get("opacity", 1.0),
            }

            # Analyze screen using direct LLM API
            result = self.llm_client.analyze_screen(
                image_data=self.image_data, prompt=self.prompt, context=context
            )

            # Check for thread termination request
            if self._is_stopping:
                print("Thread termination requested after analysis")
                return

            # Process the result
            output_score = result.get("output", "Unknown")
            reason = result.get("reason", "No reason")
            print(f"[LLM] Analysis complete (Score: {output_score}): {reason}")

            # Add metadata to result for compatibility
            result["analyzed_images"] = []  # No local images anymore
            result["analyzed_image_count"] = 1
            result["primary_analyzed_image"] = None  # No local image path
            
            # Add prompt for debugging
            result["prompt"] = self.prompt

            # Emit the result
            if self.analysis_complete and not self._is_stopping:
                self.analysis_complete.emit(result)

        except Exception as e:
            if not self._is_stopping:  # Only emit error signal if not terminating
                error_msg = f"Analysis error: {str(e)}"
                print(f"Error: {error_msg}")
                self.analysis_error.emit(error_msg)
            else:
                print(f"[LLM_THREAD] Thread stopped, suppressing error: {str(e)}")

    def terminate(self):
        """Override method for safe thread termination"""
        print(f"Thread {self.objectName()} terminating...")
        self._is_stopping = True
        # Call parent terminate
        super().terminate()

    # Legacy method - no longer used with direct API calls
    def process_server_response(self, response):
        """Deprecated: Process server response (not used with direct API calls)"""
        print(
            "[LLM_THREAD] process_server_response called but not used with direct API"
        )

from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QGraphicsOpacityEffect,
    QScrollArea,
    QDialog,
    QSlider,
)
from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QTimer,
    QCoreApplication,
    QPropertyAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QThread,
    QSize,
    QRect,
    QUrl,
    QEvent,
)
from PyQt6.QtGui import (
    QTextOption,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QDesktopServices,
)

import sys
import objc
import json
import os
import requests
import time
import re
from datetime import datetime
from AppKit import NSWindow, NSWindowSharingNone
from ctypes import c_void_p
from ..config.constants import (
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
    NOTIFICATION_ENABLED,
)
from ..config.language import get_text


# Import new modular components
from .history_manager import TimelineWidget, HistoryManager
from .window_manager import WindowManager
from .llm_client import LLMClient
from .feedback_manager import FeedbackManager

# These will be updated by refresh_ui_language()
TYPE_MESSAGE = get_text("type_message")
CLICK_MESSAGE = get_text("click_message")

# UI Constants
INPUT_HEIGHT = 40  # Height for input fields and buttons
DASHBOARD_WIDTH = 400  # Dashboard width
DASHBOARD_HEIGHT = 100  # Dashboard height
HISTORY_WINDOW_HEIGHT = 200  # History window height (increased for more items)
TIMELINE_HEIGHT = 200  # Timeline widget height (increased for more items)
QUIT_BUTTON_SIZE = 24  # All buttons same size for perfect alignment
BUTTON_WIDTH = 60  # Start button width (wider for text)
START_BUTTON_HEIGHT = 24  # Same height as other buttons for perfect alignment

# Screen Capture Settings
EXCLUDE_FROM_SCREEN_CAPTURE = (
    True  # Set to False to include dashboard in screenshots/recordings
)

# Animation Constants
ANIMATION_SHOW_DURATION = 300  # Show animation duration in ms
ANIMATION_HIDE_DURATION = 200  # Hide animation duration in ms
ANIMATION_SLIDE_OFFSET = 20  # Slide animation offset in pixels


class Dashboard(QWidget):
    # Signals to notify app when capture starts/stops
    capture_started = pyqtSignal()
    capture_stopped = pyqtSignal()
    # play_sound_requested signal removed - sound functionality disabled

    def __init__(self, thread_manager, storage):
        super().__init__()
        self.thread_manager = thread_manager
        self.storage = storage

        # Store clarification data in memory
        self.current_clarification_data = []

        # Flag for auto-starting after clarification completion
        self.auto_start_after_clarification = False

        # Learning data management (now moved to 4-type system below)
        print(f"[DASHBOARD] Initialized")

        # Current task tracking
        self.current_task = None
        self.task_start_time = None
        self.current_session_start_time = (
            None  # Track session start time for reflection files
        )

        print("[DASHBOARD] Starting initialization")

        # App focus monitoring variables
        self.focus_monitoring_enabled = False
        self.last_frontmost_app = None
        self.app_switch_time = None
        self.focus_check_timer = QTimer()
        self.FOCUS_CHECK_INTERVAL = 2000  # Check every 2 seconds
        # Focus popup feature removed - no longer needed

        # Cache current app name for focus monitoring
        self.current_intention_app_name = None

        # Current opacity setting for all windows
        self.current_opacity = 1.0  # Default 100% opacity

        # Connect focus monitoring signals
        self.focus_check_timer.timeout.connect(self._check_app_focus)

        # Initialize managers
        self.history_manager = HistoryManager()
        self.window_manager = WindowManager(self)
        self.llm_client = LLMClient(self)

        # FeedbackManager will be initialized later when storage and prompt_config are available
        self.feedback_manager = FeedbackManager(
            self.thread_manager.prompt_config,
            storage,
            dashboard=self,
            parent=self,
        )

        # Session rating removed - only local storage used
        self.session_rating_manager = None

        # Connect feedback signals
        self.feedback_manager.feedback_processed.connect(self._on_feedback_processed)

        # Feedback-related state variables
        self.last_llm_response = None  # Store last LLM response for feedback
        self.last_analyzed_image = None  # Store last analyzed image path for feedback
        self.last_llm_response_image_id = (
            None  # Store image_id for precise feedback targeting
        )
        # Currently displayed message tracking (separate from latest received)
        self.displayed_message_image_id = None  # ID of message currently shown to user
        self.displayed_message_response = (
            None  # Response data of currently displayed message
        )
        self.displayed_message_timestamp = None  # When the message was displayed
        self.is_processing_feedback = (
            False  # Flag to prevent session termination during feedback
        )

        # Learning from feedback
        self.current_reflection_intentions = []
        self.current_reflection_rules = []

        # Initialize timeline widget
        self.history_timeline = TimelineWidget()

        # Connect timeline signals for intention selection
        self.history_timeline.intention_clicked.connect(self.on_intention_selected)

        # Initialize state variables
        self._current_task = ""
        self.current_rating = 0
        self.clarification_conversation = []
        self.is_capturing = False
        self.history_timer = QTimer()
        self.history_timer.timeout.connect(self.hide_history_window)
        self.history_timer.setSingleShot(True)

        # IME state tracking for Korean input support
        self._ime_composition_active = False
        self._pending_task_set = False

        # Initialize loading animation timer
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_dots = 0
        self.loading_message_widget = None

        # Initialize UI
        self.init_ui()

        # Install event filters on all widgets to catch clicks anywhere on dashboard
        self._install_event_filters()

        # Create all popup windows
        self.window_manager.create_all_windows()

        # Load and display today's history
        history_loaded = self.history_manager.load_intention_history()
        if history_loaded:
            self.load_and_display_today_history()
            print("[DASHBOARD] History loaded and displayed successfully")
        else:
            print("[DASHBOARD] History loading failed, starting with empty state")
            # Still try to display empty state
            self.load_and_display_today_history()

        # Show history window on startup
        QTimer.singleShot(
            500, self.show_history_window
        )  # Small delay to ensure UI is ready

        # Make windows secure from screen capture
        self.window_manager.make_windows_secure(EXCLUDE_FROM_SCREEN_CAPTURE)

        # Make dashboard itself secure from screen capture
        self.makeWindowSecure()

        print("[DASHBOARD] Ready")

        # Focus monitoring will start only when user clicks Start button
        print("[FOCUS] Focus monitoring disabled - will start when user clicks Start")

    def _start_basic_focus_monitoring(self):
        """Start basic focus monitoring without requiring an intention"""
        print("[FOCUS] Starting basic focus monitoring (always active)")
        print(
            f"[FOCUS] Check interval: {self.FOCUS_CHECK_INTERVAL/1000}s, Notification delay: {self.NOTIFICATION_DELAY/1000}s"
        )

        # Get and cache current app name for focus monitoring
        if self.current_intention_app_name is None:
            from ..utils.activity import get_current_app_name

            self.current_intention_app_name = get_current_app_name()
            print(
                f"[FOCUS] Cached intention app name: '{self.current_intention_app_name}'"
            )

        # Enable monitoring even without current task
        self.focus_monitoring_enabled = True

        from ..utils.activity import get_frontmost_app

        self.last_frontmost_app = get_frontmost_app()
        print(f"[FOCUS] Initial app: '{self.last_frontmost_app}'")

        # Start the timer
        self.focus_check_timer.start(self.FOCUS_CHECK_INTERVAL)
        print("[FOCUS] Basic monitoring timer started")

    def _is_korean_text(self, text):
        """Check if text contains Korean characters"""
        import re

        return bool(re.search(r"[가-힣]", text))

    def init_ui(self):
        APP_TITLE = get_text("app_title_1")

        # Basic window settings
        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Set window size
        self.setFixedWidth(DASHBOARD_WIDTH)
        self.setFixedHeight(DASHBOARD_HEIGHT)

        # Main layout setup (no margins)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Container widget (with rounded corners and background)
        self._container_widget = QWidget(self)
        self._container_widget.setObjectName("containerWidget")
        main_layout.addWidget(self._container_widget)

        # Container widget internal layout
        layout = QVBoxLayout(self._container_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Create title bar
        # Create a container for the title bar
        title_bar = QWidget()
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(12, 6, 12, 6)
        title_bar_layout.setSpacing(0)

        # Add drag functionality to the entire title bar
        title_bar.mousePressEvent = self.drag_bar_mouse_press
        title_bar.mouseMoveEvent = self.drag_bar_mouse_move
        title_bar.mouseReleaseEvent = self.drag_bar_mouse_release

        # Opacity slider (left side)
        opacity_container = QWidget()
        opacity_layout = QHBoxLayout(opacity_container)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.setSpacing(4)

        # Opacity label
        opacity_label = QLabel("🔍")
        opacity_label.setFixedSize(16, 16)
        opacity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opacity_label.setStyleSheet("font-size: 12px;")

        # Opacity slider
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setObjectName("opacitySlider")
        self.opacity_slider.setMinimum(20)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(80)
        self.opacity_slider.setFixedHeight(16)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)

        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_slider)

        # Create a container to hold the centered title
        title_center_container = QWidget()
        title_center_layout = QHBoxLayout(title_center_container)
        title_center_layout.setContentsMargins(0, 0, 0, 0)
        title_center_layout.setSpacing(0)

        # Title label (drag bar)
        self.drag_bar = QLabel(APP_TITLE)
        self.drag_bar.setObjectName("dragBar")
        self.drag_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add drag functionality to drag bar only
        self.drag_bar.mousePressEvent = self.drag_bar_mouse_press
        self.drag_bar.mouseMoveEvent = self.drag_bar_mouse_move
        self.drag_bar.mouseReleaseEvent = self.drag_bar_mouse_release

        title_center_layout.addStretch()
        title_center_layout.addWidget(self.drag_bar)
        title_center_layout.addStretch()

        # Settings button (gear icon)
        self.settings_button = QPushButton("⚙")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setFixedSize(QUIT_BUTTON_SIZE, QUIT_BUTTON_SIZE)
        self.settings_button.clicked.connect(self.open_api_settings)

        # Quit button (right aligned)
        self.quit_button = QPushButton("✕")
        self.quit_button.setObjectName("quitButton")
        self.quit_button.setFixedSize(QUIT_BUTTON_SIZE, QUIT_BUTTON_SIZE)
        self.quit_button.clicked.connect(lambda: self.force_quit())

        # Create container for right side buttons
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(4)
        buttons_layout.addWidget(self.settings_button)
        buttons_layout.addWidget(self.quit_button)

        # Add title (centered) and buttons (right aligned) to the main title bar layout
        title_bar_layout.addWidget(opacity_container, 0)  # Opacity slider on left
        title_bar_layout.addWidget(
            title_center_container, 1
        )  # stretch=1 to occupy remaining space
        title_bar_layout.setContentsMargins(12, 6, 0, 6)
        title_bar_layout.addWidget(buttons_container, 0, Qt.AlignmentFlag.AlignRight)

        # Insert the title bar at the top of the main layout
        layout.insertWidget(0, title_bar)

        # Main UI content - FULL mode only
        # STATE 1: Task input state (initial state)
        self.input_container = QWidget()  # Container for input state
        input_layout = QHBoxLayout(self.input_container)  # Horizontal layout
        input_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        input_layout.setSpacing(6)  # Space between elements

        # Task input field
        self.task_input = QTextEdit()
        self.task_input.setPlaceholderText(TYPE_MESSAGE)  # Placeholder text
        self.task_input.setFixedHeight(INPUT_HEIGHT)  # Use constant for height
        self.task_input.setWordWrapMode(
            QTextOption.WrapMode.WordWrap
        )  # Enable word wrap

        # Ensure cursor is visible
        self.task_input.setCursorWidth(2)  # Set cursor width
        self.task_input.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction
        )

        # Connect custom key event handler and mouse events
        self.task_input.keyPressEvent = self.task_input_key_press

        # Handle IME composition events for better Korean input support
        self.task_input.inputMethodEvent = self.task_input_ime_event

        # Additional IME support - ensure proper text handling
        self.task_input.textChanged.connect(self._on_text_changed)

        # Set button to confirm task
        self.set_button = QPushButton(get_text("set_button"))  # Button to set task
        self.set_button.clicked.connect(self.set_task)  # Click handler
        self.set_button.setFixedWidth(BUTTON_WIDTH)  # Fixed button width
        self.set_button.setFixedHeight(INPUT_HEIGHT)  # Use constant for height

        # Add widgets to input layout
        input_layout.addWidget(self.task_input)
        input_layout.addWidget(self.set_button)

        # STATE 2: Task display state (after task is set)
        self.task_container = QWidget()  # Container for task display state
        task_layout = QVBoxLayout(self.task_container)  # Vertical layout
        task_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        task_layout.setSpacing(8)  # Space between elements

        # Task info container (task name and start/stop button)
        task_info_container = QWidget()  # Container for task info
        task_info_layout = QHBoxLayout(task_info_container)  # Horizontal layout
        task_info_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        task_info_layout.setSpacing(6)  # Space between elements

        # Task display field (replaces QLabel)
        self.task_display = QTextEdit()
        self.task_display.setObjectName("taskDisplay")
        self.task_display.setReadOnly(False)
        self.task_display.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.task_display.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.task_display.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.task_display.setFixedHeight(INPUT_HEIGHT)  # Use constant for height
        self.task_display.mousePressEvent = self.task_display_clicked

        # Start/Stop button
        self.start_button = QPushButton(get_text("start_button"))  # Start/stop button
        self.start_button.setObjectName("startButton")
        self.start_button.setCheckable(True)
        self.start_button.clicked.connect(self.toggle_capture)
        self.start_button.setFixedWidth(BUTTON_WIDTH)
        self.start_button.setFixedHeight(INPUT_HEIGHT)  # Use constant for height

        # Add widgets in correct order
        task_info_layout.addWidget(self.task_display)
        task_info_layout.addWidget(self.start_button)

        # Message label to show status/feedback
        self.message_label = QLabel()  # Label for status messages
        self.message_label.setObjectName("messageLabel")  # CSS selector name
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center text
        self.message_label.setWordWrap(True)  # Enable word wrapping
        self.message_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )  # Size policy for dynamic height

        # Add widgets to task layout
        task_layout.addWidget(task_info_container)
        task_layout.addWidget(self.message_label)
        self.task_container.hide()  # Hide task container initially

        # Add both containers to main layout
        layout.addWidget(self.input_container)  # Add input container
        layout.addWidget(self.task_container)  # Add task container

        # CSS styling for the dashboard
        self.setStyleSheet(
            """
            /* Parent widget (Dashboard) is completely transparent */
            Dashboard {
                background-color: transparent;
            }
            
            /* Container widget with rounded corners and background */
            #containerWidget {
                background-color: #202020;  /* Completely opaque dark gray */
                border-radius: 6px;  /* Smaller rounded corners for compact design */
            }
            
            QLineEdit {
                background-color: #2D2D2D;  /* Opaque input field background */
                border: none;  /* No border */
                border-radius: 8px;  /* Rounded corners */
                padding: 8px 12px;  /* Inner padding */
                font-size: 14px;  /* Font size */
                selection-background-color: #505050;  /* Selection color */
                margin-right: 4px;  /* Right margin */
                min-width: 80px;  /* Minimum width */
                color: white;  /* Text color */
            }

            QPushButton {
                background-color: #464646;  /* Opaque button background */
                border: none;  /* No border */
                border-radius: 8px;  /* Rounded corners */
                padding: 8px 12px;  /* Inner padding */
                font-size: 14px;  /* Font size */
                text-transform: none;  /* Lowercase text */
                min-width: 40px;  /* Minimum width */
                font-weight: 600;  /* Semi-bold text */
                color: white;  /* Text color */
            }

            QPushButton:hover {
                background-color: #555555;  /* Hover state */
            }

            QTextEdit {
                background-color: #2D2D2D;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: white;
                min-width: 80px;
            }

            QTextEdit#taskDisplay { 
                background-color: #2D2D2D; 
                border-radius: 8px; 
                padding: 8px 12px; 
                font-size: 13px; 
                color: white; 
            }

            #dragBar {
                background-color: rgba(30, 30, 30, 0.75);
                color: white;  
                font-size: 14px;  /* Reduced from 16px for more compact look */
                font-weight: bold;
            }
            #compactDragBar {
                background-color: transparent;
                color: white;  
                font-size: 10px;  /* Very small for compact mode */
                font-weight: 500;
                padding: 2px 0px;
            }

            #settingsButton {
                background-color: #666666;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                padding: 0px;
            }
            #settingsButton:hover {
                background-color: #777777;
            }

            #quitButton {
                background-color: #ff3b30;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                padding: 0px;
            }
            #quitButton:hover {
                background-color: #ff5e57;
            }
            #startButton {
                background-color: #007AFF;  /* Blue start button */
            }
            #startButton:hover {
                background-color: #1E8EFF;  /* Hover state */
            }
            #startButton:checked {
                background-color: #FF3B30;  /* Red when recording (checked) */
            }
            #startButton:checked:hover {
                background-color: #FF4F44;  /* Hover state when checked */
            }
            #messageLabel {
                padding: 10px 12px;  /* Inner padding */
                border-radius: 8px;  /* Rounded corners */
                font-size: 14px;  /* Font size */
                font-weight: 600;  /* Semi-bold text */
                letter-spacing: 0.2px;  /* Letter spacing */
                line-height: 1.3;  /* Line height */
                margin: 0px;  /* No margin */
                color: white;  /* Text color */
            }
            #messageLabel[status="processing"] {
                background-color: #3C3C3C;  /* Opaque processing background */
                color: #FFFFFF;  /* Text color */
                font-size: 13px;  /* Font size */
            }
            #messageLabel[status="waiting"] {
                background-color: #2D2D2D;  /* Opaque waiting background */
                color: #FFFFFF;  /* Text color */
                font-size: 13px;  /* Font size */
            }
            #messageLabel[status="focused"] {
                background-color: #2ecc71;  /* Green - for focused state (0) */
                font-size: 14px;  /* Font size */
            }
            #messageLabel[status="distracted"] {
                background-color: #e74c3c;  /* Red - for distracted state (1) */
                font-size: 14px;  /* Font size */
            }
            #bigStartButton {
                background-color: #007AFF;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border-radius: 10px;
            }
            #bigStartButton:hover {
                background-color: #0069D9;
            }
            #bigStartButton:checked {
                background-color: #FF3B30;
            }
            #compactStartButton {
                background-color: #007AFF;
                color: white;
                font-size: 14px;
                font-weight: 600;
                border-radius: 8px;
                padding: 4px 12px;
                min-width: 40px;
            }
            #compactStartButton:hover {
                background-color: #0069D9;
            }
            #compactStartButton:checked {
                background-color: #FF3B30;
            }
            #basicTitleLabel {
                color: white;
                font-size: 14px;
                font-weight: 600;
                background-color: transparent;
                padding: 0px;
                margin: 0px;
            }
            #instructionLabel {
                color: #CCCCCC;
                font-size: 14px;
            }
            
            /* Opacity slider styles */
            #opacitySlider {
                background: transparent;
            }
            #opacitySlider::groove:horizontal {
                border: 1px solid #666666;
                height: 4px;
                background: #333333;
                border-radius: 2px;
            }
            #opacitySlider::handle:horizontal {
                background: #007AFF;
                border: 1px solid #005BB8;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            #opacitySlider::handle:horizontal:hover {
                background: #1E8EFF;
            }
            #opacitySlider::sub-page:horizontal {
                background: #007AFF;
                border: 1px solid #005BB8;
                height: 4px;
                border-radius: 2px;
            }
            
        """
        )

    def task_input_key_press(self, event):
        """Custom key handler for QTextEdit to allow Enter = set_task, Shift+Enter = new line"""
        # Prevent keyboard input if rating window is visible
        if self.is_rating_window_visible():
            print("[DEBUG] Rating required before keyboard input")
            return

        if event.key() == Qt.Key.Key_Return and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            # Check if IME composition is in progress
            if self._ime_composition_active:
                # IME composition is active, defer task setting
                self._pending_task_set = True
                QTextEdit.keyPressEvent(self.task_input, event)
                return

            # No IME composition active, safe to set task
            # Small delay to ensure any final text processing is complete
            QTimer.singleShot(50, self.set_task)
        else:
            QTextEdit.keyPressEvent(self.task_input, event)

    def task_input_ime_event(self, event):
        """Handle IME composition events for better Korean input support"""
        # Check if composition is starting
        if hasattr(event, "preeditString") and event.preeditString():
            self._ime_composition_active = True

        # Call the default implementation to handle composition
        QTextEdit.inputMethodEvent(self.task_input, event)

        # Store the composition state for better handling
        if hasattr(event, "commitString") and event.commitString():
            # Composition is complete, text has been committed
            self._ime_composition_active = False
            # Force text update to ensure all characters are properly handled
            QTimer.singleShot(50, lambda: self.task_input.update())

            # If there was a pending task set, execute it now
            if self._pending_task_set:
                self._pending_task_set = False
                QTimer.singleShot(100, self.set_task)

    def _on_text_changed(self):
        """Handle text changes to ensure IME composition is properly handled"""
        # This method helps ensure Korean IME text is properly committed
        # Reset IME composition state when text changes
        if not self._ime_composition_active:
            # Text changed but not due to IME composition
            pass

    def set_task(self):
        """Set the current task from the input field"""
        # User config removed - direct local usage only
        if False:  # Disabled - no user validation needed
            from ..ui.dialogs import Dialogs

            Dialogs.show_error(
                "Credentials Required",
                "Please enter your assigned User ID and Password in Settings > User Settings before setting a task.",
            )
            # Open user settings dialog automatically
            self.open_user_settings()
            return

        # Force any pending IME composition to complete
        self.task_input.clearFocus()
        self.task_input.setFocus()

        # Get the text after ensuring IME completion
        task = self.task_input.toPlainText().strip()
        if not task:
            return

        # Store task info
        self._current_task = task

        # Generate session_id immediately when task is set
        if not self.current_session_start_time:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_task_name = "".join(
                c for c in task if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            clean_task_name = clean_task_name.replace(" ", "_")[:30]
            self.current_session_start_time = f"{clean_task_name}_{timestamp}"
            print(f"[DEBUG] Generated session_id: {self.current_session_start_time}")
        else:
            print(
                f"[DEBUG] Using existing session_id: {self.current_session_start_time}"
            )

        # Update task display
        self.task_display.setText(task)
        self.start_button.setText(get_text("start_button"))

        # Keep message label hidden to prevent layout changes
        self.message_label.hide()
        self.message_label.setVisible(False)
        self.message_label.setMaximumHeight(0)
        self.message_label.setMinimumHeight(0)

        # Switch to task state
        self.show_task_state()

        # Clear previous clarification data when setting new task
        self.current_clarification_data = []
        if hasattr(self, "thread_manager"):
            self.thread_manager.clear_clarification_data()
        if hasattr(self, "llm_client") and hasattr(
            self.llm_client, "clarification_manager"
        ):
            self.llm_client.clarification_manager.reset()
        print("[CLARIFICATION] Cleared previous clarification data for new task")

        # Show clarification window
        self.show_clarification_window(task)

        # Start focus monitoring when intention is set
        self.start_focus_monitoring()

        # Clear input field only after everything is set
        self.task_input.clear()

    def show_input_state(self):
        """Show input container (State 1) and hide task container."""
        # Prevent switching to input state if rating window is visible
        if self.is_rating_window_visible():
            print("[DEBUG] Rating required before switching to input state")
            return

        # Stop focus monitoring when returning to input state
        self.stop_focus_monitoring()

        # Clear clarification data when returning to input state (user will set new intention)
        self.current_clarification_data = []
        if hasattr(self, "thread_manager"):
            self.thread_manager.clear_clarification_data()
        if hasattr(self, "llm_client") and hasattr(
            self.llm_client, "clarification_manager"
        ):
            self.llm_client.clarification_manager.reset()
        print(
            "[CLARIFICATION] Cleared clarification data when returning to input state"
        )

        # Re-enable UI elements when switching to input state
        self.task_display.setEnabled(True)
        self.task_display.setStyleSheet("")

        self.input_container.show()
        self.task_container.hide()

        # Show history window when switching to input state
        self.show_history_window()

        # Completely hide message label
        self.message_label.hide()
        self.message_label.setVisible(False)
        self.message_label.setMaximumHeight(0)
        self.message_label.setMinimumHeight(0)

        self.message_label.setText("")
        self.message_label.setProperty("status", "")

        # Force layout update without changing window size
        self.task_container.updateGeometry()
        self.layout().activate()

        self.task_input.setFocus()

    def show_task_state(self):
        """Show task container (State 2) and hide input container."""
        self.input_container.hide()
        self.task_container.show()

        # Keep message label hidden to prevent layout changes
        self.message_label.hide()
        self.message_label.setVisible(False)
        self.message_label.setMaximumHeight(0)
        self.message_label.setMinimumHeight(0)

        # Force layout update without changing window size
        self.task_container.updateGeometry()
        self.layout().activate()

    def toggle_capture(self):
        """Toggle capturing on/off"""
        # 🔥 CRITICAL: Reset feedback flag if user manually clicks stop button
        if self.is_processing_feedback and self.is_capturing:
            print("[DEBUG] User clicked stop - force clearing feedback processing flag")
            self.is_processing_feedback = False

            # 🔥 CRITICAL: Reset ALL feedback states when stopping
            self._reset_all_feedback_states()
            print("[DEBUG] All feedback states reset on stop")

        # Only block if trying to start during feedback processing (not stop)
        if self.is_processing_feedback and not self.is_capturing:
            print("[DEBUG] BLOCKED: Cannot start capture during feedback processing")
            return

        # Check if user ID and password are set before allowing capture start
        if not self.is_capturing and False:  # Disabled - no user validation needed
            if (
                not user_info
                or not user_info.get("name")
                or not user_info.get("password")
            ):
                from ..ui.dialogs import Dialogs

                Dialogs.show_error(
                    "Credentials Required",
                    "Please enter your assigned User ID and Password in Settings > User Settings before starting capture.",
                )
                # Open user settings dialog automatically
                self.open_user_settings()
                return

        # Check if task is set
        if not self._current_task:
            print("Error: No task set for capture")
            return

        if not self.is_capturing:
            # Start recording - hide clarification window, history window and show starting soon
            self.hide_clarification_window()
            self.hide_history_window()

            # Show starting soon window
            self.show_starting_soon_window()

            # Use existing session_id (already generated when task was set)
            if not self.current_session_start_time:
                # Fallback: generate session_id if not already created
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_task_name = "".join(
                    c for c in self._current_task if c.isalnum() or c in (" ", "-", "_")
                ).rstrip()
                clean_task_name = clean_task_name.replace(" ", "_")[:30]
                self.current_session_start_time = f"{clean_task_name}_{timestamp}"
                print(
                    f"[DEBUG] Fallback: Generated session_id: {self.current_session_start_time}"
                )
            else:
                print(
                    f"[DEBUG] Using existing session_id: {self.current_session_start_time}"
                )

            # Handle clarification data
            if self.current_clarification_data:
                # Use existing clarification data
                self.thread_manager.set_clarification_data(
                    self.current_clarification_data
                )
                print("[CLARIFICATION] Using existing clarification data")
            elif self.is_clarification_in_progress():
                # Clarification is in progress but not completed - force complete it
                print(
                    "[CLARIFICATION] Start pressed during clarification - completing with current responses"
                )
                self.force_complete_clarification_and_start()
                return  # Exit early, will restart after clarification completes
            else:
                # No clarification data - proceed with original intention only
                print(
                    "[CLARIFICATION] No clarification data - proceeding with original intention"
                )
                pass

            # Start intention session
            self.start_intention_session(self._current_task)

            self.start_button.setText(get_text("stop_button"))
            self.is_capturing = True
            self.capture_started.emit()

            # Update to "set/started" state with message
            self.message_label.setText(CLICK_MESSAGE)

            self.task_display.setReadOnly(True)
            self.task_display.setStyleSheet(
                "background-color: #343434; color: white; border-radius: 8px;"
            )
        else:
            # Check if feedback is being processed - warn but still allow session termination
            if self.is_processing_feedback:
                print(
                    "[DEBUG] Feedback processing in progress - force stopping session anyway"
                )
                # Force clear feedback processing flag
                self.is_processing_feedback = False

            # Stop recording - hide all windows and return to initial state
            self.hide_starting_soon_window()
            self.hide_llm_response_window()
            self.hide_feedback_window()

            # Clear context data from thread manager when stopping
            self.thread_manager.clear_clarification_data()
            self.thread_manager.clear_reflection_data()
            self.thread_manager.clear_reflection_rule()

            # End intention session
            print("[DEBUG] MANUAL SESSION TERMINATION: User clicked stop button")
            self.end_intention_session()

            # Clear session start time
            self.current_session_start_time = None
            print("[DEBUG] Session ended, session start time cleared")

            # Change button text and state
            self.is_capturing = False
            self.capture_stopped.emit()
            self.start_button.setText(get_text("start_button"))
            self.start_button.setChecked(False)

            # Return to initial state (input state)
            self.show_input_state()

        # Always update the checked state of the button
        # self.start_button.setChecked(self.is_capturing)  # Moved to on_rating_complete

    def update_intention_level(self, level, message, raw_value=0.0):
        """Update the displayed intention level and message"""
        # Skip updating if session is no longer active
        if not self.is_capturing:
            print(f"[DEBUG] Ignoring analysis result - session is stopped")
            return

        # Store AI judgment for feedback system
        self.last_ai_judgement = level
        print(
            f"[DASHBOARD] AI judgment stored: {level} ({'focused' if level == 0 else 'distracted'})"
        )

        # Check if this is a state change and request sound playback
        previous_level = getattr(self, "current_level", None)
        if previous_level is None or previous_level != level:
            print(f"[DASHBOARD] State change detected: {previous_level} -> {level}")
            # Sound request removed - sound functionality disabled

        # Track focus/distracted messages in history manager (skip for BASIC mode)
        # REMOVED: Now using rating system instead of automatic count tracking
        # if (
        #     APP_MODE != APP_MODE_BASIC
        #     and self.history_manager
        #     and self.history_manager.current_session
        # ):
        #     if level == 0:  # Focused
        #         self.history_manager.add_focus_message()
        #     else:  # Distracted (level == 1)
        #         self.history_manager.add_distracted_message()
        #
        #     # Update rating display in real-time
        #     self.update_rating_display()

        # Update level and message
        # Store level and message
        self.current_level = level
        self.current_message = message

        # Only process if we're in task display state and capturing
        if self.task_container.isVisible() and self.is_capturing:
            # Show LLM response window with appropriate color
            self.show_llm_response_window(message, raw_value)

    # Drag bar specific mouse handlers - Only allow dragging from drag bar
    def drag_bar_mouse_press(self, event):
        """Handle mouse press on drag bar to start window dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()  # Store position

    def drag_bar_mouse_move(self, event):
        """Handle mouse movement on drag bar to move window"""
        if hasattr(self, "oldPos") and self.oldPos:
            delta = event.globalPosition().toPoint() - self.oldPos  # Calculate movement
            self.move(self.pos() + delta)  # Move window
            self.oldPos = event.globalPosition().toPoint()  # Update position

            # Update all popup window positions through WindowManager
            self.window_manager.update_all_window_positions()

    def drag_bar_mouse_release(self, event):
        """Handle mouse release on drag bar to end window dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = None  # Reset position

    # Dashboard mouse handlers - Allow dragging from dashboard
    def mousePressEvent(self, event):
        """Handle mouse press for dashboard interactions and dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Start dragging
            self.oldPos = event.globalPosition().toPoint()

            # Focus popup feature removed
            pass

    def mouseMoveEvent(self, event):
        """Handle mouse movement - allow dragging from dashboard"""
        if hasattr(self, "oldPos") and self.oldPos:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.pos() + delta)
            self.oldPos = event.globalPosition().toPoint()

            # Update all popup window positions through WindowManager
            self.window_manager.update_all_window_positions()

    def mouseReleaseEvent(self, event):
        """Handle mouse release - end dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = None

    def setup_window_level(self):
        """Setup window level for macOS - Keep window above others"""
        if sys.platform == "darwin":
            try:
                from AppKit import NSApp, NSFloatingWindowLevel

                self.show()
                windows = NSApp.windows()
                if windows:
                    windows[-1].setLevel_(NSFloatingWindowLevel)  # Set floating level

                # 창이 실제로 보여진 후 보안 설정 적용
                self.makeWindowSecure()
            except ImportError:
                self.show()
        else:
            self.show()

    def makeWindowSecure(self):
        """창을 보안 모드로 설정하여 화면 캡처에서 제외 (설정에 따라)"""
        if sys.platform == "darwin" and EXCLUDE_FROM_SCREEN_CAPTURE:
            try:
                # Main window security
                native_view = objc.objc_object(c_void_p=int(self.winId()))
                ns_window = native_view.window()
                ns_window.setSharingType_(NSWindowSharingNone)
                print("[DASHBOARD] Screen capture protection enabled")

                # All popup windows security is handled by WindowManager
                self.window_manager.make_windows_secure(EXCLUDE_FROM_SCREEN_CAPTURE)

            except Exception as e:
                print(f"[ERROR] Failed to enable screen capture protection: {e}")
        elif sys.platform == "darwin" and not EXCLUDE_FROM_SCREEN_CAPTURE:
            print("[DASHBOARD] Screen capture protection disabled (debug mode)")
        else:
            print(
                "[DASHBOARD] Screen capture protection not available on this platform"
            )

    @property
    def current_task(self):
        """Property getter for current task"""
        return self._current_task

    @current_task.setter
    def current_task(self, value):
        """Property setter for current task"""
        self._current_task = value.strip() if isinstance(value, str) else ""

    def resizeEvent(self, event):
        """Window resize event handler"""
        # Not using setMask method - parent widget is transparent and child widget has border-radius applied
        pass

    def is_rating_window_visible(self):
        """Check if rating window is currently visible"""
        rating_window = self.window_manager.windows.get("rating")
        return rating_window and rating_window.isVisible()

    def is_clarification_window_visible(self):
        """Check if clarification window is currently visible"""
        clarification_window = self.window_manager.windows.get("clarification")
        return clarification_window and clarification_window.isVisible()

    def is_settings_dialog_visible(self):
        """Check if any settings dialog is visible"""
        # Check for various settings dialogs
        settings_dialogs = [
            "user_settings_dialog",
            "language_settings_dialog",
            "settings_dialog",
        ]

        for dialog_attr in settings_dialogs:
            if hasattr(self, dialog_attr):
                dialog = getattr(self, dialog_attr)
                if dialog and hasattr(dialog, "isVisible") and dialog.isVisible():
                    return True

        # Also check for any visible QDialog children
        from PyQt6.QtWidgets import QDialog

        for child in self.findChildren(QDialog):
            if child.isVisible():
                return True

        return False

    def task_display_clicked(self, event):
        """Handle task display click to allow editing"""
        # Prevent interaction if rating window is visible
        if self.is_rating_window_visible():
            print("[DEBUG] Rating required before proceeding")
            return

        if not self.start_button.isChecked():  # Only allow editing when not running
            self.task_input.setPlainText(
                self.current_task
            )  # Copy current task to input field
            self.show_input_state()  # Switch to input mode

    def show_settings_menu(self):
        """Show settings menu with various options"""
        from PyQt6.QtWidgets import QMenu

        # Create context menu
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #2D2D2D;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #007AFF;
            }
        """
        )

        # Add menu items
        api_settings_action = menu.addAction("API Settings")
        api_settings_action.triggered.connect(self.open_api_settings)

        # Language Settings removed - English only
        # Sound Settings removed - sound functionality disabled
        # Display Settings removed - single display auto-selection

        # Show menu at settings button position
        button_pos = self.settings_button.mapToGlobal(
            self.settings_button.rect().bottomLeft()
        )
        menu.exec(button_pos)

    def open_api_settings(self):
        """Open unified settings dialog"""
        from .unified_settings_dialog import UnifiedSettingsDialog

        dialog = UnifiedSettingsDialog(self)
        dialog.exec()

    def open_user_settings(self):
        """Deprecated: Redirect to API settings"""
        try:
            from ..ui.settings_dialog import UserSettingsDialog
            from PyQt6.QtWidgets import QDialog

            self.user_settings_dialog = UserSettingsDialog({})
            if self.user_settings_dialog.exec() == QDialog.DialogCode.Accepted:
                user_input = self.user_settings_dialog.get_user_input()
                name, password, device = (
                    user_input["name"],
                    user_input["password"],
                    user_input["device"],
                )
                if name and password and device:
                    self.config.set_user_info(
                        name=name, password=password, device_name=device
                    )
                    print(f"User credentials updated: {name}, {device}")
            # Clear reference after dialog closes
            self.user_settings_dialog = None
        except Exception as e:
            print(f"Error opening user settings: {e}")
            # Clear reference on error
            self.user_settings_dialog = None

    def open_language_settings(self):
        """Open language settings dialog from dashboard"""
        try:
            from ..ui.settings_dialog import LanguageSettingsDialog
            from PyQt6.QtWidgets import QDialog

            self.language_settings_dialog = LanguageSettingsDialog(self)

            # Connect language change signal
            self.language_settings_dialog.language_changed.connect(
                self._on_language_changed
            )

            self.language_settings_dialog.exec()
            # Clear reference after dialog closes
            self.language_settings_dialog = None
        except Exception as e:
            print(f"Error opening language settings: {e}")
            # Clear reference on error
            self.language_settings_dialog = None

    def _on_language_changed(self, new_language):
        """Handle language change from dashboard settings"""
        print(f"[LANGUAGE] Language changed to: {new_language} from dashboard")

        # Refresh dashboard UI immediately
        self.refresh_ui_language()

    # open_sound_settings method removed - sound functionality disabled
    # open_display_settings method removed - single display auto-selection

    def force_quit(self):
        """Forcefully quit the entire application, including background process"""
        QCoreApplication.quit()
        sys.exit(0)

    def load_and_display_today_history(self):
        """Load and display today's intention history"""
        try:
            today_records = self.history_manager.get_today_records()

            if today_records:
                print(f"[DASHBOARD] Today's data: {len(today_records)} records")
            else:
                print("[DASHBOARD] No data for today - this is normal for first run")

            # Clear existing timeline items
            self.history_timeline.clear_items()

            # Add today's records to timeline with record data
            for record in today_records:
                try:
                    formatted_record = self.history_manager.format_record_for_display(
                        record
                    )
                    self.history_timeline.add_item(
                        formatted_record, record
                    )  # Pass record data
                except Exception as e:
                    print(f"[ERROR] Failed to format record: {e}")
                    continue

            # Update rating display
            self.update_rating_display()

            # If no records exist, ensure UI is still properly initialized
            if not today_records:
                print(
                    "[DASHBOARD] Initialized with empty history - ready for first intention"
                )

        except Exception as e:
            print(f"[ERROR] Failed to load today's history: {e}")
            # Ensure timeline is cleared even if there's an error
            if hasattr(self, "history_timeline"):
                self.history_timeline.clear_items()
            # Still try to update rating display
            try:
                self.update_rating_display()
            except Exception as rating_error:
                print(f"[ERROR] Failed to update rating display: {rating_error}")

    def update_rating_display(self):
        """Rating display functionality removed - no longer showing daily rating"""
        # This method is kept for compatibility but no longer displays rating
        pass

    def start_intention_session(self, intention):
        """Start a new intention session"""
        session_id = getattr(self, "current_session_start_time", None)
        return self.history_manager.start_intention_session(intention, session_id)

    def end_intention_session(self):
        """End the current intention session"""
        session_ended = self.history_manager.end_intention_session()
        if session_ended:
            # Refresh the timeline display
            self.load_and_display_today_history()
            # Update rating display immediately
            self.update_rating_display()
        return session_ended

    def format_duration(self, duration_minutes):
        """Format duration from minutes to hours:minutes format"""
        return self.history_manager.format_duration(duration_minutes)

    def update_history_display_from_real_data(self):
        """Update history display using real intention data"""
        # This is now handled by load_and_display_today_history
        self.load_and_display_today_history()

    def show_history_window(self):
        """Show history window with animation"""
        # Hide other windows that should not be visible with history
        self.hide_clarification_window()
        self.hide_llm_response_window()
        self.hide_starting_soon_window()

        self.window_manager.show_window_with_animation("history")

    def hide_history_window(self):
        """Hide history window with animation"""
        self.window_manager.hide_window_with_animation("history")

    def show_clarification_window(self, initial_task):
        """Show clarification window with initial AI message"""

        # Hide other windows that should not be visible with clarification
        self.hide_history_window()

        # Clear previous conversation
        self.clear_clarification_chat()

        # Clear previous clarification data when starting new clarification
        self.current_clarification_data = []
        if hasattr(self, "thread_manager"):
            self.thread_manager.clear_clarification_data()
        if hasattr(self, "llm_client") and hasattr(
            self.llm_client, "clarification_manager"
        ):
            self.llm_client.clarification_manager.reset()
        print(
            "[CLARIFICATION] Cleared previous clarification data for new clarification"
        )

        # Re-enable input and send button for new clarification
        self.enable_clarification_input()

        # Show the clarification window with animation
        self.window_manager.show_window_with_animation("clarification")

        # Start new clarification cycle
        self.llm_client.start_clarification_cycle(initial_task)

    def hide_clarification_window(self):
        """Hide clarification window with animation"""
        self.window_manager.hide_window_with_animation("clarification")

    def show_starting_soon_window(self):
        """Show starting soon window"""
        # Hide other windows that should not be visible with starting soon
        self.hide_history_window()
        self.hide_clarification_window()
        self.hide_llm_response_window()

        self.window_manager.show_window("starting_soon")

    def hide_starting_soon_window(self):
        """Hide starting soon window"""
        self.window_manager.hide_window("starting_soon")

    def hide_llm_response_window(self):
        """Hide LLM response window"""
        self.window_manager.hide_window("llm_response")

    def show_llm_response_window(self, message, raw_value=0.0):
        """Show LLM response window with message"""

        # Hide other windows that should not be visible with LLM response
        self.hide_starting_soon_window()
        self.hide_history_window()
        self.hide_clarification_window()

        # Store raw_value for feedback message determination
        self.current_raw_value = raw_value

        # 🔥 CRITICAL: Store currently displayed message info for accurate feedback
        self.displayed_message_image_id = self.last_llm_response_image_id
        self.displayed_message_response = self.last_llm_response
        self.displayed_message_timestamp = time.time()

        print(
            f"[FEEDBACK_TARGET] Message displayed - Image ID: {self.displayed_message_image_id}"
        )
        print(
            f"[FEEDBACK_TARGET] This will be the target for any feedback given on this message"
        )

        if raw_value <= 0.2:
            status = "focused"
        elif raw_value <= 0.6:  # Back to 0.6 as requested
            status = "ambiguous"
        else:
            status = "distracted"

        print(f"[UI] LLM response window with status: {status}")
        self.llm_response_label.setText(message)

        # Adjust window height based on message length
        self.window_manager.adjust_llm_response_window_height(message)

        # Set status-based styling
        container = self.llm_response_window.findChild(QWidget, "llmContainer")
        if container:
            container.setProperty("status", status)
            container.style().unpolish(container)
            container.style().polish(container)

        self.window_manager.show_window("llm_response")

        # Remove automatic feedback window display
        # Feedback window will only show on mouse hover

    def llm_response_enter_event(self, event):
        """Show feedback window when mouse enters LLM response window"""
        # Cancel any pending hide timer
        if hasattr(self, "feedback_hide_timer") and self.feedback_hide_timer.isActive():
            self.feedback_hide_timer.stop()

        # Update feedback message based on current raw value
        self._update_feedback_message()

        # Show feedback window immediately
        self.window_manager.show_window_with_animation("feedback")

    def _update_feedback_message(self):
        """Update feedback message based on current raw value"""
        if not hasattr(self, "current_raw_value"):
            return

        # Determine feedback message based on raw_value
        if self.current_raw_value <= 0.2:
            feedback_message = get_text("feedback_focused")
        elif self.current_raw_value <= 0.6:
            feedback_message = get_text("feedback_ambiguous")
        else:  # 0.7 - 1.0
            feedback_message = get_text("feedback_distracted")

        # Find and update the feedback window message label
        feedback_window = self.window_manager.windows.get("feedback")
        if feedback_window:
            # Look for the question label in the feedback window
            message_label = feedback_window.findChild(QLabel, "questionLabel")
            if message_label:
                message_label.setText(feedback_message)
                print(
                    f"[FEEDBACK] Updated message: '{feedback_message}' (score: {self.current_raw_value:.1f})"
                )
            else:
                print(f"[FEEDBACK] Question label not found in feedback window")

    def llm_response_leave_event(self, event):
        """Hide feedback window when mouse leaves LLM response window"""
        # Start timer to hide feedback window after short delay
        if not hasattr(self, "feedback_hide_timer"):
            self.feedback_hide_timer = QTimer()
            self.feedback_hide_timer.setSingleShot(True)
            self.feedback_hide_timer.timeout.connect(self.hide_feedback_window)

        self.feedback_hide_timer.start(300)  # 300ms delay before hiding

    def feedback_window_enter_event(self, event):
        """Keep feedback window visible when mouse enters"""
        # Cancel any pending hide timer
        if hasattr(self, "feedback_hide_timer") and self.feedback_hide_timer.isActive():
            self.feedback_hide_timer.stop()

    def feedback_window_leave_event(self, event):
        """Hide feedback window when mouse leaves with a small delay"""
        # Start timer to hide feedback window after short delay
        if not hasattr(self, "feedback_hide_timer"):
            self.feedback_hide_timer = QTimer()
            self.feedback_hide_timer.setSingleShot(True)
            self.feedback_hide_timer.timeout.connect(self.hide_feedback_window)

        self.feedback_hide_timer.start(300)  # 300ms delay before hiding

    def show_feedback_window_with_delay(self):
        """Show feedback window 1 second after LLM response - REMOVED"""
        # This method is no longer used - feedback only shows on hover
        pass

    def hide_feedback_window(self):
        """Hide feedback window with animation"""
        # 🔥 CRITICAL: Reset ALL feedback states when hiding feedback window
        if self.is_processing_feedback:
            print("[DEBUG] Feedback window closed - resetting ALL feedback states")
            self._reset_all_feedback_states()
        else:
            # Even if not processing, still clean up UI states
            try:
                self.reset_feedback_buttons()
                # Text input removed - no need to hide container
                if hasattr(self, "selected_feedback_type"):
                    self.selected_feedback_type = None
                print("[DEBUG] Feedback UI states cleaned up")
            except Exception as e:
                print(f"[DEBUG] Error cleaning feedback UI states: {e}")

        self.window_manager.hide_window_with_animation("feedback")

    def handle_feedback_click(self, feedback_type, button):
        """Handle feedback button click with simple border highlight"""
        # Stop any hide timers
        if hasattr(self, "feedback_hide_timer") and self.feedback_hide_timer:
            self.feedback_hide_timer.stop()

        # Set feedback processing flag to prevent session termination
        self.is_processing_feedback = True

        # 🔥 SAFE: Set timeout with safe exception handling
        try:
            if not hasattr(self, "feedback_timeout_timer"):
                self.feedback_timeout_timer = QTimer()
                self.feedback_timeout_timer.setSingleShot(True)
                self.feedback_timeout_timer.timeout.connect(
                    self._reset_feedback_timeout
                )

            # Start 30-second timeout (reduced from 60s to minimize crash window)
            if hasattr(self.feedback_timeout_timer, "start"):
                self.feedback_timeout_timer.start(30000)  # 30 seconds
                print(
                    "[DEBUG] Feedback timeout started (30s) - auto-reset if not completed"
                )
        except Exception as e:
            print(f"[DEBUG] Error setting feedback timeout: {e}")
            # Continue without timeout if timer setup fails

        # Store the selected feedback type for later submission
        self.selected_feedback_type = feedback_type

        # Determine the feedback case based on AI judgment and user feedback
        if hasattr(self, "last_ai_judgement"):
            ai_judgement_text = (
                "distracted" if self.last_ai_judgement == 1 else "focused"
            )
            print(
                f"[FEEDBACK] AI judgment: {self.last_ai_judgement} ({ai_judgement_text})"
            )
            print(f"[FEEDBACK] User feedback: {feedback_type}")
        else:
            print(f"[FEEDBACK] Warning: No AI judgment stored")

        # Simple visual feedback - change button border
        self.highlight_feedback_button(button, feedback_type)

        # Process feedback immediately (text input feature removed)
        print(f"[FEEDBACK] Processing {feedback_type} feedback immediately")
        self._process_feedback_submission(feedback_type)

    def expand_feedback_window(self):
        """Expand feedback window to accommodate text input"""
        if hasattr(self, "feedback_window"):
            # Expand to larger size (reduced height since no skip button)
            self.feedback_window.setFixedSize(400, 200)
            # Update container geometry
            container = self.feedback_window.findChild(QWidget, "feedbackContainer")
            if container:
                container.setGeometry(0, 0, 400, 200)

    def shrink_feedback_window(self):
        """Shrink feedback window back to button-only size"""
        if hasattr(self, "feedback_window"):
            # Shrink to original size
            self.feedback_window.setFixedSize(400, 90)
            # Update container geometry
            container = self.feedback_window.findChild(QWidget, "feedbackContainer")
            if container:
                container.setGeometry(0, 0, 400, 90)

    def highlight_feedback_button(self, button, feedback_type):
        """Highlight clicked feedback button with border color"""
        # Reset both buttons to default style first
        if hasattr(self, "good_feedback_button"):
            self.good_feedback_button.setStyleSheet("")
        if hasattr(self, "bad_feedback_button"):
            self.bad_feedback_button.setStyleSheet("")

        # Highlight the clicked button
        if feedback_type == "good":
            border_color = "#28a745"  # Green
        else:
            border_color = "#dc3545"  # Red

        button.setStyleSheet(
            f"""
            QPushButton {{
                border: 2px solid {border_color};
                border-radius: 12px;
            }}
        """
        )

    def _process_feedback_submission(self, feedback_type):
        """Process feedback submission immediately (text input removed)"""
        print(f"[FEEDBACK] Processing {feedback_type} feedback")

        # Get AI judgment for reflection processing
        if hasattr(self, "last_ai_judgement"):
            ai_judgement_text = (
                "distracted" if self.last_ai_judgement == 1 else "focused"
            )
        else:
            ai_judgement_text = "unknown"

        # 🔥 CRITICAL: Use displayed message ID for accurate feedback (not latest received)
        feedback_image_id = (
            self.displayed_message_image_id or self.last_llm_response_image_id
        )
        feedback_response = self.displayed_message_response or self.last_llm_response

        # Check if feedback is for a recently displayed message (within 5 minutes)
        time_since_display = time.time() - (self.displayed_message_timestamp or 0)
        if time_since_display > 300:  # 5 minutes
            print(
                f"[FEEDBACK_WARNING] Feedback given {time_since_display:.0f}s after message display"
            )
            print(f"[FEEDBACK_WARNING] This might not be for the intended message")

        print(f"[FEEDBACK_TARGET] Using Image ID: {feedback_image_id}")
        print(
            f"[FEEDBACK_TARGET] vs Latest received ID: {self.last_llm_response_image_id}"
        )

        if feedback_image_id != self.last_llm_response_image_id:
            print(
                f"[FEEDBACK_MISMATCH] ⚠️  Feedback target differs from latest message!"
            )

        # Also process feedback for reflection (using displayed message data)
        self.feedback_manager.process_feedback(
            task_name=self.current_task,
            llm_response=(
                feedback_response
                if feedback_response
                else """
```json
{
    "reason": "unknown",
    "output": 0.0
}
"""
            ),
            image_path=self.last_analyzed_image,
            ai_judgement=ai_judgement_text,
            feedback_type=feedback_type,
            image_id=feedback_image_id,  # Use displayed message ID
            user_text="",  # Text input removed
        )

        # Reset button styles
        self.reset_feedback_buttons()

        # Hide feedback window
        QTimer.singleShot(500, self.hide_feedback_window)

        # Reset processing flag
        self.is_processing_feedback = False

    def reset_feedback_buttons(self):
        """Reset feedback button styles to default"""
        if hasattr(self, "good_feedback_button"):
            self.good_feedback_button.setStyleSheet("")
        if hasattr(self, "bad_feedback_button"):
            self.bad_feedback_button.setStyleSheet("")

    def moveEvent(self, event):
        """Handle window move event to update popup window positions"""
        super().moveEvent(event)
        # Update all popup window positions when dashboard moves
        self.update_window_positions()

    def update_loading_animation(self):
        """Update the loading animation"""
        self.loading_dots = (self.loading_dots + 1) % 4
        if self.loading_message_widget:
            loading_text = get_text("loading")
            self.loading_message_widget.setText(
                f"{loading_text}{'.' * self.loading_dots}"
            )

    def _unlock_session_termination(self):
        """Unlock session termination after feedback processing is complete"""
        self.is_processing_feedback = False

    def _reset_all_feedback_states(self):
        """Reset all feedback-related states to clean slate"""
        try:
            print("[DEBUG] Resetting ALL feedback states...")

            # 1. Reset feedback processing flag
            self.is_processing_feedback = False

            # 2. 🔥 SAFE: Stop feedback timeout timer with exception handling
            try:
                if (
                    hasattr(self, "feedback_timeout_timer")
                    and self.feedback_timeout_timer
                    and hasattr(self.feedback_timeout_timer, "isActive")
                    and self.feedback_timeout_timer.isActive()
                ):
                    self.feedback_timeout_timer.stop()
                    print("[DEBUG] ✅ Feedback timeout timer stopped")
            except Exception as e:
                print(f"[DEBUG] Error stopping feedback timeout timer: {e}")

            # 3. 🔥 SAFE: Stop feedback hide timer with exception handling
            try:
                if (
                    hasattr(self, "feedback_hide_timer")
                    and self.feedback_hide_timer
                    and hasattr(self.feedback_hide_timer, "isActive")
                    and self.feedback_hide_timer.isActive()
                ):
                    self.feedback_hide_timer.stop()
                    print("[DEBUG] ✅ Feedback hide timer stopped")
            except Exception as e:
                print(f"[DEBUG] Error stopping feedback hide timer: {e}")

            # 4. Reset button styles to default
            self.reset_feedback_buttons()

            # 5. Text input feature removed - no need to hide/shrink

            # 6. Clear selected feedback type
            if hasattr(self, "selected_feedback_type"):
                self.selected_feedback_type = None
                print("[DEBUG] Selected feedback type cleared")

            # 7. Text input feature removed - no field to clear

            # 8. Hide feedback window completely
            if (
                hasattr(self, "window_manager")
                and "feedback" in self.window_manager.windows
            ):
                feedback_window = self.window_manager.windows["feedback"]
                if feedback_window and feedback_window.isVisible():
                    self.hide_feedback_window()
                    print("[DEBUG] Feedback window hidden")

            print("[DEBUG] ✅ All feedback states reset successfully")

        except Exception as e:
            print(f"[DEBUG] Error resetting feedback states: {e}")

    def _reset_feedback_timeout(self):
        """Reset feedback processing flag after timeout"""
        if self.is_processing_feedback:
            print(
                "[DEBUG] Feedback timeout reached - auto-resetting feedback processing flag"
            )
            # Use the comprehensive reset method
            self._reset_all_feedback_states()

    def _on_feedback_processed(self, feedback_result):
        """Handle feedback processing completion"""
        try:
            # Stop timeout timer since feedback is completed
            if (
                hasattr(self, "feedback_timeout_timer")
                and self.feedback_timeout_timer.isActive()
            ):
                self.feedback_timeout_timer.stop()
                print("[DEBUG] Feedback completed - timeout timer stopped")

            # Unlock session termination - user can now stop session
            self.is_processing_feedback = False

        except Exception as e:
            print(f"[ERROR] Feedback processing error: {e}")

    def store_llm_response_for_feedback(self, llm_response, analyzed_image_path):
        """Store the latest LLM response and image for potential feedback"""
        try:
            # Store image_id and response for feedback
            image_id = llm_response.get("image_id", None)

            if image_id:
                print(
                    f"[FEEDBACK_STORAGE] New LLM response received - Image ID: {image_id}"
                )

                self.last_llm_response = llm_response
                self.last_llm_response_reason = llm_response.get("reason", "")
                self.last_llm_response_image_path = analyzed_image_path
                self.last_llm_response_image_id = image_id

                # Store image path for feedback (this was missing!)
                self.last_analyzed_image = analyzed_image_path

                # Determine AI judgment based on output (store as number for consistency)
                output = llm_response.get("output", 0)
                self.last_ai_judgement = (
                    1 if output >= 0.5 else 0
                )  # 1=distracted, 0=focused

                print(
                    f"[FEEDBACK] AI judgment stored: {self.last_ai_judgement} ({'distracted' if self.last_ai_judgement == 1 else 'focused'})"
                )

                # Check if this creates a mismatch with displayed message
                if (
                    hasattr(self, "displayed_message_image_id")
                    and self.displayed_message_image_id
                    and self.displayed_message_image_id != image_id
                ):
                    print(
                        f"[FEEDBACK_STORAGE] ⚠️  New message received while user sees different message!"
                    )
                    print(
                        f"[FEEDBACK_STORAGE] Displayed: {self.displayed_message_image_id} | New: {image_id}"
                    )

        except Exception as e:
            print(f"[ERROR] Failed to store LLM response: {e}")

    def cleanup(self):
        """Clean up resources when dashboard is being destroyed"""
        print("[DASHBOARD] Starting cleanup...")

        # Stop focus monitoring
        self.stop_focus_monitoring()

        # Clean up all manager threads
        if hasattr(self, "llm_client"):
            self.llm_client.cleanup()

        if hasattr(self, "feedback_manager"):
            self.feedback_manager.cleanup()

        # Clean up ThreadManager (most important)
        if hasattr(self, "thread_manager"):
            self.thread_manager.stop()

        print("[DASHBOARD] Cleanup complete")

    def show_rating_window(self):
        """Show rating window with animation"""
        self.reset_rating_progress()
        self.window_manager.show_window_with_animation("rating")

    def hide_rating_window(self):
        """Hide rating window with animation"""
        self.window_manager.hide_window_with_animation("rating")

    def update_window_positions(self):
        """Update all window positions when dashboard moves"""
        self.window_manager.update_all_window_positions()

    def clear_clarification_chat(self):
        """Clear the clarification chat"""
        # Remove all widgets from chat layout
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Add stretch back
        self.chat_layout.addStretch()

        # Clear conversation history
        self.clarification_conversation = []

    def add_clarification_message(self, text, is_user=True):
        """Add a message to the clarification chat"""
        # Remove the stretch from the end
        if self.chat_layout.count() > 0:
            last_item = self.chat_layout.itemAt(self.chat_layout.count() - 1)
            if last_item.spacerItem():
                self.chat_layout.removeItem(last_item)

        # Create message label
        message_label = QLabel(text)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(
            f"""
            background-color: {'#E5E5EA' if is_user else '#007AFF'};
            color: {'#000000' if is_user else '#FFFFFF'};
            border-radius: 12px;
            padding: 8px 12px;
            margin: 2px;
            max-width: 250px;
        """
        )

        # Create container for alignment
        message_container = QWidget()
        container_layout = QHBoxLayout(message_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        if is_user:
            # User messages align right
            container_layout.addStretch()
            container_layout.addWidget(message_label)
        else:
            # AI messages align left
            container_layout.addWidget(message_label)
            container_layout.addStretch()

        self.chat_layout.addWidget(message_container)

        # Add stretch at the end
        self.chat_layout.addStretch()

        # Handle loading animation
        loading_text = get_text("loading")
        if not is_user and text.startswith(loading_text):
            # Start loading animation for AI loading messages
            self.loading_message_widget = message_label
            self.loading_dots = 0
            self.loading_timer.start(500)  # Update every 500ms
        else:
            # Stop loading animation for any other message
            self.stop_loading_animation()

        # Scroll to bottom
        QTimer.singleShot(50, self.scroll_clarification_to_bottom)

        # Store in conversation history (but not loading messages)
        loading_text = get_text("loading")
        if not text.startswith(loading_text):
            self.clarification_conversation.append({"text": text, "is_user": is_user})

    def stop_loading_animation(self):
        """Stop the loading animation"""
        if self.loading_timer.isActive():
            self.loading_timer.stop()
        self.loading_message_widget = None

    def scroll_clarification_to_bottom(self):
        """Scroll clarification chat to bottom"""
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def send_clarification_message(self):
        """Handle sending a clarification message"""
        message = self.clarification_input.text().strip()
        if message:
            # Add user message
            self.add_clarification_message(message, is_user=True)
            self.clarification_input.clear()

            # Add user answer to clarification cycle
            self.llm_client.add_user_answer(message)

    def on_clarification_question_received(self, response):
        """Handle clarification question from LLM"""

        # Remove the "Loading..." message
        self.remove_last_clarification_message()

        # Add the actual AI response
        self.add_clarification_message(response, is_user=False)

    def on_augmentation_received(self, response):
        """Handle augmentation response from LLM"""

        # Remove the "Loading..." message
        self.remove_last_clarification_message()

        # Parse JSON response and save to memory
        try:
            import json
            import re

            # Clean the response
            response_str = re.sub(r"```(?:json)?", "", response).strip()

            if response_str:
                data_dict = json.loads(response_str)
                sorted_list = [data_dict[str(i)] for i in range(1, 11)]

                # Store clarification data in memory for immediate use
                self.current_clarification_data = sorted_list
                print(f"[CLARIFICATION] Augmented to {len(sorted_list)} intentions")

                # Also save to file for persistence (optional)
                filepath = self.llm_client.save_results(sorted_list)

                # Show simple completion message
                completion_msg = get_text("clarification_complete")
                self.add_clarification_message(completion_msg, is_user=False)

                # Disable send button and input field after completion
                self.disable_clarification_input()

                # Auto-start capture if flag is set and not already capturing
                if (
                    getattr(self, "auto_start_after_clarification", False)
                    and not self.is_capturing
                ):
                    self.auto_start_after_clarification = False
                    # Hide clarification window and start capture
                    self.hide_clarification_window()
                    QTimer.singleShot(
                        500, self.toggle_capture
                    )  # Small delay to ensure UI updates
                elif self.is_capturing:
                    # Already capturing, just update clarification data
                    print(
                        "[CLARIFICATION] Already capturing, just updating clarification data"
                    )
                    self.auto_start_after_clarification = False

            else:
                # Show simple completion message even if augmentation failed
                completion_msg = get_text("clarification_complete")
                self.add_clarification_message(completion_msg, is_user=False)

                # Disable send button and input field after completion
                self.disable_clarification_input()

                # Auto-start capture if flag is set and not already capturing (even if augmentation failed)
                if (
                    getattr(self, "auto_start_after_clarification", False)
                    and not self.is_capturing
                ):
                    self.auto_start_after_clarification = False
                    # Use original intention as fallback
                    if hasattr(self, "llm_client") and hasattr(
                        self.llm_client, "clarification_manager"
                    ):
                        original_intention = (
                            self.llm_client.clarification_manager.stated_intention
                        )
                        self.current_clarification_data = [original_intention] * 10
                    # Hide clarification window and start capture
                    self.hide_clarification_window()
                    QTimer.singleShot(500, self.toggle_capture)
                elif self.is_capturing:
                    # Already capturing, just use original intention as fallback
                    print(
                        "[CLARIFICATION] Already capturing, using original intention as fallback"
                    )
                    if hasattr(self, "llm_client") and hasattr(
                        self.llm_client, "clarification_manager"
                    ):
                        original_intention = (
                            self.llm_client.clarification_manager.stated_intention
                        )
                        self.current_clarification_data = [original_intention] * 10
                    self.auto_start_after_clarification = False

        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            # Show simple completion message even if parsing failed
            completion_msg = get_text("clarification_complete")
            self.add_clarification_message(completion_msg, is_user=False)

            # Disable send button and input field after completion
            self.disable_clarification_input()

            # Auto-start capture if flag is set and not already capturing (even if JSON parsing failed)
            if (
                getattr(self, "auto_start_after_clarification", False)
                and not self.is_capturing
            ):
                self.auto_start_after_clarification = False
                # Use original intention as fallback
                if hasattr(self, "llm_client") and hasattr(
                    self.llm_client, "clarification_manager"
                ):
                    original_intention = (
                        self.llm_client.clarification_manager.stated_intention
                    )
                    self.current_clarification_data = [original_intention] * 10
                # Hide clarification window and start capture
                self.hide_clarification_window()
                QTimer.singleShot(500, self.toggle_capture)
            elif self.is_capturing:
                # Already capturing, just use original intention as fallback
                print(
                    "[CLARIFICATION] Already capturing, using original intention as fallback (JSON parse error)"
                )
                if hasattr(self, "llm_client") and hasattr(
                    self.llm_client, "clarification_manager"
                ):
                    original_intention = (
                        self.llm_client.clarification_manager.stated_intention
                    )
                    self.current_clarification_data = [original_intention] * 10
                self.auto_start_after_clarification = False
        except Exception as e:
            print(f"Error processing augmentation: {e}")
            # Show simple completion message even if error occurred
            completion_msg = get_text("clarification_complete")
            self.add_clarification_message(completion_msg, is_user=False)

            # Disable send button and input field after completion
            self.disable_clarification_input()

            # Auto-start capture if flag is set and not already capturing (even if error occurred)
            if (
                getattr(self, "auto_start_after_clarification", False)
                and not self.is_capturing
            ):
                self.auto_start_after_clarification = False
                # Use original intention as fallback
                if hasattr(self, "llm_client") and hasattr(
                    self.llm_client, "clarification_manager"
                ):
                    original_intention = (
                        self.llm_client.clarification_manager.stated_intention
                    )
                    self.current_clarification_data = [original_intention] * 10
                # Hide clarification window and start capture
                self.hide_clarification_window()
                QTimer.singleShot(500, self.toggle_capture)
            elif self.is_capturing:
                # Already capturing, just use original intention as fallback
                print(
                    "[CLARIFICATION] Already capturing, using original intention as fallback (general error)"
                )
                if hasattr(self, "llm_client") and hasattr(
                    self.llm_client, "clarification_manager"
                ):
                    original_intention = (
                        self.llm_client.clarification_manager.stated_intention
                    )
                    self.current_clarification_data = [original_intention] * 10
                self.auto_start_after_clarification = False

    def get_last_ai_message(self):
        """Get the last AI message from conversation history"""
        loading_text = get_text("loading")
        for conv in reversed(self.clarification_conversation):
            if not conv["is_user"] and not conv["text"].startswith(loading_text):
                return conv["text"]
        return ""

    def on_initial_clarification_received(self, response):
        """Handle initial clarification response from LLM (deprecated)"""
        # Redirect to new method
        self.on_clarification_question_received(response)

    def on_clarification_response_received(self, response):
        """Handle clarification response from LLM for user messages (deprecated)"""
        # Redirect to new method
        self.on_clarification_question_received(response)

    def on_clarification_error(self, error_message):
        """Handle clarification API error"""
        print(f"[CLARIFICATION] Error: {error_message}")

        # Remove the "Loading..." message
        self.remove_last_clarification_message()

        # Add fallback message
        fallback_message = "Hey! Could you be a bit more specific about your intention?"
        self.add_clarification_message(fallback_message, is_user=False)

    def remove_last_clarification_message(self):
        """Remove the last message from clarification chat (used to remove loading message)"""
        # Stop loading animation first
        self.stop_loading_animation()

        if self.chat_layout.count() > 1:  # Keep at least the stretch
            # Remove the last widget (which should be the loading message)
            last_item = self.chat_layout.itemAt(
                self.chat_layout.count() - 2
            )  # -2 because of stretch
            if last_item and last_item.widget():
                last_item.widget().deleteLater()
                self.chat_layout.removeItem(last_item)

    def reset_rating_progress(self):
        """Reset rating progress bar to default state"""
        self.current_rating = 0
        if hasattr(self, "progress_bar"):
            self.progress_bar.set_value(0)  # Reset to no selection

        # Disable UI elements while rating window is visible
        self.disable_ui_for_rating()

    def set_rating(self, rating):
        """Set the session rating and submit"""
        self.current_rating = rating
        print(
            f"[RATING] User rated session: {rating}/5 (0%=1, 25%=2, 50%=3, 75%=4, 100%=5)"
        )

        # Prepare session info for rating submission
        session_info = {
            "user_id": "local_user",  # User config removed
            "session_id": getattr(self, "current_session_start_time", None),
            "task_name": self.current_task or "Unknown Task",
            "intention": self.current_task or "",
            "device_name": "mac_os_device",  # User config removed
            "app_mode": "rating_submission",
        }

        # Store rating in history manager and end session immediately
        if hasattr(self, "history_manager") and self.history_manager:
            self.history_manager.set_session_rating(rating)
            print(f"[RATING] Stored rating in history: {rating}/5")

            # End session immediately to save with rating
            session_ended = self.history_manager.end_intention_session()
            if session_ended:
                print(f"[RATING] Session ended and saved with rating: {rating}/5")
                # Refresh the timeline display
                self.load_and_display_today_history()
                # Update rating display immediately
                self.update_rating_display()

        # Backend rating removed - rating saved locally only
        print(f"[RATING] Rating saved locally: {rating}/5")

        # Hide rating window after 1 second and show history
        QTimer.singleShot(1000, self.on_rating_complete)

    def on_rating_complete(self):
        """Called when rating is complete"""
        # Session already ended in set_rating(), just clean up UI

        # Stop focus monitoring when session ends
        self.stop_focus_monitoring()

        # 🔥 CRITICAL: Reset ALL feedback states when session ends
        self._reset_all_feedback_states()
        print("[DEBUG] All feedback states reset on session complete")

        # Hide rating window
        self.hide_rating_window()

        # Re-enable UI elements after rating is complete
        self.enable_ui_after_rating()

        # Now clear session info after rating is complete
        self.current_session_start_time = None
        print("[DEBUG] Rating complete, session_id cleared")

        # Reset current task to empty state
        self._current_task = ""
        self.task_input.clear()
        self.task_display.clear()

        # Switch back to input state (this will show Set button and history window for non-BASIC modes)
        QTimer.singleShot(300, self.show_input_state)

        # 🔥 CRITICAL: DO NOT restart focus monitoring after manual stop
        # Focus monitoring should only restart when user manually sets new intention
        # Restarting here causes memory leaks from timer threads
        print("[FOCUS] ⚠️  Focus monitoring NOT restarted - preventing memory leaks")

    def disable_ui_for_rating(self):
        """Disable all UI elements when rating window is visible"""
        # Disable task display and start button
        self.task_display.setEnabled(False)
        self.start_button.setEnabled(False)

        # Apply disabled styling
        self.task_display.setStyleSheet(
            """
            QTextEdit#taskDisplay { 
                background-color: #666666; 
                border-radius: 8px; 
                padding: 8px 12px; 
                font-size: 13px; 
                color: #999999; 
            }
        """
        )

        self.start_button.setStyleSheet(
            """
            #startButton {
                background-color: #666666;
                color: #999999;
                font-size: 14px;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
                min-width: 40px;
            }
        """
        )

    def enable_ui_after_rating(self):
        """Re-enable all UI elements after rating is complete"""
        # Re-enable task display and start button
        self.task_display.setEnabled(True)
        self.start_button.setEnabled(True)

        # Reset to default styling
        self.task_display.setStyleSheet("")
        self.start_button.setStyleSheet("")

    def on_intention_selected(self, intention, record):
        """Handle intention selection from timeline"""
        print(f"[DASHBOARD] Selected intention: {intention}")

        # Reset button state to initial "Start" state
        self.start_button.setText(get_text("start_button"))
        self.start_button.setChecked(False)
        self.is_capturing = False

        # Clear any session state
        self.current_session_start_time = None

        # Clear the input field first to remove placeholder
        self.task_input.clear()

        # Set the intention text in both input and display
        self.task_input.setText(intention)
        self.task_display.setText(intention)

        # Force UI update to show the text
        self.task_input.setFocus()
        self.task_input.update()
        self.task_input.repaint()

        # Update current task
        self.current_task = intention

        # Switch to task display state (showing the intention and start button)
        self.show_task_state()

        # Additional fix: Ensure text is visible after UI state change
        QTimer.singleShot(50, lambda: self._ensure_text_visible(intention))

        # Load past clarification and reflection data
        self.load_past_settings(intention, record)

        # Start focus monitoring when intention is selected
        self.start_focus_monitoring()

        print(f"[DASHBOARD] Ready to start with: {intention}")

    def _ensure_text_visible(self, intention):
        """Ensure the intention text is visible in both input fields"""
        # Double-check that the text is in both fields
        input_text = self.task_input.toPlainText()
        display_text = self.task_display.toPlainText()

        if input_text != intention:
            print(f"[DEBUG] Input text mismatch. Setting again: '{intention}'")
            self.task_input.setText(intention)

        if display_text != intention:
            print(f"[DEBUG] Display text mismatch. Setting again: '{intention}'")
            self.task_display.setText(intention)

        # Force update on the currently visible element (task_display)
        self.task_display.update()

        print(f"[DEBUG] Final text - Input: '{input_text}', Display: '{display_text}'")

    def load_past_settings(self, intention, record):
        """Load clarification and reflection data for the selected intention"""
        try:
            # Load clarification data using session_id from record
            self.load_clarification_for_intention(intention, record)

            # Load reflection data
            self.load_reflection_for_intention(intention)

            print(f"[DASHBOARD] Loaded past settings for: {intention}")

        except Exception as e:
            print(f"[ERROR] Failed to load past settings: {e}")

    def load_clarification_for_intention(self, intention, record=None):
        """Load clarification data for a specific intention using session_id if available"""
        try:
            from ..logging.storage import LocalStorage

            storage = LocalStorage()

            # Try to use session_id from record first
            session_id = None
            if record and "session_id" in record:
                session_id = record["session_id"]

            if session_id:
                # Use session_id for exact match
                clarification_file = f"{session_id}_clarification.json"
                print(
                    f"[DASHBOARD] Looking for clarification with session_id: {session_id}"
                )
            else:
                # Fallback to old method using task name
                clean_task_name = "".join(
                    c for c in intention if c.isalnum() or c in (" ", "-", "_")
                ).rstrip()
                clean_task_name = clean_task_name.replace(" ", "_")
                clarification_file = f"{clean_task_name}_clarification.json"
                print(
                    f"[DASHBOARD] Fallback: Looking for clarification with task name: {clean_task_name}"
                )

            clarification_path = os.path.join(
                storage.get_clarification_data_dir(), clarification_file
            )

            if os.path.exists(clarification_path):
                with open(clarification_path, "r", encoding="utf-8") as f:
                    clarification_data = json.load(f)

                # Set clarification data in thread manager
                if hasattr(self, "thread_manager"):
                    self.thread_manager.set_clarification_data(clarification_data)
                    print(
                        f"[DASHBOARD] Loaded clarification data for: {intention} (file: {clarification_file})"
                    )
            else:
                print(f"[DASHBOARD] No clarification file found: {clarification_file}")

        except Exception as e:
            print(f"[ERROR] Failed to load clarification data: {e}")

    def load_reflection_for_intention(self, intention):
        """Load reflection/feedback data for a specific intention"""
        try:
            from ..logging.storage import LocalStorage

            storage = LocalStorage()

            # Clean task name for filename
            clean_task_name = "".join(
                c for c in intention if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            clean_task_name = clean_task_name.replace(" ", "_")

            # Try to load different types of reflection data files
            reflection_files = [
                f"{clean_task_name}_dislike_on_notification.json",
                f"{clean_task_name}_dislike_on_focus.json",
                f"{clean_task_name}_like_on_notification.json",
                f"{clean_task_name}_like_on_focus.json",
            ]

            reflection_data = {
                "dislike_on_notification": [],
                "dislike_on_focus": [],
                "like_on_notification": [],
                "like_on_focus": [],
            }

            reflection_types = [
                "dislike_on_notification",
                "dislike_on_focus",
                "like_on_notification",
                "like_on_focus",
            ]

            # Load each type of reflection data if file exists
            loaded_count = 0
            for i, filename in enumerate(reflection_files):
                file_path = os.path.join(storage.get_clarification_data_dir(), filename)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            reflection_data[reflection_types[i]] = data
                            loaded_count += 1
                    except Exception as e:
                        print(f"[ERROR] Failed to load {filename}: {e}")

            # Set reflection data in thread manager
            if hasattr(self, "thread_manager"):
                self.thread_manager.set_dislike_on_notification(
                    reflection_data["dislike_on_notification"]
                )
                self.thread_manager.set_dislike_on_focus(
                    reflection_data["dislike_on_focus"]
                )
                self.thread_manager.set_like_on_notification(
                    reflection_data["like_on_notification"]
                )
                self.thread_manager.set_like_on_focus(reflection_data["like_on_focus"])

                if loaded_count > 0:
                    print(
                        f"[DASHBOARD] Loaded {loaded_count} reflection data files for: {intention}"
                    )
                else:
                    print(f"[DASHBOARD] No reflection data found for: {intention}")

        except Exception as e:
            print(f"[ERROR] Failed to load reflection data: {e}")

    def disable_clarification_input(self):
        """Disable the clarification input field and send button after 2 turns"""
        if hasattr(self, "clarification_input"):
            self.clarification_input.setEnabled(False)
            self.clarification_input.setPlaceholderText("Clarification completed")
            self.clarification_input.setStyleSheet(
                """
                #clarificationInput {
                    background-color: #666666;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 13px;
                    color: #999999;
                }
            """
            )

        if hasattr(self, "clarification_send_button"):
            self.clarification_send_button.setEnabled(False)
            self.clarification_send_button.setStyleSheet(
                """
                #clarificationSendButton {
                    background-color: #666666;
                    color: #999999;
                    font-size: 13px;
                    font-weight: bold;
                    border: none;
                    border-radius: 8px;
                }
            """
            )

        print("[CLARIFICATION] Input and send button disabled after 2 turns")

    def enable_clarification_input(self):
        """Enable the clarification input field and send button for new clarification"""
        if hasattr(self, "clarification_input"):
            self.clarification_input.setEnabled(True)
            self.clarification_input.setPlaceholderText(
                get_text("clarification_placeholder")
            )
            self.clarification_input.setStyleSheet(
                """
                #clarificationInput {
                    background-color: #2D2D2D;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 13px;
                    color: white;
                }
            """
            )

        if hasattr(self, "clarification_send_button"):
            self.clarification_send_button.setEnabled(True)
            self.clarification_send_button.setStyleSheet(
                """
                #clarificationSendButton {
                    background-color: #FFD60A;
                    color: #000000;
                    font-size: 13px;
                    font-weight: bold;
                    border: none;
                    border-radius: 8px;
                }
                #clarificationSendButton:hover {
                    background-color: #FFED4E;
                }
            """
            )

        print("[CLARIFICATION] Input and send button enabled for new clarification")

    def is_clarification_in_progress(self):
        """Check if clarification is currently in progress"""
        # Check if clarification window is visible and clarification is not completed
        if not self.is_clarification_window_visible():
            return False

        if hasattr(self, "llm_client") and hasattr(
            self.llm_client, "clarification_manager"
        ):
            manager = self.llm_client.clarification_manager
            # Clarification is in progress if it has started but not completed
            return (
                manager.stated_intention
                and not manager.is_complete
                and len(manager.qa_pairs) >= 0
            )  # At least started (even with 0 Q&A pairs)

        return False

    def force_complete_clarification_and_start(self):
        """Force complete clarification with current responses and then start capture"""
        print(
            "[CLARIFICATION] Force completing clarification and starting capture immediately"
        )

        # IMMEDIATELY update UI state to avoid confusion
        self.start_button.setText(get_text("stop_button"))
        self.is_capturing = True
        self.capture_started.emit()

        # Hide clarification window immediately
        self.hide_clarification_window()

        # Show starting soon window immediately
        self.show_starting_soon_window()

        # Update task display to readonly mode immediately
        self.task_display.setReadOnly(True)
        self.task_display.setStyleSheet(
            "background-color: #343434; color: white; border-radius: 8px;"
        )

        # Start intention session immediately
        self.start_intention_session(self._current_task)

        # Handle clarification completion in background
        if hasattr(self, "llm_client") and hasattr(
            self.llm_client, "clarification_manager"
        ):
            manager = self.llm_client.clarification_manager

            # Force complete the clarification
            manager.is_complete = True

            # Use current Q&A pairs as immediate clarification data
            # Even if empty, we'll proceed with original intention
            if manager.qa_pairs:
                # Use existing Q&A pairs to create basic clarification data
                clarification_text = f"{manager.stated_intention}\n\n"
                clarification_text += "\n\n".join(
                    [f"Q: {q}\nA: {a}" for q, a in manager.qa_pairs]
                )
                self.current_clarification_data = [clarification_text] * 10
                print(
                    f"[CLARIFICATION] Using {len(manager.qa_pairs)} Q&A pairs for immediate start"
                )
            else:
                # No Q&A pairs, use original intention
                self.current_clarification_data = [manager.stated_intention] * 10
                print(
                    "[CLARIFICATION] No Q&A pairs, using original intention for immediate start"
                )

            # Set clarification data in thread manager immediately
            if hasattr(self, "thread_manager"):
                self.thread_manager.set_clarification_data(
                    self.current_clarification_data
                )

            # Show completion message in background
            self.add_clarification_message(
                "Completing clarification with current responses...", is_user=False
            )

            # Request augmentation with current Q&A pairs (even if empty)
            # This will run in background and update clarification data later
            self.llm_client.request_augmentation()

            # Clear the auto-start flag since we're already starting
            self.auto_start_after_clarification = False
        else:
            # Fallback: No clarification manager, use original intention
            print("[CLARIFICATION] No clarification manager - using original intention")
            self.current_clarification_data = [self._current_task] * 10
            # Set clarification data in thread manager immediately
            if hasattr(self, "thread_manager"):
                self.thread_manager.set_clarification_data(
                    self.current_clarification_data
                )

        # Update message
        self.message_label.setText(CLICK_MESSAGE)

        print(
            "[CLARIFICATION] UI state updated immediately, clarification processing in background"
        )

    def _check_app_focus(self):
        """Check if user switched away from intention app"""
        if not self.focus_monitoring_enabled:
            return

        try:
            from ..utils.activity import get_frontmost_app

            current_app = get_frontmost_app()
            print(f"[FOCUS DEBUG] Current app: '{current_app}'")

            # Filter out browser URLs to get just the app name
            if " - " in current_app:
                current_app = current_app.split(" - ")[0]
                print(f"[FOCUS DEBUG] App name after filtering: '{current_app}'")

            # Use cached intention app name
            intention_app_name = self.current_intention_app_name

            # Fallback if cache is empty
            if not intention_app_name:
                from ..utils.activity import get_current_app_name

                intention_app_name = get_current_app_name()
                self.current_intention_app_name = intention_app_name
                print(
                    f"[FOCUS DEBUG] Fallback: got intention app name: '{intention_app_name}'"
                )

            print(f"[FOCUS DEBUG] Intention app name: '{intention_app_name}'")

            # Check if current app is our intention app (exact match or contains our app name)
            is_intention_app = (
                current_app.lower() == intention_app_name.lower()
                or intention_app_name.lower() in current_app.lower()
                or current_app.lower() in intention_app_name.lower()
            )

            # Additional check for common development apps if the current app name is generic
            if not is_intention_app and intention_app_name.lower() in [
                "python",
                "main",
            ]:
                intention_keywords = [
                    "python",
                    "pycharm",
                    "vscode",
                    "terminal",
                    "iterm",
                    "intention",
                    "intentional",
                    "dash",
                    "cursor",  # Added Cursor IDE
                    "code",  # Added VS Code variants
                    "atom",  # Added Atom editor
                    "sublime",  # Added Sublime Text
                    "vim",  # Added Vim
                    "emacs",  # Added Emacs
                    "jupyter",  # Added Jupyter
                    "spyder",  # Added Spyder
                    "qtcreator",  # Added Qt Creator
                    "qt",  # Added Qt apps
                    "pyqt",  # Added PyQt apps
                ]

                is_intention_app = any(
                    keyword in current_app.lower() for keyword in intention_keywords
                )
                print(
                    f"[FOCUS DEBUG] Fallback keyword check result: {is_intention_app}"
                )

            print(f"[FOCUS DEBUG] Is intention app: {is_intention_app}")
            if not is_intention_app:
                print(
                    f"[FOCUS DEBUG] Current app '{current_app}' doesn't match intention app '{intention_app_name}'"
                )

            if is_intention_app:
                # User is back in intention-related app
                # Focus popup feature removed - no notification timer

                # Reset state for fresh detection when user leaves again
                if self.app_switch_time is not None:
                    self.app_switch_time = None
                    print(
                        "[FOCUS DEBUG] Reset app switch time - ready for new detection"
                    )

                self.last_frontmost_app = current_app
                return

            # User is in a different app
            if self.last_frontmost_app != current_app:
                # App changed to non-intention app
                if self.app_switch_time is None:
                    self.app_switch_time = time.time()
                    print(f"[FOCUS] User switched to: {current_app}")
                    # Focus popup feature removed - no notification timer

            self.last_frontmost_app = current_app

        except Exception as e:
            print(f"[ERROR] Focus monitoring error: {e}")

    # Focus popup feature removed - no longer showing popups for app switches

    def start_focus_monitoring(self):
        """Start monitoring app focus when user clicks Start button"""
        if self.current_task:
            print(f"[FOCUS] Starting focus monitoring for task: '{self.current_task}'")
            print(f"[FOCUS] Check interval: {self.FOCUS_CHECK_INTERVAL/1000}s")

            # Get and cache current app name for focus monitoring
            if self.current_intention_app_name is None:
                from ..utils.activity import get_current_app_name

                self.current_intention_app_name = get_current_app_name()
                print(
                    f"[FOCUS] Cached intention app name: '{self.current_intention_app_name}'"
                )

            self.focus_monitoring_enabled = True
            from ..utils.activity import get_frontmost_app

            self.last_frontmost_app = get_frontmost_app()
            print(f"[FOCUS] Initial app: '{self.last_frontmost_app}'")
            self.focus_check_timer.start(self.FOCUS_CHECK_INTERVAL)
            print("[FOCUS] Monitoring timer started")
        else:
            print("[FOCUS] Cannot start monitoring - no current task set")

    def stop_focus_monitoring(self):
        """Stop monitoring app focus"""
        if self.focus_monitoring_enabled:
            print("[FOCUS] Stopping focus monitoring")
            self.focus_monitoring_enabled = False
            self.focus_check_timer.stop()
            self.app_switch_time = None
            self.last_frontmost_app = None
            # Focus popup feature removed

    def on_opacity_changed(self, value):
        """Handle opacity slider value change"""
        # Convert slider value (20-100) to opacity (0.2-1.0)
        opacity = value / 100.0

        # Apply opacity to the main window
        self.setWindowOpacity(opacity)

        # Store current opacity for other windows
        self.current_opacity = opacity

        # Apply to all currently visible windows managed by window_manager
        if hasattr(self, "window_manager") and self.window_manager:
            # Apply to all windows in window_manager
            for window_name, window in self.window_manager.windows.items():
                if window and window.isVisible():
                    window.setWindowOpacity(opacity)

        # Focus popup feature removed

        print(
            f"[UI] Opacity changed to {value}% ({opacity:.1f}) - applied to all windows"
        )

    def apply_current_opacity_to_window(self, window):
        """Apply current opacity setting to a specific window"""
        if window and hasattr(self, "current_opacity"):
            window.setWindowOpacity(self.current_opacity)
            print(f"[UI] Applied opacity {self.current_opacity:.1f} to new window")

    def _show_reminder_message(self, message):
        """Show the reminder message after hiding starting soon window"""
        # Hide starting soon window first, then show reminder message
        self.hide_starting_soon_window()
        self.show_llm_response_window(message, 0.0)  # 0.0 = focused

    def _close_focus_popup_on_dashboard_click(self):
        """Focus popup feature removed - this method is now a no-op"""
        pass

    def focusInEvent(self, event):
        """Handle focus in event when dashboard gets focus"""
        super().focusInEvent(event)
        self._close_focus_popup_on_dashboard_click()

    def showEvent(self, event):
        """Handle show event when dashboard becomes visible"""
        super().showEvent(event)
        # Small delay to ensure the window is fully shown before closing popup
        QTimer.singleShot(100, self._close_focus_popup_on_dashboard_click)

    def _install_event_filters(self):
        """Install event filters on all child widgets to catch clicks"""
        # Install on the dashboard itself
        self.installEventFilter(self)

        # Recursively install on all child widgets
        self._install_filter_recursive(self)

        print("[FOCUS] Event filters installed on all dashboard widgets")

    def _install_filter_recursive(self, widget):
        """Recursively install event filters on all child widgets"""
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, source, event):
        """Event filter to catch clicks on any child widget and close focus popup"""
        # Check if it's a mouse press event
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            # Focus popup feature removed
            pass

        # Continue with normal event processing
        return super().eventFilter(source, event)

    def refresh_ui_language(self):
        """Refresh all UI text when language changes"""
        print("[LANGUAGE] Refreshing dashboard UI language")

        # Update global constants
        global TYPE_MESSAGE, CLICK_MESSAGE
        TYPE_MESSAGE = get_text("type_message")
        CLICK_MESSAGE = get_text("click_message")

        # Update window title
        APP_TITLE = get_text("app_title_1")
        self.setWindowTitle(APP_TITLE)

        # Update drag bar text
        if hasattr(self, "drag_bar"):
            self.drag_bar.setText(APP_TITLE)

        # Update placeholder text
        if hasattr(self, "task_input"):
            self.task_input.setPlaceholderText(TYPE_MESSAGE)

        # Update button texts
        if hasattr(self, "set_button"):
            self.set_button.setText(get_text("set_button"))

        if hasattr(self, "start_button"):
            # Check current state and set appropriate text
            current_text = self.start_button.text()
            if current_text in ["Start", "시작"]:
                self.start_button.setText(get_text("start_button"))
            elif current_text in ["Stop", "중지"]:
                self.start_button.setText(get_text("stop_button"))

        # Update message labels
        if hasattr(self, "message_label") and self.message_label.text():
            # Only update if it contains the clickable message
            current_msg = self.message_label.text()
            if "reset intention" in current_msg or "재설정" in current_msg:
                self.message_label.setText(CLICK_MESSAGE)

        # Update instruction labels
        if hasattr(self, "instruction_label") and self.instruction_label:
            current_instruction = self.instruction_label.text()
            if (
                "start activity" in current_instruction
                or "시작하려면" in current_instruction
            ):
                self.instruction_label.setText(get_text("instruction_start"))
            elif (
                "finish activity" in current_instruction
                or "마무리" in current_instruction
            ):
                self.instruction_label.setText(get_text("instruction_finish"))

        # Daily rating display removed - no longer showing rating in history window

        # Update feedback messages if feedback window is visible
        if (
            hasattr(self, "llm_response_window")
            and self.llm_response_window
            and self.llm_response_window.isVisible()
        ):
            self._update_feedback_message()

        # Update loading animation if currently active
        if self.loading_timer.isActive() and self.loading_message_widget:
            loading_text = get_text("loading")
            self.loading_message_widget.setText(
                f"{loading_text}{'.' * self.loading_dots}"
            )

        # Update history window title if visible
        if hasattr(self, "window_manager") and self.window_manager:
            history_window = self.window_manager.windows.get("history")
            if history_window:
                history_title = history_window.findChild(QLabel, "historyTitle")
                if history_title:
                    history_title.setText(get_text("todays_intentions"))

            # Update starting soon window label if visible
            starting_soon_window = self.window_manager.windows.get("starting_soon")
            if starting_soon_window:
                starting_label = starting_soon_window.findChild(QLabel, "startingLabel")
                if starting_label:
                    starting_label.setText(get_text("starting_soon"))

            # Update clarification window elements if visible
            clarification_window = self.window_manager.windows.get("clarification")
            if clarification_window:
                clarification_title = clarification_window.findChild(
                    QLabel, "clarificationTitle"
                )
                if clarification_title:
                    clarification_title.setText(get_text("clarification_title").upper())

        # Update clarification input and send button if they exist
        if hasattr(self, "clarification_input") and self.clarification_input:
            self.clarification_input.setPlaceholderText(
                get_text("clarification_placeholder")
            )

        if (
            hasattr(self, "clarification_send_button")
            and self.clarification_send_button
        ):
            self.clarification_send_button.setText(get_text("send_button"))

        # Update rating window if it exists
        if hasattr(self, "window_manager") and self.window_manager:
            rating_window = self.window_manager.windows.get("rating")
            if rating_window:
                # Update rating window title
                rating_title = rating_window.findChild(QLabel)
                if rating_title and rating_title.objectName() == "ratingTitle":
                    rating_title.setText(get_text("rating_question"))

                # Update rating widget text
                if hasattr(self, "progress_bar") and hasattr(
                    self.progress_bar, "refresh_language"
                ):
                    self.progress_bar.refresh_language()

        print("[LANGUAGE] Dashboard UI language refresh complete")

    def get_dashboard_position(self):
        """Get simple x,y position of dashboard for image analysis"""
        pos = self.pos()
        return {"x": pos.x(), "y": pos.y()}

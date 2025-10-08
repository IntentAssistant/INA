"""
Window management functionality for the dashboard
Handles creation, positioning, and animation of popup windows
"""

import sys
import objc
from ctypes import c_void_p
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QGraphicsOpacityEffect,
    QScrollArea,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
)
from PyQt6.QtGui import QFont
from AppKit import NSWindowSharingNone

# Animation Constants
ANIMATION_SHOW_DURATION = 300  # Show animation duration in ms
ANIMATION_HIDE_DURATION = 200  # Hide animation duration in ms
ANIMATION_SLIDE_OFFSET = 20  # Slide animation offset in pixels

# UI Constants
DASHBOARD_WIDTH = 400  # Dashboard width
INPUT_HEIGHT = 40  # Height for input fields and buttons

HISTORY_TITLE_TEXT = "Today's Intentions"
CLARIFICATION_TITLE_TEXT = "Clarification"
CLARIFICATION_PLACEHOLDER_TEXT = "Type your response..."
SEND_BUTTON_TEXT = "Send"
STARTING_SOON_TEXT = "Starting soon..."


class WindowManager:
    """Manages popup windows for the dashboard"""

    def __init__(self, parent_dashboard):
        self.dashboard = parent_dashboard
        self.windows = {}
        self.opacity_effects = {}
        self.animation_groups = {}

    def create_all_windows(self):
        """Create all popup windows"""
        self.create_history_window()
        self.create_clarification_window()
        self.create_starting_soon_window()
        self.create_llm_response_window()
        self.create_feedback_window()

    def get_window_flags(self):
        """Get window flags based on float on top setting"""
        from ..config.api_config import get_api_config_manager

        api_manager = get_api_config_manager()
        current_float_on_top = api_manager.get_float_on_top()

        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
        if current_float_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        return flags

    def create_history_window(self):
        """Create the history window that appears below the main dashboard"""
        # Create history window as separate widget
        history_window = QWidget()
        history_window.setWindowFlags(self.get_window_flags())
        history_window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        history_window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        history_window.setFixedSize(DASHBOARD_WIDTH, 200)

        # Create container widget for styling
        history_container = QWidget(history_window)
        history_container.setObjectName("historyContainer")
        history_container.setGeometry(0, 0, DASHBOARD_WIDTH, 200)

        # Layout for history window
        history_layout = QVBoxLayout(history_container)
        history_layout.setContentsMargins(12, 4, 12, 8)
        history_layout.setSpacing(2)

        # Title
        history_title = QLabel(HISTORY_TITLE_TEXT)
        history_title.setObjectName("historyTitle")
        history_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_layout.addWidget(history_title)

        # Focus percentage label removed - no longer showing daily rating

        # History timeline (will be set from dashboard)
        self.dashboard.history_timeline.setObjectName("historyTimeline")
        self.dashboard.history_timeline.dashboard = self.dashboard
        history_layout.addWidget(self.dashboard.history_timeline)

        # Apply styling
        history_window.setStyleSheet(
            """
            #historyContainer {
                background-color: #202020;
                border-radius: 12px;
            }
            #historyTitle {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            #focusPercentageLabel {
                color: #007AFF;
                font-size: 13px;
                font-weight: 600;
                padding: 2px 0px;
                margin: 0px;
            }
            #historyTimeline {
                background-color: transparent;
                border: none;
            }
        """
        )

        # Set up opacity effect for animation
        opacity_effect = QGraphicsOpacityEffect()
        history_window.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(0)  # Start invisible

        # Store references
        self.windows["history"] = history_window
        self.opacity_effects["history"] = opacity_effect

        # Drag functionality removed - only dashboard should be draggable

        # Hide initially
        history_window.hide()

    def create_clarification_window(self):
        """Create clarification window for LLM chat"""
        clarification_window = QWidget()
        clarification_window.setWindowFlags(self.get_window_flags())
        clarification_window.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        clarification_window.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating, True
        )
        clarification_window.setFixedSize(DASHBOARD_WIDTH, 300)

        # Create container widget for styling
        clarification_container = QWidget(clarification_window)
        clarification_container.setObjectName("clarificationContainer")
        clarification_container.setGeometry(0, 0, DASHBOARD_WIDTH, 300)

        # Layout for clarification window
        clarification_layout = QVBoxLayout(clarification_container)
        clarification_layout.setContentsMargins(12, 8, 12, 12)
        clarification_layout.setSpacing(8)

        # Title
        clarification_title = QLabel(CLARIFICATION_TITLE_TEXT.upper())
        clarification_title.setObjectName("clarificationTitle")
        clarification_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clarification_layout.addWidget(clarification_title)

        # Chat area (scrollable)
        chat_scroll = QScrollArea()
        chat_scroll.setObjectName("chatScroll")
        chat_scroll.setWidgetResizable(True)
        chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Chat container
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(8)
        chat_layout.addStretch()  # Push messages to bottom initially

        chat_scroll.setWidget(chat_container)
        clarification_layout.addWidget(chat_scroll)

        # Input area
        input_area = QWidget()
        input_layout = QHBoxLayout(input_area)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        # Input field
        clarification_input = QLineEdit()
        clarification_input.setObjectName("clarificationInput")
        clarification_input.setPlaceholderText(CLARIFICATION_PLACEHOLDER_TEXT)
        clarification_input.setFixedHeight(INPUT_HEIGHT)
        clarification_input.returnPressed.connect(
            self.dashboard.send_clarification_message
        )

        # Send button
        clarification_send_button = QPushButton(SEND_BUTTON_TEXT)
        clarification_send_button.setObjectName("clarificationSendButton")
        clarification_send_button.setFixedWidth(60)
        clarification_send_button.setFixedHeight(INPUT_HEIGHT)
        clarification_send_button.clicked.connect(
            self.dashboard.send_clarification_message
        )

        input_layout.addWidget(clarification_input)
        input_layout.addWidget(clarification_send_button)
        clarification_layout.addWidget(input_area)

        # Apply styling
        clarification_window.setStyleSheet(
            """
            #clarificationContainer {
                background-color: #202020;
                border-radius: 12px;
            }
            #clarificationTitle {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 0px;
                margin: 0px;
            }
            #chatScroll {
                background-color: #202020;
                border: none;
            }
            QWidget {
                background-color: #202020;
            }
            #clarificationInput {
                background-color: #2D2D2D;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: white;
            }
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
            QScrollBar:vertical {
                background-color: #3C3C3C;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: #666666;
                border-radius: 3px;
                min-height: 20px;
            }
        """
        )

        # Set up opacity effect for animation
        opacity_effect = QGraphicsOpacityEffect()
        clarification_window.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(0)

        # Store references
        self.windows["clarification"] = clarification_window
        self.opacity_effects["clarification"] = opacity_effect

        # Store UI elements for dashboard access
        self.dashboard.clarification_window = clarification_window
        self.dashboard.clarification_input = clarification_input
        self.dashboard.clarification_send_button = clarification_send_button
        self.dashboard.chat_scroll = chat_scroll
        self.dashboard.chat_container = chat_container
        self.dashboard.chat_layout = chat_layout

        # Drag functionality removed - only dashboard should be draggable

        # Hide initially
        clarification_window.hide()

    def create_starting_soon_window(self):
        """Create starting soon window"""
        starting_soon_window = QWidget()
        starting_soon_window.setWindowFlags(self.get_window_flags())
        starting_soon_window.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        starting_soon_window.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating, True
        )
        starting_soon_window.setFixedSize(DASHBOARD_WIDTH, 60)

        # Create container widget for styling
        starting_container = QWidget(starting_soon_window)
        starting_container.setObjectName("startingContainer")
        starting_container.setGeometry(0, 0, DASHBOARD_WIDTH, 60)

        # Layout for starting soon window
        starting_layout = QVBoxLayout(starting_container)
        starting_layout.setContentsMargins(12, 8, 12, 8)
        starting_layout.setSpacing(0)

        # Starting soon label
        starting_label = QLabel(STARTING_SOON_TEXT)
        starting_label.setObjectName("startingLabel")
        starting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        starting_layout.addWidget(starting_label)

        # Apply styling
        starting_soon_window.setStyleSheet(
            """
            #startingContainer {
                background-color: #202020;
                border-radius: 12px;
            }
            #startingLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 0px;
                margin: 0px;
            }
        """
        )

        # Store references
        self.windows["starting_soon"] = starting_soon_window
        self.dashboard.starting_soon_window = starting_soon_window

        # Drag functionality removed - only dashboard should be draggable

        # Hide initially
        starting_soon_window.hide()

    def create_llm_response_window(self):
        """Create LLM response window without feedback buttons"""
        llm_response_window = QWidget()
        llm_response_window.setWindowFlags(self.get_window_flags())
        llm_response_window.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        llm_response_window.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating, True
        )
        llm_response_window.setFixedSize(DASHBOARD_WIDTH, 70)  # Default 2-line height

        # Create container widget for styling
        llm_container = QWidget(llm_response_window)
        llm_container.setObjectName("llmContainer")
        llm_container.setGeometry(0, 0, DASHBOARD_WIDTH, 70)

        # Main layout for LLM response window
        main_llm_layout = QHBoxLayout(llm_container)
        main_llm_layout.setContentsMargins(12, 12, 12, 12)
        main_llm_layout.setSpacing(8)

        # LLM response label (takes all space)
        llm_response_label = QLabel()
        llm_response_label.setObjectName("llmResponseLabel")
        llm_response_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        llm_response_label.setWordWrap(True)
        main_llm_layout.addWidget(llm_response_label, 1)

        # Apply styling
        llm_response_window.setStyleSheet(
            """
            #llmContainer {
                background-color: #202020;
                border-radius: 12px;
            }
            #llmContainer[status="focused"] {
                background-color: #2ecc71;
            }
            #llmContainer[status="ambiguous"] {
                background-color: #f39c12; 
            }
            #llmContainer[status="distracted"] {
                background-color: #e74c3c;
            }
            #llmResponseLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 8px;
                margin: 0px;
                line-height: 1.3;
            }
        """
        )

        # Add mouse events to LLM container for feedback window control
        llm_container.enterEvent = self.dashboard.llm_response_enter_event
        llm_container.leaveEvent = self.dashboard.llm_response_leave_event

        # Store references
        self.windows["llm_response"] = llm_response_window
        self.dashboard.llm_response_window = llm_response_window
        self.dashboard.llm_response_label = llm_response_label

        # Drag functionality removed - only dashboard should be draggable

        # Hide initially
        llm_response_window.hide()

    def adjust_llm_response_window_height(self, message):
        """Dynamically adjust LLM response window height based on message length"""
        llm_response_window = self.windows.get("llm_response")
        if not llm_response_window:
            return

        # Calculate required height based on message
        from PyQt6.QtGui import QFontMetrics
        from PyQt6.QtCore import QRect

        # Get the label to measure text
        llm_response_label = self.dashboard.llm_response_label
        font = llm_response_label.font()
        font_metrics = QFontMetrics(font)

        # Calculate text width (window width minus margins and padding)
        text_width = DASHBOARD_WIDTH - 24 - 16  # margins (12*2) + padding (8*2)

        # Calculate required height for the text
        text_rect = font_metrics.boundingRect(
            QRect(0, 0, text_width, 0), Qt.TextFlag.TextWordWrap, message
        )

        # Calculate total window height (text height + padding + margins)
        text_height = text_rect.height()
        total_height = text_height + 24 + 8  # margins (12*2) + padding (4*2)

        # Set minimum height (2 lines) and maximum height (4 lines)
        min_height = 70
        max_height = 130
        final_height = max(min_height, min(total_height, max_height))

        # Update window and container sizes
        llm_response_window.setFixedSize(DASHBOARD_WIDTH, final_height)

        llm_container = llm_response_window.findChild(QWidget, "llmContainer")
        if llm_container:
            llm_container.setGeometry(0, 0, DASHBOARD_WIDTH, final_height)

        print(
            f"[WINDOW] Adjusted LLM response height: {final_height}px for message length: {len(message)}"
        )

    def create_feedback_window(self):
        """Create separate feedback window with O/X buttons"""
        feedback_window = QWidget()
        feedback_window.setWindowFlags(self.get_window_flags())
        feedback_window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        feedback_window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        feedback_window.setFixedSize(400, 90)  # Start small

        # Create container widget for styling
        feedback_container = QWidget(feedback_window)
        feedback_container.setObjectName("feedbackContainer")
        feedback_container.setGeometry(0, 0, 400, 90)  # Start small

        # Main layout for feedback window
        feedback_layout = QVBoxLayout(feedback_container)
        feedback_layout.setContentsMargins(8, 6, 8, 6)  # Reduced margins from 12,8,12,8
        feedback_layout.setSpacing(6)  # Reduced spacing from 8

        # Question label
        question_label = QLabel("Is the notification correct?")
        question_label.setObjectName("questionLabel")
        question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        feedback_layout.addWidget(question_label)

        # Buttons container
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)  # Reduced spacing between buttons from 12

        # Good feedback button (O mark) - aligned to left
        good_button = QPushButton("✅")
        good_button.setObjectName("goodFeedbackButton")
        good_button.setFixedSize(185, 50)  # Much bigger buttons
        good_button.clicked.connect(
            lambda: self.dashboard.handle_feedback_click("good", good_button)
        )
        buttons_layout.addWidget(good_button)

        # Add stretch between buttons to push X button to the right
        buttons_layout.addStretch()

        # Bad feedback button (X mark) - aligned to right
        bad_button = QPushButton("❌")
        bad_button.setObjectName("badFeedbackButton")
        bad_button.setFixedSize(185, 50)  # Much bigger buttons
        bad_button.clicked.connect(
            lambda: self.dashboard.handle_feedback_click("bad", bad_button)
        )
        buttons_layout.addWidget(bad_button)

        feedback_layout.addWidget(buttons_container)

        # Text input feature removed - feedback is now Good/Bad only

        # Mouse events for showing/hiding feedback window
        feedback_container.enterEvent = (
            lambda event: self.dashboard.feedback_window_enter_event(event)
        )
        feedback_container.leaveEvent = (
            lambda event: self.dashboard.feedback_window_leave_event(event)
        )

        # Apply styling
        feedback_window.setStyleSheet(
            """
            #feedbackContainer {
                background-color: #202020;
                border-radius: 12px;
            }
            #questionLabel {
                color: white;
                font-size: 14px;
                font-weight: 500;
                padding: 0px;
                margin: 0px;
            }
            #goodFeedbackButton {
                background-color: #202020;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border: none;
                border-radius: 12px;
            }
            #goodFeedbackButton:hover {
                background-color: #303030;
            }
            #badFeedbackButton {
                background-color: #202020;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border: none;
                border-radius: 12px;
            }
            #badFeedbackButton:hover {
                background-color: #303030;
            }
            #textQuestionLabel {
                color: white;
                font-size: 13px;
                font-weight: 500;
                padding: 0px;
                margin: 0px;
            }
            #textInputField {
                background-color: #2D2D2D;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                color: white;
            }
            #textInputField:focus {
                border: 1px solid #007AFF;
            }

            #submitButton {
                background-color: #007AFF;
                color: white;
                font-size: 12px;
                font-weight: 500;
                border: none;
                border-radius: 6px;
            }
            #submitButton:hover {
                background-color: #0069D9;
            }
        """
        )

        # Set up opacity effect for animation
        opacity_effect = QGraphicsOpacityEffect()
        feedback_window.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(0)

        # Store references
        self.windows["feedback"] = feedback_window
        self.opacity_effects["feedback"] = opacity_effect
        self.dashboard.feedback_window = feedback_window
        self.dashboard.good_feedback_button = good_button
        self.dashboard.bad_feedback_button = bad_button
        # Text input references removed

        # Drag functionality removed - only dashboard should be draggable

        # Hide initially
        feedback_window.hide()

    def show_window_with_animation(self, window_name):
        """Show window with fade-in and slide-down animation"""
        print(f"[WINDOW] Attempting to show window: {window_name}")

        if window_name not in self.windows:
            print(f"[WINDOW] ERROR: Window '{window_name}' not found in windows dict")
            print(f"[WINDOW] Available windows: {list(self.windows.keys())}")
            return

        window = self.windows[window_name]
        if window.isVisible():
            print(f"[WINDOW] Window '{window_name}' is already visible")
            return

        print(f"[WINDOW] Showing window '{window_name}'...")

        # Position the window below the main dashboard
        self.update_window_position(window_name)
        print(f"[WINDOW] Window '{window_name}' positioned at: {window.pos()}")

        # Store the final position for animation
        final_pos = window.pos()

        # Different slide offsets for different windows
        if window_name == "feedback":
            # Feedback window slides down less to avoid covering LLM response
            slide_offset = 5  # Much smaller offset for feedback window
        else:
            slide_offset = ANIMATION_SLIDE_OFFSET  # Normal offset for other windows

        # Start position (slightly above final position for slide effect)
        start_y = final_pos.y() - slide_offset
        window.move(final_pos.x(), start_y)

        # Update window flags to match current settings before showing
        # This ensures the window respects any setting changes made while it was hidden
        current_flags = self.get_window_flags()
        window.setWindowFlags(current_flags)

        # Show the window
        window.show()

        # Apply dashboard's current opacity to the window
        if hasattr(self.dashboard, "current_opacity"):
            window.setWindowOpacity(self.dashboard.current_opacity)
            print(
                f"[WINDOW] Applied opacity {self.dashboard.current_opacity:.1f} to '{window_name}'"
            )

        print(
            f"[WINDOW] Window '{window_name}' show() called. Visible: {window.isVisible()}"
        )

        # Force window to front using macOS native API (for app bundles)
        if sys.platform == "darwin":
            try:
                import objc
                from ctypes import c_void_p
                from AppKit import NSApp

                # Get the native window and force it to front
                native_view = objc.objc_object(c_void_p=int(window.winId()))
                ns_window = native_view.window()

                # Make window key and order front
                ns_window.makeKeyAndOrderFront_(None)

                # Also activate the application to ensure windows come to front
                NSApp.activateIgnoringOtherApps_(True)

                print(
                    f"[WINDOW] Window '{window_name}' forced to front using native API"
                )
            except Exception as e:
                print(f"[WINDOW] Failed to force window to front: {e}")
                # Fallback to Qt methods
                window.raise_()
                window.activateWindow()

        # Create animation group for parallel animations
        animation_group = QParallelAnimationGroup()

        # Create opacity animation (fade in) if opacity effect exists
        if window_name in self.opacity_effects:
            print(f"[WINDOW] Setting up opacity animation for '{window_name}'")
            opacity_animation = QPropertyAnimation(
                self.opacity_effects[window_name], b"opacity"
            )

            # Faster animation for feedback window
            if window_name == "feedback":
                opacity_animation.setDuration(150)  # Faster fade for feedback
            else:
                opacity_animation.setDuration(ANIMATION_SHOW_DURATION)

            opacity_animation.setStartValue(0.0)
            opacity_animation.setEndValue(1.0)
            opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation_group.addAnimation(opacity_animation)
        else:
            print(f"[WINDOW] No opacity effect found for '{window_name}'")

        # Create position animation (slide down)
        position_animation = QPropertyAnimation(window, b"pos")

        # Faster animation for feedback window
        if window_name == "feedback":
            position_animation.setDuration(150)  # Faster slide for feedback
        else:
            position_animation.setDuration(ANIMATION_SHOW_DURATION)

        position_animation.setStartValue(window.pos())
        position_animation.setEndValue(final_pos)
        position_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation_group.addAnimation(position_animation)

        # Store animation group
        self.animation_groups[f"{window_name}_show"] = animation_group

        # Start animation group
        animation_group.start()
        print(
            f"[WINDOW] Animation started for '{window_name}'. Final position: {final_pos}"
        )

        # Add callback to check animation completion
        animation_group.finished.connect(
            lambda: print(
                f"[WINDOW] Animation completed for '{window_name}'. Visible: {window.isVisible()}"
            )
        )

        print(f"[WINDOW] Window '{window_name}' setup complete")

    def hide_window_with_animation(self, window_name):
        """Hide window with fade-out and slide-up animation"""
        if window_name not in self.windows:
            return

        window = self.windows[window_name]
        if not window.isVisible():
            return

        # Store current position and calculate end position
        current_pos = window.pos()

        # Different slide offsets for different windows
        if window_name == "feedback":
            slide_offset = 5  # Smaller offset for feedback window
            animation_duration = 100  # Faster hide for feedback
        else:
            slide_offset = ANIMATION_SLIDE_OFFSET
            animation_duration = ANIMATION_HIDE_DURATION

        end_y = current_pos.y() - slide_offset

        # Create animation group for parallel animations
        animation_group = QParallelAnimationGroup()

        # Create opacity animation (fade out) if opacity effect exists
        if window_name in self.opacity_effects:
            opacity_animation = QPropertyAnimation(
                self.opacity_effects[window_name], b"opacity"
            )
            opacity_animation.setDuration(animation_duration)
            opacity_animation.setStartValue(1.0)
            opacity_animation.setEndValue(0.0)
            opacity_animation.setEasingCurve(QEasingCurve.Type.InCubic)
            animation_group.addAnimation(opacity_animation)

        # Create position animation (slide up)
        position_animation = QPropertyAnimation(window, b"pos")
        position_animation.setDuration(animation_duration)
        position_animation.setStartValue(current_pos)
        position_animation.setEndValue(QPoint(current_pos.x(), end_y))
        position_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        animation_group.addAnimation(position_animation)

        # Hide window when animation finishes
        animation_group.finished.connect(lambda: window.hide())

        # Store animation group
        self.animation_groups[f"{window_name}_hide"] = animation_group

        # Start animation group
        animation_group.start()

    def update_window_position(self, window_name):
        """Update window position to follow main dashboard"""
        if window_name not in self.windows:
            return

        window = self.windows[window_name]

        # Position the window below the main dashboard with 5px gap
        main_pos = self.dashboard.pos()
        main_size = self.dashboard.size()
        window_x = main_pos.x()

        if window_name == "feedback":
            # Position feedback window below LLM response window
            if (
                "llm_response" in self.windows
                and self.windows["llm_response"].isVisible()
            ):
                llm_pos = self.windows["llm_response"].pos()
                llm_size = self.windows["llm_response"].size()
                window_y = llm_pos.y() + llm_size.height() + 5
            else:
                # If LLM response is not visible, position below main dashboard
                window_y = (
                    main_pos.y() + main_size.height() + 70
                )  # 5 + 60 (LLM response height) + 5
        else:
            window_y = main_pos.y() + main_size.height() + 5

        window.move(window_x, window_y)

    def update_all_window_positions(self):
        """Update all window positions when dashboard moves"""
        for window_name in self.windows:
            if self.windows[window_name].isVisible():
                self.update_window_position(window_name)

    def make_windows_secure(self, exclude_from_capture=True):
        """Make all windows secure for screen capture exclusion"""
        if sys.platform == "darwin" and exclude_from_capture:
            try:
                for window_name, window in self.windows.items():
                    if window:
                        native_view = objc.objc_object(c_void_p=int(window.winId()))
                        ns_window = native_view.window()
                        ns_window.setSharingType_(NSWindowSharingNone)
                print("[DASHBOARD] All windows protected from screen capture")
            except Exception as e:
                print(f"[ERROR] Failed to secure windows: {e}")
        elif sys.platform == "darwin" and not exclude_from_capture:
            print(
                "[DASHBOARD] Screen capture protection disabled for popup windows (debug mode)"
            )
        else:
            print(
                "[DASHBOARD] Screen capture protection not available on this platform"
            )

    def show_window(self, window_name):
        """Show window without animation"""
        if window_name in self.windows:
            self.update_window_position(window_name)
            self.windows[window_name].show()

            # Apply dashboard's current opacity to the window
            if hasattr(self.dashboard, "current_opacity"):
                self.windows[window_name].setWindowOpacity(
                    self.dashboard.current_opacity
                )
                print(
                    f"[WINDOW] Applied opacity {self.dashboard.current_opacity:.1f} to '{window_name}' (no animation)"
                )

    def hide_window(self, window_name):
        """Hide window without animation"""
        if window_name in self.windows:
            self.windows[window_name].hide()

    def add_drag_functionality(self, window):
        """Add mouse drag functionality to a window"""
        # Initialize drag state
        window.oldPos = None

        # Store original mouse event handlers if they exist
        original_mouse_press = getattr(window, "mousePressEvent", None)
        original_mouse_move = getattr(window, "mouseMoveEvent", None)
        original_mouse_release = getattr(window, "mouseReleaseEvent", None)

        def mousePressEvent(event):
            """Handle mouse press to start window dragging"""
            if event.button() == Qt.MouseButton.LeftButton:
                window.oldPos = event.globalPosition().toPoint()
            # Call original handler if it exists
            if original_mouse_press:
                original_mouse_press(event)

        def mouseMoveEvent(event):
            """Handle mouse movement to move window"""
            if hasattr(window, "oldPos") and window.oldPos:
                delta = event.globalPosition().toPoint() - window.oldPos
                window.move(window.pos() + delta)
                window.oldPos = event.globalPosition().toPoint()
            # Call original handler if it exists
            if original_mouse_move:
                original_mouse_move(event)

        def mouseReleaseEvent(event):
            """Handle mouse release to end window dragging"""
            if event.button() == Qt.MouseButton.LeftButton:
                window.oldPos = None
            # Call original handler if it exists
            if original_mouse_release:
                original_mouse_release(event)

        # Bind the new handlers to the window
        window.mousePressEvent = mousePressEvent
        window.mouseMoveEvent = mouseMoveEvent
        window.mouseReleaseEvent = mouseReleaseEvent

    def cleanup_all_windows(self):
        """Clean up all managed windows to prevent memory leaks"""
        try:
            print("[WINDOW_MANAGER] Cleaning up all windows...")

            for window_name, window in list(self.windows.items()):
                if window:
                    try:
                        print(f"[WINDOW_MANAGER] Cleaning up {window_name} window")

                        # Stop any running animations
                        if (
                            hasattr(self, "animations")
                            and window_name in self.animations
                        ):
                            animation = self.animations[window_name]
                            if animation:
                                animation.stop()
                                animation.deleteLater()

                        # Close and delete the window
                        window.close()
                        window.deleteLater()

                    except Exception as e:
                        print(f"[WINDOW_MANAGER] Error cleaning up {window_name}: {e}")

            # Clear the windows dictionary
            self.windows.clear()

            # Clean up animations dictionary if it exists
            if hasattr(self, "animations"):
                self.animations.clear()

            print("[WINDOW_MANAGER] All windows cleaned up")

        except Exception as e:
            print(f"[WINDOW_MANAGER] Error in cleanup: {e}")

    def set_all_windows_float_on_top(self, enabled: bool):
        """Update float on top setting for all windows"""
        # Update flags for all existing windows
        # Note: These keys match the actual keys used in self.windows dictionary
        window_names = [
            "history",
            "clarification",
            "starting_soon",
            "llm_response",
            "feedback",
        ]

        for window_name in window_names:
            if window_name in self.windows:
                window = self.windows[window_name]
                if window:
                    # Get current visibility state and geometry
                    was_visible = window.isVisible()
                    current_geometry = window.geometry()

                    # Get current flags and update
                    current_flags = window.windowFlags()

                    # Remove or add WindowStaysOnTopHint based on enabled
                    if enabled:
                        new_flags = current_flags | Qt.WindowType.WindowStaysOnTopHint
                    else:
                        new_flags = current_flags & ~Qt.WindowType.WindowStaysOnTopHint

                    # Apply new flags
                    window.setWindowFlags(new_flags)

                    # Restore geometry (setWindowFlags can reset position)
                    window.setGeometry(current_geometry)

                    # Re-show if was visible (required after setWindowFlags)
                    if was_visible:
                        window.show()

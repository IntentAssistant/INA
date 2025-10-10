"""Unified Settings Dialog - Cursor-style settings UI"""

import os
import subprocess
import sys

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QGroupBox,
    QMessageBox,
    QCheckBox,
    QSpinBox,
    QApplication,
    QRadioButton,
    QButtonGroup,
)
from PyQt6.QtCore import Qt, QSize, QRect, QTimer, QUrl
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QDesktopServices

from ..config.api_config import (
    LLMProvider,
    get_api_config_manager,
    API_CONFIG,
)


class DisplayHighlightWindow(QWidget):
    """Transparent window that shows a green border around a display"""

    def __init__(self, screen_geometry: QRect):
        super().__init__()
        # Set window properties for overlay
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Set geometry to match the screen
        self.setGeometry(screen_geometry)

        # Border properties
        self.border_width = 8
        self.border_color = QColor(0, 255, 0)  # Green

    def paintEvent(self, event):
        """Draw the green border"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Create pen for border
        pen = QPen(self.border_color)
        pen.setWidth(self.border_width)
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)

        # Draw rectangle border (inset by half border width)
        offset = self.border_width // 2
        rect = self.rect().adjusted(offset, offset, -offset, -offset)
        painter.drawRect(rect)


class UnifiedSettingsDialog(QDialog):
    """Unified settings dialog with sidebar navigation"""

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(900, 600)
        self.highlight_windows = []  # Store display highlight overlays
        self.app = app  # Store reference to main app for real-time updates
        self.setup_ui()

    def setup_ui(self):
        """Setup the unified settings UI"""
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left sidebar - Category list
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(200)
        self.category_list.setSpacing(2)

        # Add categories
        categories = ["General", "Models", "Display", "Notifications"]
        for category in categories:
            item = QListWidgetItem(category)
            item.setSizeHint(QSize(200, 40))
            self.category_list.addItem(item)

        self.category_list.setCurrentRow(0)
        self.category_list.currentRowChanged.connect(self.on_category_changed)

        main_layout.addWidget(self.category_list)

        # Right side - Content pages
        self.content_stack = QStackedWidget()

        # Create content pages
        self.general_page = self.create_general_page()
        self.models_page = self.create_models_page()
        self.display_page = self.create_display_page()
        self.notifications_page = self.create_notifications_page()

        self.content_stack.addWidget(self.general_page)
        self.content_stack.addWidget(self.models_page)
        self.content_stack.addWidget(self.display_page)
        self.content_stack.addWidget(self.notifications_page)

        main_layout.addWidget(self.content_stack, 1)

        # Apply styling
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QListWidget {
                background-color: #252526;
                border: none;
                border-right: 1px solid #3e3e42;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 15px;
                color: #cccccc;
            }
            QListWidget::item:selected {
                background-color: #37373d;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
            QLabel {
                color: #cccccc;
            }
            QGroupBox {
                color: #cccccc;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 8px;
            }
            QComboBox:hover {
                border: 1px solid #007acc;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #cccccc;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                selection-background-color: #007acc;
                selection-color: #ffffff;
                border: 1px solid #3e3e42;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #2a2d2e;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0d5a8f;
            }
            QCheckBox {
                color: #cccccc;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                background-color: #3c3c3c;
            }
            QCheckBox::indicator:checked {
                background-color: #007acc;
                border-color: #007acc;
            }
            QRadioButton {
                color: #cccccc;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3e3e42;
                border-radius: 9px;
                background-color: #3c3c3c;
            }
            QRadioButton::indicator:checked {
                background-color: #007acc;
                border-color: #007acc;
            }
            QRadioButton::indicator:checked:after {
                width: 10px;
                height: 10px;
                border-radius: 5px;
                background-color: white;
            }
            QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 5px;
            }
        """
        )

    def create_general_page(self):
        """Create General settings page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Page title
        title = QLabel("General")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        # App info group
        info_group = QGroupBox("Application Information")
        info_layout = QVBoxLayout()

        from ..config.constants import APP_VERSION

        app_name_label = QLabel("App Name: INA (Intent Assistant)")
        app_version_label = QLabel(f"Version: {APP_VERSION}")

        info_layout.addWidget(app_name_label)
        info_layout.addWidget(app_version_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Window behavior group
        window_group = QGroupBox("Window Behavior")
        window_layout = QVBoxLayout()

        self.api_manager = get_api_config_manager()
        self.float_on_top_checkbox = QCheckBox("Float on top")
        self.float_on_top_checkbox.setChecked(self.api_manager.get_float_on_top())
        self.float_on_top_checkbox.stateChanged.connect(self.on_float_on_top_changed)
        window_layout.addWidget(self.float_on_top_checkbox)

        self.exclude_capture_checkbox = QCheckBox("Hide dashboard from screen recordings (macOS)")
        self.exclude_capture_checkbox.setChecked(
            self.api_manager.get_exclude_dashboard_from_capture()
        )
        self.exclude_capture_checkbox.stateChanged.connect(
            self.on_exclude_capture_changed
        )
        window_layout.addWidget(self.exclude_capture_checkbox)

        float_info = QLabel(
            "When enabled, the dashboard will always stay on top of other windows"
        )
        float_info.setStyleSheet("color: #888888;")
        window_layout.addWidget(float_info)

        capture_info = QLabel(
            "If checked, the dashboard and its popups are excluded from macOS screen capture."
        )
        capture_info.setStyleSheet("color: #888888;")
        window_layout.addWidget(capture_info)

        window_group.setLayout(window_layout)
        layout.addWidget(window_group)

        layout.addStretch()
        return page

    def create_models_page(self):
        """Create Models settings page (includes API configuration)"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Page title
        title = QLabel("Models")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        # API Configuration
        api_manager = get_api_config_manager()

        # Get current settings
        current_provider = api_manager.get_provider()
        current_api_key = (
            api_manager.get_api_key(current_provider) if current_provider else ""
        )
        current_model = (
            api_manager.get_model(current_provider) if current_provider else None
        )

        # Provider selection
        provider_group = QGroupBox("AI Provider")
        provider_layout = QVBoxLayout()

        provider_label = QLabel("Select your AI model provider:")
        provider_layout.addWidget(provider_label)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("OpenAI GPT", LLMProvider.OPENAI)
        self.provider_combo.addItem("Google Gemini", LLMProvider.GEMINI)

        # Set current provider
        if current_provider == LLMProvider.OPENAI:
            self.provider_combo.setCurrentIndex(0)
        else:
            self.provider_combo.setCurrentIndex(1)

        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # API Key input
        api_key_group = QGroupBox("API Key")
        api_key_layout = QVBoxLayout()

        api_key_label = QLabel("Enter your API key:")
        api_key_layout.addWidget(api_key_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Your API key")
        self.api_key_input.setText(current_api_key)
        api_key_layout.addWidget(self.api_key_input)

        # Show/Hide password button
        show_password_checkbox = QCheckBox("Show API Key")
        show_password_checkbox.toggled.connect(
            lambda checked: self.api_key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        api_key_layout.addWidget(show_password_checkbox)

        # Test API key button
        test_button = QPushButton("Test API Key")
        test_button.clicked.connect(self.test_api_key)
        test_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2d7d2d;
                color: white;
            }
            QPushButton:hover {
                background-color: #3a9d3a;
            }
            QPushButton:pressed {
                background-color: #256d25;
            }
        """
        )
        api_key_layout.addWidget(test_button)

        api_key_group.setLayout(api_key_layout)
        layout.addWidget(api_key_group)

        # Model selection
        model_group = QGroupBox("Model")
        model_layout = QVBoxLayout()

        model_label = QLabel("Select model:")
        model_layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.update_model_list()
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        model_layout.addWidget(self.model_combo)

        # Custom model input (hidden by default)
        self.custom_model_label = QLabel("Enter custom model name:")
        self.custom_model_input = QLineEdit()
        self.custom_model_input.setPlaceholderText("e.g., gemini-1.5-pro")
        self.custom_model_label.hide()
        self.custom_model_input.hide()

        model_layout.addWidget(self.custom_model_label)
        model_layout.addWidget(self.custom_model_input)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # Save button
        save_button = QPushButton("Save API Configuration")
        save_button.clicked.connect(self.save_api_config)
        layout.addWidget(save_button)

        layout.addStretch()
        return page

    def create_display_page(self):
        """Create Display settings page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Page title
        title = QLabel("Display")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        # Screen capture selection group
        capture_group = QGroupBox("Screen Capture")
        capture_layout = QVBoxLayout()

        capture_label = QLabel("Select which display to capture:")
        capture_layout.addWidget(capture_label)

        # Get available displays
        screens = QApplication.screens()
        api_manager = get_api_config_manager()
        current_display = api_manager.get_selected_display()

        # Create button group for radio buttons
        self.display_button_group = QButtonGroup(page)
        self.display_radios = []

        for i, screen in enumerate(screens):
            geometry = screen.geometry()
            is_primary = i == 0

            # Create display info
            display_info = f"Display {i + 1}"
            if is_primary:
                display_info += " (Primary)"
            display_info += f" - {geometry.width()}x{geometry.height()}"

            # Create radio button
            radio = QRadioButton(display_info)
            radio.setChecked(i == current_display)
            self.display_button_group.addButton(radio, i)
            self.display_radios.append(radio)

            # Create horizontal layout for radio + preview button
            display_row = QHBoxLayout()
            display_row.addWidget(radio)

            # Add preview button
            preview_btn = QPushButton("Preview")
            preview_btn.setFixedWidth(100)
            preview_btn.clicked.connect(
                lambda checked, idx=i: self.preview_display(idx)
            )
            display_row.addWidget(preview_btn)
            display_row.addStretch()

            capture_layout.addLayout(display_row)

        # Save button
        save_btn = QPushButton("Save Display Selection")
        save_btn.clicked.connect(self.save_display_selection)
        capture_layout.addWidget(save_btn)

        capture_group.setLayout(capture_layout)
        layout.addWidget(capture_group)

        # Display settings group
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()

        opacity_label = QLabel("Dashboard Opacity:")
        display_layout.addWidget(opacity_label)

        opacity_info = QLabel("Adjust opacity from the dashboard slider (🔍)")
        opacity_info.setStyleSheet("color: #888888;")
        display_layout.addWidget(opacity_info)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        layout.addStretch()
        return page

    def create_notifications_page(self):
        """Create Notifications settings page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Page title
        title = QLabel("Notifications")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        # Notification settings group
        notification_group = QGroupBox("Notification Settings")
        notification_layout = QVBoxLayout()

        api_manager = get_api_config_manager()
        self.enable_notifications_checkbox = QCheckBox("Enable desktop notifications")
        self.enable_notifications_checkbox.setChecked(
            api_manager.get_notification_enabled()
        )
        self.enable_notifications_checkbox.stateChanged.connect(
            self.on_notification_enabled_changed
        )
        notification_layout.addWidget(self.enable_notifications_checkbox)

        notification_info = QLabel(
            "Notifications are managed by macOS system preferences"
        )
        notification_info.setStyleSheet("color: #888888;")
        notification_layout.addWidget(notification_info)

        # Button to open macOS notification settings
        open_settings_btn = QPushButton("Open macOS Notification Settings")
        open_settings_btn.clicked.connect(self.open_macos_notification_settings)
        notification_layout.addWidget(open_settings_btn)

        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)

        # Sound settings group
        sound_group = QGroupBox("Sound Settings")
        sound_layout = QVBoxLayout()

        # Sound enable/disable
        api_manager = get_api_config_manager()
        self.sound_enabled_checkbox = QCheckBox("Enable notification sounds")
        self.sound_enabled_checkbox.setChecked(api_manager.get_sound_enabled())
        self.sound_enabled_checkbox.stateChanged.connect(self.on_sound_enabled_changed)
        sound_layout.addWidget(self.sound_enabled_checkbox)

        # On-task sound selection
        on_task_label = QLabel("Focus (On-task) Sound:")
        sound_layout.addWidget(on_task_label)

        on_task_row = QHBoxLayout()
        self.on_task_combo = QComboBox()

        # Get available on_task sound files
        import os

        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        on_task_sounds = sorted(
            [f for f in os.listdir(assets_dir) if f.startswith("on_task_")]
        )

        for sound in on_task_sounds:
            self.on_task_combo.addItem(sound, sound)

        # Set current selection
        current_on_task = api_manager.get_on_task_sound()
        index = self.on_task_combo.findData(current_on_task)
        if index >= 0:
            self.on_task_combo.setCurrentIndex(index)

        on_task_row.addWidget(self.on_task_combo)

        # Preview button
        on_task_preview_btn = QPushButton("▶ Preview")
        on_task_preview_btn.setFixedWidth(100)
        on_task_preview_btn.clicked.connect(lambda: self.preview_sound("on_task"))
        on_task_row.addWidget(on_task_preview_btn)

        sound_layout.addLayout(on_task_row)

        # Off-task sound selection
        off_task_label = QLabel("Distracted (Off-task) Sound:")
        sound_layout.addWidget(off_task_label)

        off_task_row = QHBoxLayout()
        self.off_task_combo = QComboBox()

        # Get available off_task sound files
        off_task_sounds = sorted(
            [f for f in os.listdir(assets_dir) if f.startswith("off_task_")]
        )

        for sound in off_task_sounds:
            self.off_task_combo.addItem(sound, sound)

        # Set current selection
        current_off_task = api_manager.get_off_task_sound()
        index = self.off_task_combo.findData(current_off_task)
        if index >= 0:
            self.off_task_combo.setCurrentIndex(index)

        off_task_row.addWidget(self.off_task_combo)

        # Preview button
        off_task_preview_btn = QPushButton("▶ Preview")
        off_task_preview_btn.setFixedWidth(100)
        off_task_preview_btn.clicked.connect(lambda: self.preview_sound("off_task"))
        off_task_row.addWidget(off_task_preview_btn)

        sound_layout.addLayout(off_task_row)

        # Save button
        save_sound_btn = QPushButton("Save Sound Settings")
        save_sound_btn.clicked.connect(self.save_sound_settings)
        sound_layout.addWidget(save_sound_btn)

        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)

        layout.addStretch()
        return page

    def on_category_changed(self, index):
        """Handle category selection change"""
        self.content_stack.setCurrentIndex(index)

    def on_provider_changed(self, index):
        """Handle provider change - update API key and model list"""
        provider = self.provider_combo.currentData()
        api_manager = get_api_config_manager()

        # Load the API key for this provider
        provider_api_key = api_manager.get_api_key(provider)
        self.api_key_input.setText(provider_api_key)

        # Update model list
        self.update_model_list()

    def update_model_list(self):
        """Update model list based on selected provider"""
        provider = self.provider_combo.currentData()
        api_manager = get_api_config_manager()

        self.model_combo.clear()

        # Use fixed models from API_CONFIG
        if provider == LLMProvider.OPENAI:
            models = API_CONFIG["openai"]["models"]
        elif provider == LLMProvider.GEMINI:
            models = API_CONFIG["gemini"]["models"]

        for model_id, model_name in models.items():
            self.model_combo.addItem(model_name, model_id)

        # Set current model
        if api_manager.get_provider() == provider:
            current_model = api_manager.get_model(provider)
            if current_model:
                # Check if it's a custom model
                index = self.model_combo.findData(current_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                else:
                    # Custom model - select "custom" and set the input
                    custom_index = self.model_combo.findData("custom")
                    if custom_index >= 0:
                        self.model_combo.setCurrentIndex(custom_index)
                        self.custom_model_input.setText(current_model)

    def on_model_changed(self, index):
        """Handle model selection change - show/hide custom input"""
        selected_model = self.model_combo.currentData()

        if selected_model == "custom":
            # Show custom input field
            self.custom_model_label.show()
            self.custom_model_input.show()
        else:
            # Hide custom input field
            self.custom_model_label.hide()
            self.custom_model_input.hide()

        # Adjust dialog size to fit content
        self.adjustSize()

    def save_api_config(self):
        """Save API configuration"""
        provider = self.provider_combo.currentData()
        api_key = self.api_key_input.text().strip()
        model = self.model_combo.currentData()

        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API key")
            return

        # Handle custom model input
        if model == "custom":
            custom_model = self.custom_model_input.text().strip()
            if not custom_model:
                QMessageBox.warning(self, "Error", "Please enter a custom model name")
                return
            model = custom_model

        if not model:
            QMessageBox.warning(self, "Error", "Please select a model")
            return

        api_manager = get_api_config_manager()

        # Save configuration using separate methods
        api_manager.set_provider(provider)
        api_manager.set_api_key(provider, api_key)
        api_manager.set_model(provider, model)

        QMessageBox.information(
            self,
            "Success",
            f"API configuration saved successfully!\n\nProvider: {provider.value}\nModel: {model}",
        )

    def test_api_key(self):
        """Test if the API key works"""
        from PyQt6.QtWidgets import QApplication, QProgressDialog
        from PyQt6.QtCore import Qt

        provider = self.provider_combo.currentData()
        api_key = self.api_key_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API key first")
            return

        # Show progress dialog
        progress = QProgressDialog(
            f"Testing {provider.value} API key...", None, 0, 0, self
        )
        progress.setWindowTitle("Testing...")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        try:
            from ..utils.direct_llm_client import DirectLLMClient

            # Temporarily create a client with this key
            import os

            original_key = os.getenv(API_CONFIG[provider.value]["api_key_env"])
            os.environ[API_CONFIG[provider.value]["api_key_env"]] = api_key

            client = None
            try:
                # Get currently selected model from UI
                selected_model = self.model_combo.currentData()

                # Handle custom model input
                if selected_model == "custom":
                    custom_model = self.custom_model_input.text().strip()
                    if not custom_model:
                        progress.close()
                        QMessageBox.warning(
                            self, "Error", "Please enter a custom model name"
                        )
                        return
                    selected_model = custom_model
                    model_name = custom_model
                else:
                    model_name = self.model_combo.currentText()

                # Create client with the selected model
                client = DirectLLMClient(provider, model=selected_model)

                # Test with a simple prompt
                result = client.test_api_key()

                # Close progress dialog immediately after getting result
                progress.close()

                if result["success"]:
                    QMessageBox.information(
                        self,
                        "Success",
                        f"✅ API key is valid!\n\nModel: {model_name}\n{result['message']}",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Test Failed",
                        f"❌ API key test failed:\n\nModel: {model_name}\n{result['message']}",
                    )
            finally:
                if client is not None:
                    client.close()
                # Restore original key
                if original_key:
                    os.environ[API_CONFIG[provider.value]["api_key_env"]] = original_key
                else:
                    os.environ.pop(API_CONFIG[provider.value]["api_key_env"], None)

        except Exception as e:
            # Close progress dialog in case of exception
            try:
                progress.close()
            except:
                pass
            QMessageBox.critical(self, "Error", f"Failed to test API key:\n\n{str(e)}")

    def preview_display(self, display_index: int):
        """Show green border around the selected display"""
        # Clear any existing highlights
        self.clear_display_highlights()

        # Get the screen geometry
        screens = QApplication.screens()
        if display_index < len(screens):
            screen = screens[display_index]
            geometry = screen.geometry()

            # Create highlight window
            highlight = DisplayHighlightWindow(geometry)
            highlight.show()
            self.highlight_windows.append(highlight)

            print(f"[DISPLAY] Previewing display {display_index}: {geometry}")

            # Auto-hide after 3 seconds
            QTimer.singleShot(3000, self.clear_display_highlights)

    def save_display_selection(self):
        """Save the selected display"""
        selected_id = self.display_button_group.checkedId()
        if selected_id >= 0:
            api_manager = get_api_config_manager()
            api_manager.set_selected_display(selected_id)

            # Apply to running app immediately if available
            applied = False

            # Try to update via app reference
            if self.app and hasattr(self.app, "manager"):
                self.app.manager.selected_display = selected_id
                print(
                    f"[DISPLAY] Applied display {selected_id} to running manager (via app)"
                )
                applied = True

            # Try to update via parent (Dashboard)
            if (
                not applied
                and self.parent()
                and hasattr(self.parent(), "thread_manager")
            ):
                self.parent().thread_manager.selected_display = selected_id
                print(
                    f"[DISPLAY] Applied display {selected_id} to running manager (via dashboard)"
                )
                applied = True

            # Clear highlights
            self.clear_display_highlights()

            if applied:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Display {selected_id + 1} selected for screen capture.\n\nSettings applied immediately!",
                )
            else:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Display {selected_id + 1} selected for screen capture.\n\nSettings will apply on next start.",
                )

            print(f"[DISPLAY] Saved display selection: {selected_id}")
        else:
            QMessageBox.warning(self, "Error", "Please select a display")

    def clear_display_highlights(self):
        """Remove all display highlight windows"""
        for window in self.highlight_windows:
            window.close()
            window.deleteLater()
        self.highlight_windows.clear()

    def on_float_on_top_changed(self, state):
        """Handle float on top setting change"""
        enabled = state == Qt.CheckState.Checked.value
        api_manager = get_api_config_manager()
        api_manager.set_float_on_top(enabled)

        # Apply to dashboard immediately if available
        # Try to update via app reference
        if self.app and hasattr(self.app, "dashboard"):
            self.app.dashboard.set_float_on_top(enabled)
        # Try to update via parent (Dashboard)
        elif self.parent() and hasattr(self.parent(), "set_float_on_top"):
            self.parent().set_float_on_top(enabled)

    def on_exclude_capture_changed(self, state):
        """Handle dashboard capture exclusion toggle"""
        enabled = state == Qt.CheckState.Checked.value
        api_manager = get_api_config_manager()
        api_manager.set_exclude_dashboard_from_capture(enabled)
        print(
            f"[SETTINGS] Dashboard screen capture exclusion "
            f"{'enabled' if enabled else 'disabled'}"
        )

        # Apply immediately if possible
        if self.app and hasattr(self.app, "dashboard"):
            self.app.dashboard.set_exclude_from_capture(enabled)
        elif self.parent() and hasattr(self.parent(), "set_exclude_from_capture"):
            self.parent().set_exclude_from_capture(enabled)

    def on_notification_enabled_changed(self, state):
        """Handle notification enabled/disabled change"""
        enabled = state == Qt.CheckState.Checked.value
        api_manager = get_api_config_manager()
        api_manager.set_notification_enabled(enabled)
        print(f"[NOTIFICATION] Notifications {'enabled' if enabled else 'disabled'}")

    def on_sound_enabled_changed(self, state):
        """Handle sound enabled/disabled change"""
        enabled = state == Qt.CheckState.Checked.value
        api_manager = get_api_config_manager()
        api_manager.set_sound_enabled(enabled)
        print(f"[SOUND] Sound {'enabled' if enabled else 'disabled'}")

    def preview_sound(self, sound_type: str):
        """Preview the selected sound"""
        import os
        import subprocess
        import threading

        # Get selected sound file
        if sound_type == "on_task":
            sound_file = self.on_task_combo.currentData()
        else:
            sound_file = self.off_task_combo.currentData()

        # Get assets directory
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        sound_path = os.path.join(assets_dir, sound_file)

        if not os.path.exists(sound_path):
            QMessageBox.warning(self, "Error", f"Sound file not found: {sound_file}")
            return

        print(f"[SOUND] Previewing: {sound_path}")

        # Play sound in background thread using afplay (macOS native)
        def _play_preview():
            try:
                result = subprocess.run(
                    ["afplay", sound_path], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    print(f"[SOUND] Preview played successfully: {sound_file}")
                else:
                    print(f"[SOUND] Preview failed: {result.stderr}")
            except Exception as e:
                print(f"[SOUND] Preview error: {e}")

        threading.Thread(target=_play_preview, daemon=True).start()

    def save_sound_settings(self):
        """Save sound settings"""
        api_manager = get_api_config_manager()

        # Get selected sounds
        on_task_sound = self.on_task_combo.currentData()
        off_task_sound = self.off_task_combo.currentData()

        # Save to config
        api_manager.set_on_task_sound(on_task_sound)
        api_manager.set_off_task_sound(off_task_sound)

        QMessageBox.information(
            self,
            "Success",
            f"Sound settings saved!\n\nOn-task: {on_task_sound}\nOff-task: {off_task_sound}",
        )
        print(
            f"[SOUND] Settings saved - On-task: {on_task_sound}, Off-task: {off_task_sound}"
        )

    def open_macos_notification_settings(self):
        """Open macOS System Settings to Notifications"""
        import subprocess

        try:
            # Try to open Notifications settings directly
            # This works on macOS Ventura and later
            result = subprocess.run(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.notifications",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Fallback: just open System Settings
                subprocess.run(["open", "-a", "System Settings"])
                QMessageBox.information(
                    self,
                    "System Settings",
                    "Please navigate to Notifications in System Settings",
                )

            print("[SETTINGS] Opened macOS Notification Settings")

        except Exception as e:
            print(f"[SETTINGS] Failed to open notification settings: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open System Settings.\n\nPlease open System Settings manually and navigate to Notifications.",
            )

    def closeEvent(self, event):
        """Handle dialog close - clean up highlights"""
        self.clear_display_highlights()
        super().closeEvent(event)

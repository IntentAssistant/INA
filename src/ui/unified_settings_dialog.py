"""
Unified Settings Dialog - Cursor-style settings UI
"""

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
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

from ..config.api_config import (
    LLMProvider,
    get_api_config_manager,
    API_CONFIG,
)


class UnifiedSettingsDialog(QDialog):
    """Unified settings dialog with sidebar navigation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(900, 600)
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

        app_name_label = QLabel("App Name: AIM (Aligned Intention Monitoring)")
        app_version_label = QLabel("Version: 1.0.1")
        app_description = QLabel("AI-powered focus management application for macOS")
        app_description.setWordWrap(True)

        info_layout.addWidget(app_name_label)
        info_layout.addWidget(app_version_label)
        info_layout.addWidget(app_description)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

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

        enable_notifications = QCheckBox("Enable desktop notifications")
        enable_notifications.setChecked(True)
        enable_notifications.setEnabled(False)  # Always enabled
        notification_layout.addWidget(enable_notifications)

        notification_info = QLabel(
            "Notifications are managed by macOS system preferences"
        )
        notification_info.setStyleSheet("color: #888888;")
        notification_layout.addWidget(notification_info)

        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)

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

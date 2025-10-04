"""
API Settings Dialog for configuring LLM providers and models
"""

import sys
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QTabWidget,
    QWidget,
    QTextEdit,
    QGroupBox,
    QGridLayout,
    QMessageBox,
    QProgressBar,
    QCheckBox,
    QFrame,
    QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor
import requests
import json

from ..config.api_config import (
    LLMProvider,
    API_CONFIG,
    get_api_config_manager,
    APIConfigManager,
)


class APIValidationThread(QThread):
    """Thread for validating API keys without blocking UI"""

    validation_complete = pyqtSignal(str, bool, str)  # provider, success, message

    def __init__(self, provider: LLMProvider, api_key: str, model: str):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.model = model

    def run(self):
        """Validate API key by making a test request"""
        try:
            if self.provider == LLMProvider.OPENAI:
                success, message = self._validate_openai()
            elif self.provider == LLMProvider.GEMINI:
                success, message = self._validate_gemini()
            else:
                success, message = False, "Unknown provider"

            self.validation_complete.emit(self.provider.value, success, message)
        except Exception as e:
            self.validation_complete.emit(
                self.provider.value, False, f"Validation error: {str(e)}"
            )

    def _validate_openai(self) -> tuple[bool, str]:
        """Validate OpenAI API key"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Simple models list request to validate key
            response = requests.get(
                "https://api.openai.com/v1/models", headers=headers, timeout=10
            )

            if response.status_code == 200:
                return True, "OpenAI API key is valid"
            elif response.status_code == 401:
                return False, "Invalid OpenAI API key"
            else:
                return False, f"OpenAI API error: {response.status_code}"

        except requests.exceptions.Timeout:
            return False, "Request timeout - check your internet connection"
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"

    def _validate_gemini(self) -> tuple[bool, str]:
        """Validate Gemini API key"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models"
            params = {"key": self.api_key}

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                return True, "Gemini API key is valid"
            elif response.status_code == 400:
                return False, "Invalid Gemini API key"
            else:
                return False, f"Gemini API error: {response.status_code}"

        except requests.exceptions.Timeout:
            return False, "Request timeout - check your internet connection"
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"


class APISettingsDialog(QDialog):
    """Dialog for configuring API settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_manager = get_api_config_manager()
        self.validation_threads = {}
        self.setup_ui()
        self.load_current_settings()

    def setup_ui(self):
        """Setup the UI layout"""
        self.setWindowTitle("API Settings - AIM")
        self.setModal(True)
        self.setMinimumSize(800, 700)
        self.resize(900, 800)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        title = QLabel("LLM API Configuration")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Configure your AI model providers for intention analysis")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(subtitle)

        # Provider selection
        provider_group = QGroupBox("Active Provider")
        provider_layout = QVBoxLayout(provider_group)

        self.provider_combo = QComboBox()
        for provider in LLMProvider:
            display_name = API_CONFIG[provider.value]["display_name"]
            self.provider_combo.addItem(display_name, provider)

        provider_layout.addWidget(self.provider_combo)
        layout.addWidget(provider_group)

        # Tab widget for different providers
        self.tab_widget = QTabWidget()

        # OpenAI Tab
        self.openai_tab = self.create_provider_tab(LLMProvider.OPENAI)
        self.tab_widget.addTab(self.openai_tab, "OpenAI GPT")

        # Gemini Tab
        self.gemini_tab = self.create_provider_tab(LLMProvider.GEMINI)
        self.tab_widget.addTab(self.gemini_tab, "Google Gemini")

        layout.addWidget(self.tab_widget)

        # Status area
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("Validation results will appear here...")
        layout.addWidget(self.status_text)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()

        self.test_all_button = QPushButton("Test All APIs")
        self.test_all_button.clicked.connect(self.test_all_apis)

        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setDefault(True)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.test_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

        # Connect signals
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)

    def create_provider_tab(self, provider: LLMProvider) -> QWidget:
        """Create a tab for a specific provider"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Provider info
        config = API_CONFIG[provider.value]
        info_label = QLabel(f"Configure your {config['display_name']} settings")
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # API Key section
        api_group = QGroupBox("API Key")
        api_layout = QVBoxLayout(api_group)  # Changed to VBoxLayout for better clarity
        api_layout.setSpacing(15)
        api_layout.setContentsMargins(20, 20, 20, 20)

        # API Key label
        api_key_label = QLabel("API Key:")
        api_key_label.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: #2c3e50;"
        )
        api_layout.addWidget(api_key_label)

        # API Key input
        api_key_input = QLineEdit()
        api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_input.setPlaceholderText("Paste your API key here...")
        api_key_input.setMinimumHeight(45)
        api_key_input.setStyleSheet(
            """
            QLineEdit {
                padding: 12px;
                font-size: 14px;
                border: 3px solid #4a90e2;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 3px solid #2ecc71;
                background-color: #f0fff4;
            }
        """
        )
        api_layout.addWidget(api_key_input)

        # Show key and test button row
        button_row = QHBoxLayout()
        button_row.setSpacing(15)

        show_key_checkbox = QCheckBox("Show API Key")
        show_key_checkbox.setStyleSheet("font-size: 13px; padding: 5px;")
        show_key_checkbox.toggled.connect(
            lambda checked: api_key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        button_row.addWidget(show_key_checkbox)

        button_row.addStretch()

        test_button = QPushButton("🔍 Test API Key")
        test_button.setMinimumHeight(40)
        test_button.setMinimumWidth(150)
        test_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """
        )
        test_button.clicked.connect(lambda: self.test_api_key(provider))
        button_row.addWidget(test_button)

        api_layout.addLayout(button_row)

        layout.addWidget(api_group)

        # Model selection
        model_group = QGroupBox("Model Selection")
        model_layout = QVBoxLayout(model_group)  # Changed to VBoxLayout
        model_layout.setSpacing(15)
        model_layout.setContentsMargins(20, 20, 20, 20)

        model_label = QLabel("Model:")
        model_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        model_layout.addWidget(model_label)

        model_combo = QComboBox()
        model_combo.setMinimumHeight(45)
        model_combo.setStyleSheet(
            """
            QComboBox {
                padding: 10px;
                font-size: 14px;
                border: 3px solid #4a90e2;
                border-radius: 8px;
                background-color: white;
            }
            QComboBox:focus {
                border: 3px solid #2ecc71;
            }
            QComboBox::drop-down {
                border: none;
                width: 35px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 6px solid #4a90e2;
                margin-right: 12px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #4a90e2;
                border-radius: 5px;
                background-color: white;
                selection-background-color: #4a90e2;
                selection-color: white;
                padding: 5px;
                font-size: 13px;
            }
        """
        )

        for model_id, model_name in config["models"].items():
            model_combo.addItem(model_name, model_id)

        model_layout.addWidget(model_combo)

        layout.addWidget(model_group)

        # Get API key info
        get_key_group = QGroupBox("Get API Key")
        get_key_layout = QVBoxLayout(get_key_group)

        if provider == LLMProvider.OPENAI:
            get_key_info = QLabel(
                "Get your OpenAI API key from: "
                '<a href="https://platform.openai.com/api-keys">https://platform.openai.com/api-keys</a>'
            )
        else:
            get_key_info = QLabel(
                "Get your Gemini API key from: "
                '<a href="https://ai.google.dev/gemini-api/docs/api-key">https://ai.google.dev/gemini-api/docs/api-key</a>'
            )

        get_key_info.setOpenExternalLinks(True)
        get_key_info.setWordWrap(True)
        get_key_layout.addWidget(get_key_info)

        layout.addWidget(get_key_group)

        layout.addStretch()

        # Store references for easy access
        setattr(tab, "api_key_input", api_key_input)
        setattr(tab, "model_combo", model_combo)
        setattr(tab, "test_button", test_button)

        return tab

    def load_current_settings(self):
        """Load current settings from configuration"""
        # Set current provider
        current_provider = self.api_manager.get_provider()
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == current_provider:
                self.provider_combo.setCurrentIndex(i)
                break

        # Load API keys and models for each provider
        for provider in LLMProvider:
            tab = self.openai_tab if provider == LLMProvider.OPENAI else self.gemini_tab

            # Load API key
            api_key = self.api_manager.get_api_key(provider)
            tab.api_key_input.setText(api_key)

            # Load model
            model = self.api_manager.get_model(provider)
            for i in range(tab.model_combo.count()):
                if tab.model_combo.itemData(i) == model:
                    tab.model_combo.setCurrentIndex(i)
                    break

    def on_provider_changed(self):
        """Handle provider selection change"""
        provider = self.provider_combo.currentData()
        if provider == LLMProvider.OPENAI:
            self.tab_widget.setCurrentIndex(0)
        else:
            self.tab_widget.setCurrentIndex(1)

    def test_api_key(self, provider: LLMProvider):
        """Test a specific API key"""
        tab = self.openai_tab if provider == LLMProvider.OPENAI else self.gemini_tab

        api_key = tab.api_key_input.text().strip()
        if not api_key:
            self.show_status(
                f"❌ Please enter an API key for {API_CONFIG[provider.value]['display_name']}"
            )
            return

        model = tab.model_combo.currentData()

        # Disable test button and show progress
        tab.test_button.setEnabled(False)
        tab.test_button.setText("Testing...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Start validation thread
        thread = APIValidationThread(provider, api_key, model)
        thread.validation_complete.connect(self.on_validation_complete)
        self.validation_threads[provider.value] = thread
        thread.start()

    def test_all_apis(self):
        """Test all configured API keys"""
        self.status_text.clear()
        self.show_status("🔄 Testing all API configurations...")

        tested_any = False
        for provider in LLMProvider:
            tab = self.openai_tab if provider == LLMProvider.OPENAI else self.gemini_tab
            api_key = tab.api_key_input.text().strip()

            if api_key:
                self.test_api_key(provider)
                tested_any = True

        if not tested_any:
            self.show_status(
                "❌ No API keys to test. Please enter at least one API key."
            )

    def on_validation_complete(self, provider_str: str, success: bool, message: str):
        """Handle validation completion"""
        provider = LLMProvider(provider_str)
        tab = self.openai_tab if provider == LLMProvider.OPENAI else self.gemini_tab

        # Re-enable test button
        tab.test_button.setEnabled(True)
        tab.test_button.setText("Test API Key")

        # Show result
        provider_name = API_CONFIG[provider.value]["display_name"]
        status_icon = "✅" if success else "❌"
        self.show_status(f"{status_icon} {provider_name}: {message}")

        # Check if all validations are complete
        all_complete = True
        for thread in self.validation_threads.values():
            if thread.isRunning():
                all_complete = False
                break

        if all_complete:
            self.progress_bar.setVisible(False)

    def show_status(self, message: str):
        """Show status message"""
        self.status_text.append(message)
        # Auto-scroll to bottom
        cursor = self.status_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.status_text.setTextCursor(cursor)

    def save_settings(self):
        """Save all settings"""
        try:
            # Save active provider
            selected_provider = self.provider_combo.currentData()
            self.api_manager.set_provider(selected_provider)

            # Save settings for each provider
            for provider in LLMProvider:
                tab = (
                    self.openai_tab
                    if provider == LLMProvider.OPENAI
                    else self.gemini_tab
                )

                # Save API key
                api_key = tab.api_key_input.text().strip()
                if api_key:  # Only save non-empty keys
                    self.api_manager.set_api_key(provider, api_key)

                # Save model
                model = tab.model_combo.currentData()
                self.api_manager.set_model(provider, model)

            # Check if any provider is configured
            configured_providers = self.api_manager.get_configured_providers()

            if not configured_providers:
                QMessageBox.warning(
                    self,
                    "No API Configured",
                    "You haven't configured any API keys. The app may not function properly.\n\n"
                    "Please add at least one API key to use AIM.",
                )
                return

            # Success message
            provider_names = [
                API_CONFIG[p.value]["display_name"] for p in configured_providers
            ]
            active_provider = API_CONFIG[selected_provider.value]["display_name"]

            QMessageBox.information(
                self,
                "Settings Saved",
                f"API settings saved successfully!\n\n"
                f"Active Provider: {active_provider}\n"
                f"Configured Providers: {', '.join(provider_names)}\n\n"
                f"Your changes will take effect immediately.",
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Failed to save settings:\n{str(e)}"
            )

    def closeEvent(self, event):
        """Handle dialog close"""
        # Stop any running validation threads
        for thread in self.validation_threads.values():
            if thread.isRunning():
                thread.terminate()
                thread.wait(1000)

        super().closeEvent(event)


def main():
    """Test the dialog standalone"""
    app = QApplication(sys.argv)
    dialog = APISettingsDialog()
    dialog.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

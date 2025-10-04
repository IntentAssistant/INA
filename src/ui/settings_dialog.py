from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QTextEdit,
    QSpinBox,
    QGroupBox,
    QHBoxLayout,
    QDialogButtonBox,
    QRadioButton,
    QApplication,
    QWidget,
    QComboBox,
    QButtonGroup,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor
import os
import getpass
from ..config.language import get_text, set_language, get_current_language
from .api_settings_dialog import APISettingsDialog


class LanguageSettingsDialog(QDialog):
    """Dialog for language settings"""

    language_changed = pyqtSignal(str)  # Signal when language is changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the language settings dialog UI"""
        self.setWindowTitle(get_text("language_dialog_title"))
        self.setMinimumWidth(400)
        self.setModal(True)

        # Keep window frame for dragging capability
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        # Main layout
        layout = QVBoxLayout()

        # Description label
        description = QLabel(get_text("language_dialog_description"))
        description.setWordWrap(True)
        description.setStyleSheet(
            """
            QLabel {
                color: #2ecc71;
                padding: 10px;
                background-color: rgba(60, 60, 60, 80);
                border-radius: 5px;
                margin-bottom: 10px;
            }
            """
        )
        layout.addWidget(description)

        # Language selection form
        form_layout = QFormLayout()

        # Radio buttons for language selection
        self.button_group = QButtonGroup()

        self.korean_radio = QRadioButton(get_text("language_korean"))
        self.english_radio = QRadioButton(get_text("language_english"))

        # Set current language as selected
        current_lang = get_current_language()
        if current_lang == "ko":
            self.korean_radio.setChecked(True)
        else:
            self.english_radio.setChecked(True)

        self.button_group.addButton(self.korean_radio, 0)
        self.button_group.addButton(self.english_radio, 1)

        # Add radio buttons to form
        form_layout.addRow("", self.korean_radio)
        form_layout.addRow("", self.english_radio)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        # Translate button text
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            get_text("save_button")
        )
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            get_text("cancel_button")
        )

        button_box.accepted.connect(self.save_language)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

        # Apply dark theme style to match UserSettingsDialog
        self.setStyleSheet(
            """
            QDialog {
                background-color: #2c2c2c;
                color: white;
                border-radius: 12px;
                border: 1px solid #404040;
            }
            QRadioButton {
                color: white;
                padding: 5px;
                font-size: 14px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #6c6c6c;
                border-radius: 8px;
                background-color: #3c3c3c;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #2ecc71;
                border-radius: 8px;
                background-color: #2ecc71;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
            """
        )

    def save_language(self):
        """Save the selected language"""
        if self.korean_radio.isChecked():
            new_language = "ko"
        else:
            new_language = "en"

        # Change language
        if set_language(new_language):
            self.language_changed.emit(new_language)

            # Show success message with dark theme and window frame
            msg = QMessageBox(self)
            msg.setWindowTitle(get_text("language_dialog_title"))
            msg.setText(get_text("language_change_success"))
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)

            # Keep window frame for dragging capability
            msg.setWindowFlags(
                Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
            )

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
                QMessageBox QPushButton:pressed {
                    background-color: #5c5c5c;
                }
            """
            )
            msg.exec()

            self.accept()
        else:
            # Show error message with dark theme and window frame
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText("Failed to save language setting.")
            msg.setIcon(QMessageBox.Icon.Warning)

            # Keep window frame for dragging capability
            msg.setWindowFlags(
                Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
            )

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
            """
            )
            msg.exec()


class UserSettingsDialog(QDialog):
    def __init__(self, current_settings):
        super().__init__()
        self.setWindowTitle(get_text("user_settings"))
        self.setMinimumWidth(400)
        self.setup_ui(current_settings)

    def setup_ui(self, current_settings):
        layout = QVBoxLayout()

        # Description label
        description = QLabel("Configure your AI model providers (OpenAI GPT, Google Gemini)")
        description.setWordWrap(True)
        description.setStyleSheet(
            """
            QLabel {
                color: #2ecc71;
                padding: 10px;
                background-color: rgba(60, 60, 60, 80);
                border-radius: 5px;
                margin-bottom: 10px;
            }
            """
        )
        layout.addWidget(description)

        # API Settings section
        api_group = QGroupBox("AI Model Configuration")
        api_layout = QVBoxLayout(api_group)

        api_description = QLabel(
            "Configure your AI model providers (OpenAI GPT, Google Gemini)"
        )
        api_description.setStyleSheet("color: #999; font-size: 12px;")
        api_description.setWordWrap(True)
        api_layout.addWidget(api_description)

        self.api_settings_button = QPushButton("Configure API Settings")
        self.api_settings_button.clicked.connect(self.open_api_settings)
        self.api_settings_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """
        )
        api_layout.addWidget(self.api_settings_button)

        layout.addWidget(api_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        layout.addWidget(button_box)

        self.setLayout(layout)

        # Style
        self.setStyleSheet(
            """
            QDialog {
                background-color: #2c2c2c;
                color: white;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
            """
        )

    def open_api_settings(self):
        """Open API settings dialog"""
        dialog = APISettingsDialog(self)
        dialog.exec()

    def get_user_input(self):
        """Return empty dict as user credentials are no longer needed"""
        return {}


class PromptSettingsDialog(QDialog):
    def __init__(self, current_prompt):
        super().__init__()
        self.setWindowTitle("Prompt Settings")
        self.setMinimumSize(600, 400)
        self.setup_ui(current_prompt)

    def setup_ui(self, current_prompt):
        layout = QVBoxLayout()

        # Guide Label
        guide_label = QLabel(
            "Available variables for dynamic prompt:\n"
            "- {task_name} : Current task name\n\n"
            "Example:\n"
            "You are an AI coach. The user's current task is {task_name}.\n"
            "Help users stay mindful of their task while providing feedback.\n\n"
        )
        guide_label.setStyleSheet(
            """
            QLabel {
                background-color: rgba(60, 60, 60, 80);
                padding: 10px;
                border-radius: 5px;
                color: #2ecc71;
                font-size: 12px;
            }
        """
        )
        guide_label.setWordWrap(True)
        layout.addWidget(guide_label)

        # Prompt Editor Label
        editor_label = QLabel("Enter your custom prompt:")
        layout.addWidget(editor_label)

        # Text Editor
        self.text_edit = QTextEdit()
        self.text_edit.setText(current_prompt)
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setMinimumHeight(200)
        layout.addWidget(self.text_edit)

        # Save Button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def get_prompt(self):
        return self.text_edit.toPlainText()


class DisplayOverlay(QWidget):
    def __init__(self, geometry):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(geometry)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Set pen properties for the border
        pen = QPen(QColor("#00ff00"))  # Neon green color
        pen.setWidth(4)
        painter.setPen(pen)

        # Draw rectangle border
        painter.drawRect(self.rect().adjusted(2, 2, -2, -2))


class DisplaySettingsDialog(QDialog):
    def __init__(self, current_settings=None):
        super().__init__()
        self.setWindowTitle("Display Settings")
        self.setFixedWidth(400)
        self.overlay = None
        self.current_display_index = (
            current_settings.get("selected_display", 0) if current_settings else 0
        )

        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Display selection group
        display_group = QGroupBox("Display Selection")
        display_layout = QVBoxLayout()

        # Get list of displays
        self.displays = QApplication.screens()
        self.display_buttons = []

        # In single display environment, force selection to 0
        if len(self.displays) == 1:
            print(
                "Single display environment detected in settings - auto-selecting display 0"
            )
            current_settings = {"selected_display": 0}

        # Create radio buttons for each display
        for i, screen in enumerate(self.displays):
            geometry = screen.geometry()
            name = screen.name()
            manufacturer = screen.manufacturer()
            model = screen.model()

            # Format display name
            if "built-in" in name.lower() or "built-in" in model.lower():
                display_name = "Built-in Display"
            else:
                # Try to create a readable name from manufacturer and model
                if manufacturer and model:
                    display_name = f"{manufacturer} {model}"
                elif model:
                    display_name = model
                else:
                    display_name = f"Display {i+1}"

            # Add resolution info
            display_info = f"{display_name} ({geometry.width()}x{geometry.height()})"

            radio = QRadioButton(display_info)
            radio.clicked.connect(
                lambda checked, index=i: self.show_display_overlay(index)
            )

            if current_settings and current_settings.get("selected_display") == i:
                radio.setChecked(True)
            elif i == 0 and not current_settings:  # Default to first display
                radio.setChecked(True)

            self.display_buttons.append(radio)
            display_layout.addWidget(radio)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Style
        self.setStyleSheet(
            """
            QDialog {
                background-color: #2c2c2c;
                color: white;
            }
            QGroupBox {
                color: white;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QRadioButton {
                color: white;
                spacing: 5px;
                padding: 5px 0;
            }
            QRadioButton::indicator {
                width: 15px;
                height: 15px;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
        """
        )

        # Show initial overlay
        self.show_display_overlay(self.current_display_index)

    def on_accept(self):
        """Handle OK button click"""
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        self.accept()

    def show_display_overlay(self, display_index):
        """Show overlay on the selected display"""
        # Remove previous overlay if exists
        if self.overlay:
            self.overlay.close()
            self.overlay = None

        if display_index < len(self.displays):
            screen = self.displays[display_index]
            geometry = screen.geometry()

            # Create and show new overlay
            self.overlay = DisplayOverlay(geometry)
            self.overlay.show()
            self.current_display_index = display_index

    def closeEvent(self, event):
        """Clean up overlay when dialog closes"""
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        super().closeEvent(event)

    def get_settings(self):
        """Get the selected display settings"""
        for i, button in enumerate(self.display_buttons):
            if button.isChecked():
                return {"selected_display": i}
        return {"selected_display": 0}  # Default to first display if none selected


class SoundSettingsDialog(QDialog):
    def __init__(self, sound_settings):
        super().__init__()
        self.setWindowTitle("Sound Settings")
        self.setFixedWidth(400)
        self.setMinimumHeight(300)  # Set minimum height
        self.sound_settings = sound_settings
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Sound selection group
        sound_group = QGroupBox("Notification Sounds")
        sound_layout = QFormLayout()

        # Get available sound files
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        self.distract_sounds = []
        self.focus_sounds = []

        if os.path.exists(assets_dir):
            for file in os.listdir(assets_dir):
                # For distracted state, use focus_* sound files
                if file.startswith("focus_") and (
                    file.endswith(".mp3") or file.endswith(".wav")
                ):
                    self.distract_sounds.append(file)
                # For focused state, use good_* sound files
                elif file.startswith("good_") and (
                    file.endswith(".mp3") or file.endswith(".wav")
                ):
                    self.focus_sounds.append(file)

        # Sort sound files
        self.distract_sounds.sort()
        self.focus_sounds.sort()

        # Distract sound selection (for state 1 - distracted)
        self.distract_sound_combo = QComboBox()
        self.distract_sound_combo.setMinimumWidth(150)
        self.distract_sound_combo.setMaxVisibleItems(7)  # Limit visible items
        for i, sound in enumerate(self.distract_sounds):
            self.distract_sound_combo.addItem(f"Sound {i+1}")

        # Set current selection
        current_distract_sound = self.sound_settings.get(
            "distract_sound"
        )  # Key name in settings
        if current_distract_sound and current_distract_sound in self.distract_sounds:
            index = self.distract_sounds.index(current_distract_sound)
            self.distract_sound_combo.setCurrentIndex(index)

        # Add test button for distract sound
        distract_layout = QHBoxLayout()
        distract_layout.addWidget(self.distract_sound_combo, 1)

        test_distract_button = QPushButton("Test")
        test_distract_button.setFixedWidth(60)
        test_distract_button.clicked.connect(self.test_distract_sound)
        distract_layout.addWidget(test_distract_button)

        sound_layout.addRow("Distract Sound:", distract_layout)

        # Focus sound selection (for state 0 - focused)
        self.focus_sound_combo = QComboBox()
        self.focus_sound_combo.setMinimumWidth(150)
        self.focus_sound_combo.setMaxVisibleItems(7)  # Limit visible items
        for i, sound in enumerate(self.focus_sounds):
            self.focus_sound_combo.addItem(f"Sound {i+1}")

        # Set current selection
        current_focus_sound = self.sound_settings.get(
            "focus_sound"
        )  # Key name in settings
        if current_focus_sound and current_focus_sound in self.focus_sounds:
            index = self.focus_sounds.index(current_focus_sound)
            self.focus_sound_combo.setCurrentIndex(index)

        # Add test button for focus sound
        focus_layout = QHBoxLayout()
        focus_layout.addWidget(self.focus_sound_combo, 1)

        test_focus_button = QPushButton("Test")
        test_focus_button.setFixedWidth(60)
        test_focus_button.clicked.connect(self.test_focus_sound)
        focus_layout.addWidget(test_focus_button)

        sound_layout.addRow("Focus Sound:", focus_layout)

        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)

        # Description
        description = QLabel(
            "Select sounds for different notification types:\n"
            "• Focus Sound: Played when you're focused on task\n"
            "• Distract Sound: Played when you're distracted"
        )
        description.setStyleSheet(
            """
            QLabel {
                background-color: rgba(60, 60, 60, 80);
                padding: 10px;
                border-radius: 5px;
                color: #2ecc71;
                font-size: 12px;
            }
            """
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Style
        self.setStyleSheet(
            """
            QDialog {
                background-color: #2c2c2c;
                color: white;
            }
            QGroupBox {
                color: white;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 14px;
                height: 14px;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: white;
                selection-background-color: #4c4c4c;
                border: 1px solid #555;
                padding: 5px;
                min-width: 150px;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
            QLabel {
                color: white;
            }
            """
        )

    def test_distract_sound(self):
        """Test the selected distract sound"""
        index = self.distract_sound_combo.currentIndex()
        if index >= 0 and index < len(self.distract_sounds):
            sound_file = self.distract_sounds[index]
            self.play_sound(sound_file)

    def test_focus_sound(self):
        """Test the selected focus sound"""
        index = self.focus_sound_combo.currentIndex()
        if index >= 0 and index < len(self.focus_sounds):
            sound_file = self.focus_sounds[index]
            self.play_sound(sound_file)

    def play_sound(self, sound_file):
        """Play a sound file"""
        import subprocess

        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        sound_path = os.path.join(assets_dir, sound_file)
        if os.path.exists(sound_path):
            subprocess.Popen(["afplay", sound_path])

    def get_sound_settings(self):
        """Get the selected sound settings"""
        focus_index = self.focus_sound_combo.currentIndex()
        distract_index = self.distract_sound_combo.currentIndex()

        # For focus state (0), use good_* sounds
        focus_sound = (
            self.focus_sounds[focus_index]
            if focus_index >= 0 and focus_index < len(self.focus_sounds)
            else self.focus_sounds[0]
        )

        # For distracted state (1), use focus_* sounds
        distract_sound = (
            self.distract_sounds[distract_index]
            if distract_index >= 0 and distract_index < len(self.distract_sounds)
            else self.distract_sounds[0]
        )

        return {
            "focus_sound": focus_sound,
            "distract_sound": distract_sound,
        }

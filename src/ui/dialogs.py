import rumps
from PyQt6.QtWidgets import (
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


MULTI_DISPLAY_TITLE = "Multiple Displays Detected"
MULTI_DISPLAY_MESSAGE = (
    "INA currently supports a single display.\n\n"
    "Please disconnect extra monitors or disable extended desktop mode, then restart the app."
)
MULTI_DISPLAY_INSTRUCTIONS = (
    "\n\n📋 Choose one of these options:\n"
    "• Disconnect the external monitor cable\n"
    "• Close your laptop lid (clamshell mode) to use only the external monitor\n"
    "• Open System Settings → Displays and disable one display\n\n"
    "Restart the app afterwards."
)
EXIT_APP_BUTTON = "Exit App"


class MultiDisplayDialog(QDialog):
    """Custom dialog for multiple display detection with prominent display"""

    def __init__(self, display_count, display_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(MULTI_DISPLAY_TITLE)
        self.setModal(True)
        self.setFixedSize(600, 450)  # Increased size for better text visibility

        # Always on top and center on screen
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.Tool  # Better visibility on macOS
        )

        # Center the dialog on the primary screen
        self.center_on_screen()

        # Set dark theme background
        self.setStyleSheet(
            """
            QDialog {
                background-color: #202020;
                color: white;
            }
        """
        )

        # Setup UI
        self.setup_ui(display_count, display_list)

    def center_on_screen(self):
        """Center the dialog on the primary screen"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def setup_ui(self, display_count, display_list):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title_label = QLabel(MULTI_DISPLAY_TITLE)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #FF3B30; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Main message
        display_info = f"\n\nCurrently connected displays ({display_count}):\n{display_list}"
        full_message = MULTI_DISPLAY_MESSAGE + display_info + MULTI_DISPLAY_INSTRUCTIONS
        main_message = QLabel(full_message)
        main_message.setWordWrap(True)
        main_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_message.setStyleSheet(
            """
            QLabel {
                background-color: #2c2c2c;
                color: white;
                border: 2px solid #FF3B30;
                border-radius: 8px;
                padding: 20px;
                font-size: 14px;
                line-height: 1.6;
            }
        """
        )
        layout.addWidget(main_message)

        # OK button
        ok_button = QPushButton(EXIT_APP_BUTTON)
        ok_button.setFixedHeight(40)
        ok_button.setStyleSheet(
            """
            QPushButton {
                background-color: #FF3B30;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #FF5E57;
            }
            QPushButton:pressed {
                background-color: #D12B20;
            }
        """
        )
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        # Focus on the button for immediate Enter key response
        ok_button.setFocus()

    def showEvent(self, event):
        """Override showEvent to ensure dialog is brought to front"""
        super().showEvent(event)
        self.activateWindow()
        self.raise_()


class Dialogs:
    @staticmethod
    def show_notification(title, subtitle, message, sound=False):
        """Show a notification using rumps (system notifications - always show)"""
        print(f"[DIALOGS] System notification: {title} - {subtitle}")
        rumps.notification(title, subtitle, message, sound=sound)

    @staticmethod
    def show_error(title, message):
        """Show an error dialog"""
        dialog = QMessageBox()
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()

    @staticmethod
    def show_multiple_display_error(display_count, display_list):
        """Show a prominent modal dialog for multiple display detection"""
        print(f"[DIALOGS] ===== STARTING MULTIPLE DISPLAY ERROR DIALOG =====")
        print(f"[DIALOGS] Display count: {display_count}")
        print(f"[DIALOGS] Display list: {display_list}")

        try:
            # Force bring to front and ensure visibility
            app = QApplication.instance()
            if app:
                print(f"[DIALOGS] Processing QApplication events...")
                app.processEvents()  # Process pending events first
                print(f"[DIALOGS] QApplication events processed")

            # Use Qt dialog only (no native macOS alert to avoid app icon)
            print(f"[DIALOGS] Creating MultiDisplayDialog...")
            dialog = MultiDisplayDialog(display_count, display_list)
            print(f"[DIALOGS] MultiDisplayDialog created")

            # Force dialog to be on top and visible
            dialog.setWindowFlags(
                Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Dialog
                | Qt.WindowType.Tool
            )
            dialog.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)

            # Show dialog first
            dialog.show()
            print(f"[DIALOGS] Dialog shown")

            # Force to front multiple times with processing events between
            if app:
                app.processEvents()

            dialog.activateWindow()
            dialog.raise_()
            print(f"[DIALOGS] Dialog activated and raised")

            # Process events again after activation
            if app:
                app.processEvents()

            # Force focus on the dialog
            dialog.setFocus()
            print(f"[DIALOGS] Dialog focused")

            print(f"[DIALOGS] Dialog window flags set and shown")

            # Show the dialog
            print(f"[DIALOGS] Calling dialog.exec()...")
            result = dialog.exec()
            print(f"[DIALOGS] Dialog closed with result: {result}")

            # Process events after dialog closes
            if app:
                print(f"[DIALOGS] Processing events after dialog close...")
                app.processEvents()

            print(f"[DIALOGS] ===== DIALOG COMPLETED SUCCESSFULLY =====")
            return result

        except Exception as e:
            print(f"[ERROR] Failed to show multiple display dialog: {e}")
            import traceback

            print(f"[ERROR] Full traceback: {traceback.format_exc()}")

            # Fallback to system notification if dialog fails
            print(f"[DIALOGS] Falling back to system notification...")
            title = MULTI_DISPLAY_TITLE
            subtitle = EXIT_APP_BUTTON
            message = f"Detected {display_count} displays. The app will exit in 3 seconds."

            print(f"[DIALOGS] Showing system notification: {title} - {message}")
            rumps.notification(
                title,
                subtitle,
                message,
                sound=True,
            )
            print(f"[DIALOGS] System notification sent")
            return None

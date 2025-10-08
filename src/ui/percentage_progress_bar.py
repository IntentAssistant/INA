from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QBrush, QColor, QPen

RATING_LABELS = {
    1: "Not aligned at all",
    2: "Barely aligned",
    3: "Somewhat aligned",
    4: "Mostly aligned",
    5: "Fully aligned",
}


class CheckboxRatingWidget(QWidget):
    """Custom checkbox-based rating widget with text labels"""

    value_changed = pyqtSignal(int)  # Emits rating (1-5)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_rating = -1  # Start with no selection (-1 means nothing selected)
        self.checkboxes = []
        self.setup_ui()

    def setup_ui(self):
        """Setup the checkbox rating interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 20)
        layout.setSpacing(12)

        # Define rating options with their corresponding values
        self.rating_options = [
            {"rating": rating, "label": label} for rating, label in RATING_LABELS.items()
        ]

        # Create checkboxes for each rating option
        for option in self.rating_options:
            checkbox_container = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_container)
            checkbox_layout.setContentsMargins(15, 6, 15, 6)
            checkbox_layout.setSpacing(16)

            # Create checkbox
            checkbox = QCheckBox()
            checkbox.setFixedSize(28, 28)
            checkbox.setStyleSheet(
                """
                QCheckBox::indicator {
                    width: 22px;
                    height: 22px;
                    border-radius: 11px;
                    border: 2px solid #8E8E93;
                    background-color: #2C2C2E;
                }
                QCheckBox::indicator:checked {
                    border: 2px solid #0A84FF;
                    background-color: #0A84FF;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xMC42IDFMMy45IDcuN0wxLjQgNS4yIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
                }
                QCheckBox::indicator:hover {
                    border: 2px solid #0A84FF;
                    background-color: #4A4A4C;
                }
            """
            )

            # Create label
            label = QLabel(option["label"])
            label.setStyleSheet(
                """
                QLabel {
                    color: white;
                    font-size: 14px;
                    font-weight: 400;
                }
            """
            )

            # Enable mouse tracking for hover effect on checkbox only
            checkbox.setMouseTracking(True)
            checkbox.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

            # Connect checkbox signal
            checkbox.clicked.connect(
                lambda checked, rating=option["rating"]: self.on_checkbox_clicked(
                    rating
                )
            )

            # Store checkbox reference
            self.checkboxes.append(
                {
                    "checkbox": checkbox,
                    "rating": option["rating"],
                    "label": label,
                    "container": checkbox_container,
                }
            )

            # Add hover effect for checkbox - when checkbox is hovered, change label color too
            def make_checkbox_hover_handler(lbl, cb):
                def enter_event(event):
                    lbl.setStyleSheet(
                        """
                        QLabel {
                            color: #0A84FF;
                            font-size: 14px;
                            font-weight: 400;
                        }
                    """
                    )

                def leave_event(event):
                    lbl.setStyleSheet(
                        """
                        QLabel {
                            color: white;
                            font-size: 14px;
                            font-weight: 400;
                        }
                    """
                    )

                return enter_event, leave_event

            enter_handler, leave_handler = make_checkbox_hover_handler(label, checkbox)
            checkbox.enterEvent = enter_handler
            checkbox.leaveEvent = leave_handler

            # Layout with center alignment
            checkbox_layout.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
            checkbox_layout.addStretch()

            layout.addWidget(checkbox_container)

    def on_checkbox_clicked(self, rating):
        """Handle checkbox click - only allow one selection"""
        # Uncheck all other checkboxes
        for checkbox_data in self.checkboxes:
            if checkbox_data["rating"] != rating:
                checkbox_data["checkbox"].setChecked(False)

        # Update current rating
        self.current_rating = rating

        # Emit signal
        self.value_changed.emit(rating)

    def set_value(self, rating):
        """Set the current value based on rating (1-5)"""
        # Uncheck all checkboxes first
        for checkbox_data in self.checkboxes:
            checkbox_data["checkbox"].setChecked(False)

        # Check the appropriate checkbox
        if 1 <= rating <= 5:
            for checkbox_data in self.checkboxes:
                if checkbox_data["rating"] == rating:
                    checkbox_data["checkbox"].setChecked(True)
                    break
            self.current_rating = rating
        else:
            self.current_rating = -1  # No selection

    def refresh_language(self):
        """Refresh all text when language changes"""
        # Update existing labels instead of recreating everything
        for i, option in enumerate(self.rating_options):
            if i < len(self.checkboxes):
                checkbox_data = self.checkboxes[i]
                label = checkbox_data["label"]
                label.setText(option["label"])

                # Restore normal color
                label.setStyleSheet(
                    """
                    QLabel {
                        color: white;
                        font-size: 14px;
                        font-weight: 400;
                    }
                """
                )

    def mousePressEvent(self, event):
        """Handle mouse press - prevent dragging"""
        # Prevent event propagation to parent to avoid window dragging
        event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move - prevent dragging"""
        # Prevent event propagation to parent to avoid window dragging
        event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release - prevent dragging"""
        # Prevent event propagation to parent to avoid window dragging
        event.accept()

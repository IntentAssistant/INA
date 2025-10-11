"""
History management functionality for the dashboard
"""

import json
import os
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont

# Import LocalStorage to get proper directory paths
from ..logging.storage import LocalStorage

class TimelineWidget(QWidget):
    """Custom timeline widget with connected circles and lines"""

    # Signal to emit when an intention is clicked
    intention_clicked = pyqtSignal(str, dict)  # intention_text, record_data

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.intention_records = []  # Store original intention records for each item
        self.max_visible_items = 5  # Show up to five items by default
        self.scroll_offset = 0  # Track scroll offset
        self._real_scroll_offset = 0.0  # Floating-point scroll position for smooth scrolling
        self.setFixedHeight(200)  # Keep widget height constant regardless of item count
        self.hovered_item = -1  # Track hovered item for visual feedback

        # Enable mouse wheel events for scrolling
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Set cursor to indicate clickable items
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_max_visible_items(self, count):
        """Set maximum number of visible items"""
        self.max_visible_items = count
        self.update()

    def add_item(self, text, record=None):
        """Add an item to the timeline with associated record data"""
        self.items.insert(0, text)  # Add to beginning (most recent first)
        self.intention_records.insert(0, record)  # Store corresponding record

        # Keep the full history but display only up to max_visible_items
        if len(self.items) > 100:  # Limit total history to 100 entries
            self.items = self.items[:100]
            self.intention_records = self.intention_records[:100]

        # Set scroll to show most recent items (bottom of the list)
        if len(self.items) > self.max_visible_items:
            self.scroll_offset = len(self.items) - self.max_visible_items
        else:
            self.scroll_offset = 0
        self.update()  # Trigger repaint

    def clear_items(self):
        """Clear all items"""
        self.items = []
        self.intention_records = []
        self.scroll_offset = 0
        self.update()

    def reset_scroll_to_latest(self):
        """Reset scroll to show the most recent items"""
        if len(self.items) > self.max_visible_items:
            self.scroll_offset = len(self.items) - self.max_visible_items
        else:
            self.scroll_offset = 0
        self.update()

    def wheelEvent(self, event):
        """Handle mouse wheel scrolling"""
        if len(self.items) <= self.max_visible_items:
            return  # No need to scroll if all items fit

        # Calculate scroll direction and step
        delta = event.angleDelta().y()

        # Use a smaller step to slow the scroll speed
        scroll_step = 0.3 if abs(delta) < 120 else 0.5  # Previously 1 or 2

        # Floating scroll offset to support fractional steps
        if not hasattr(self, "_real_scroll_offset"):
            self._real_scroll_offset = float(self.scroll_offset)

        # Apply smooth scrolling
        if delta > 0:  # Scroll up
            self._real_scroll_offset = max(0, self._real_scroll_offset - scroll_step)
        else:  # Scroll down
            max_offset = max(0, len(self.items) - self.max_visible_items)
            self._real_scroll_offset = min(
                max_offset, self._real_scroll_offset + scroll_step
            )

        # Convert floating offset to integer index
        new_offset = int(self._real_scroll_offset)

        # Update only when the offset changes
        if new_offset != self.scroll_offset:
            self.scroll_offset = new_offset
            self.update()  # Repaint only when changed

        event.accept()

    def paintEvent(self, event):
        """Custom paint event to draw the timeline"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.items:
            return

        # Timeline styling
        circle_radius = 6  # Slightly smaller circle radius
        line_color = QColor("#007AFF")  # Blue color
        circle_color = QColor("#007AFF")
        text_color = QColor("#FFFFFF")

        # Calculate positions and adjust spacing
        margin_left = 16  # Reduce left margin
        margin_top = 10  # Reduce top margin
        item_height = 32  # Increase vertical spacing to fit long text
        margin_bottom = 15  # Bottom margin

        # Get visible items based on scroll offset
        start_index = self.scroll_offset
        end_index = min(start_index + self.max_visible_items, len(self.items))
        visible_items = self.items[start_index:end_index]

        for i, item in enumerate(visible_items):
            y_pos = margin_top + (i * item_height)

            # Draw hover background for hovered item
            if i == self.hovered_item:
                painter.fillRect(
                    0,
                    y_pos - circle_radius - 2,
                    self.width(),
                    item_height,
                    QColor(255, 255, 255, 30),  # Semi-transparent white highlight
                )

            # Draw connecting line (except for the first visible item)
            if i > 0:
                pen = QPen(line_color, 2)
                painter.setPen(pen)
                painter.drawLine(
                    margin_left + circle_radius,
                    y_pos - item_height + circle_radius,
                    margin_left + circle_radius,
                    y_pos - circle_radius,
                )
            # Draw connecting line to previous item if this is first visible but not first overall
            elif start_index > 0:
                pen = QPen(line_color, 2)
                painter.setPen(pen)
                painter.drawLine(
                    margin_left + circle_radius,
                    0,  # Start from top of widget
                    margin_left + circle_radius,
                    y_pos - circle_radius,
                )

            # Draw circle with hover effect
            circle_pen_color = (
                QColor("#00AAFF") if i == self.hovered_item else circle_color
            )
            painter.setPen(QPen(circle_pen_color, 2))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))  # No fill
            painter.drawEllipse(
                margin_left, y_pos - circle_radius, circle_radius * 2, circle_radius * 2
            )

            # Draw text with word wrapping for long text
            painter.setPen(QPen(text_color))

            # Set smaller font for better fit
            font = painter.font()
            font.setPointSize(11)  # Slightly smaller font
            painter.setFont(font)

            # Calculate text area
            text_x = margin_left + circle_radius * 2 + 8
            text_width = (
                self.width() - text_x - 20
            )  # Leave more margin on right for scroll indicator

            # Use elided text if too long
            metrics = painter.fontMetrics()
            elided_text = metrics.elidedText(
                item, Qt.TextElideMode.ElideRight, text_width
            )

            painter.drawText(
                text_x,
                y_pos + metrics.height() // 4,
                elided_text,
            )

        # Draw scroll indicator if there are more items
        if len(self.items) > self.max_visible_items:
            self.draw_scroll_indicator(painter)

    def draw_scroll_indicator(self, painter):
        """Draw scroll indicator to show there are more items"""
        indicator_width = 4
        indicator_height = 60
        indicator_x = self.width() - 8
        indicator_y = 20

        # Background track
        painter.setPen(QPen(QColor("#3C3C3C"), 2))
        painter.drawLine(
            indicator_x, indicator_y, indicator_x, indicator_y + indicator_height
        )

        # Calculate thumb position and size
        total_items = len(self.items)
        visible_ratio = self.max_visible_items / total_items
        thumb_height = max(10, int(indicator_height * visible_ratio))

        scroll_ratio = (
            self.scroll_offset / (total_items - self.max_visible_items)
            if total_items > self.max_visible_items
            else 0
        )
        thumb_y = indicator_y + int((indicator_height - thumb_height) * scroll_ratio)

        # Draw thumb
        painter.setPen(QPen(QColor("#007AFF"), 3))
        painter.drawLine(indicator_x, thumb_y, indicator_x, thumb_y + thumb_height)

    def mousePressEvent(self, event):
        """Handle mouse click to select intention from history"""
        if event.button() == Qt.MouseButton.LeftButton:
            clicked_index = self.get_clicked_item_index(event.pos())
            if clicked_index is not None:
                # Get the actual record index considering scroll offset
                actual_index = self.scroll_offset + clicked_index
                if actual_index < len(self.intention_records):
                    record = self.intention_records[actual_index]
                    if record:
                        intention = record.get("intention", "")
                        print(f"[HISTORY] User clicked on intention: {intention}")
                        # Emit signal with intention and record data
                        self.intention_clicked.emit(intention, record)

        # Prevent event propagation to parent to avoid window dragging
        event.accept()

    def get_clicked_item_index(self, pos):
        """Get the index of the clicked item based on mouse position"""
        margin_top = 10
        item_height = 32

        # Calculate which item was clicked based on Y position
        y = pos.y()
        if y < margin_top:
            return None

        item_index = int((y - margin_top) / item_height)

        # Check if click is within valid range
        visible_item_count = min(
            self.max_visible_items, len(self.items) - self.scroll_offset
        )
        if 0 <= item_index < visible_item_count:
            return item_index
        return None

    def mouseMoveEvent(self, event):
        """Handle mouse move to show hover effects"""
        hovered_index = self.get_clicked_item_index(event.pos())
        if hovered_index != self.hovered_item:
            self.hovered_item = hovered_index
            self.update()  # Trigger repaint to show hover effect

        # Prevent dragging by accepting the event and not calling parent
        event.accept()

    def leaveEvent(self, event):
        """Handle mouse leave to clear hover effects"""
        self.hovered_item = -1
        self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release - prevent dragging"""
        # Prevent event propagation to parent to avoid window dragging
        event.accept()


class HistoryManager:
    """Manages intention history data and operations"""

    def __init__(self, history_file_path=None):
        # Use LocalStorage to get the proper directory path
        self.storage = LocalStorage()

        # Set history file path to the intention_history directory
        if history_file_path:
            # If a specific path is provided, use it (for backward compatibility)
            self.history_file = history_file_path
        else:
            # Use the new intention_history directory
            self.history_file = os.path.join(
                self.storage.get_intention_history_dir(), "intention_history.json"
            )

        self.real_intention_history = []
        self.current_session = None
        self.load_intention_history()

    def load_intention_history(self):
        """Load intention history from JSON file"""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        loaded_records = json.loads(content)
                    else:
                        loaded_records = []
                        print("[HISTORY] History file was empty, starting fresh")
            else:
                loaded_records = []
                print("[HISTORY] No existing history file found, starting fresh")
                # Create empty history file
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)

            # Process records and remove duplicates
            unique_records = []
            seen_ids = set()

            for record in loaded_records:
                record_id = (record.get("timestamp", ""), record.get("intention", ""))
                if record_id not in seen_ids:
                    unique_records.append(record)
                    seen_ids.add(record_id)

            self.real_intention_history = unique_records
            print(
                f"[HISTORY] Loaded {len(self.real_intention_history)} intention records"
            )

            # Return success status for UI updates
            return True

        except FileNotFoundError:
            # File doesn't exist yet - that's normal for first run
            print("[HISTORY] No existing history file found, starting fresh")
            self.real_intention_history = []
            # Create empty history file
            try:
                os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[ERROR] Failed to create history file: {e}")
            return True
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in history file: {e}")
            # Backup corrupted file and start fresh
            try:
                backup_file = self.history_file + ".backup"
                os.rename(self.history_file, backup_file)
                print(f"[HISTORY] Corrupted file backed up to: {backup_file}")
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                self.real_intention_history = []
                return True
            except Exception as backup_error:
                print(f"[ERROR] Failed to backup corrupted file: {backup_error}")
                self.real_intention_history = []
                return False
        except Exception as e:
            print(f"[ERROR] Loading history: {e}")
            self.real_intention_history = []
            return False

    def save_intention_history(self):
        """Save intention history to JSON file"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.real_intention_history, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(self.real_intention_history)} intention records")
        except Exception as e:
            print(f"Error saving history: {e}")

    def start_intention_session(self, intention, session_id=None):
        """Start a new intention session"""
        self.current_session = {
            "intention": intention,
            "session_id": session_id,  # Add session_id for mapping with clarification
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_minutes": None,
        }
        print(f"Started session: {intention} (session_id: {session_id})")
        return self.current_session

    def end_intention_session(self):
        """End the current intention session"""
        if self.current_session:
            end_time = datetime.now()
            start_time = datetime.fromisoformat(self.current_session["start_time"])
            duration = end_time - start_time
            duration_minutes = round(duration.total_seconds() / 60, 1)

            self.current_session["end_time"] = end_time.isoformat()
            self.current_session["duration_minutes"] = duration_minutes

            # Add to history (most recent first)
            self.real_intention_history.insert(0, self.current_session.copy())

            # Keep only last 50 records
            if len(self.real_intention_history) > 50:
                self.real_intention_history = self.real_intention_history[:50]

            # Save to file
            self.save_intention_history()

            print(
                f"Ended session: {self.current_session['intention']} ({duration_minutes} min)"
            )
            self.current_session = None
            return True
        return False

    def format_duration(self, duration_minutes):
        """Format duration from minutes to hours:minutes format"""
        if duration_minutes is None:
            return "in progress..."

        hours = int(duration_minutes // 60)
        minutes = int(duration_minutes % 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def get_today_records(self):
        """Get today's intention records"""
        today = datetime.now().date()
        today_records = []

        for record in self.real_intention_history:
            start_time = record.get("start_time")
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    if start_dt.date() == today:
                        today_records.append(record)
                except:
                    continue  # Skip invalid dates

        # Sort by start_time to ensure most recent is first
        return sorted(
            today_records,
            key=lambda x: x.get("start_time", ""),
            reverse=True,
        )

    def format_record_for_display(self, record):
        """Format a single record for timeline display"""
        intention = record["intention"]
        duration = record.get("duration_minutes")
        start_time = record.get("start_time")
        end_time = record.get("end_time")

        # Format time display
        time_display = ""
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                start_str = start_dt.strftime("%H:%M")

                if end_time:
                    end_dt = datetime.fromisoformat(end_time)
                    end_str = end_dt.strftime("%H:%M")
                    time_display = f"{start_str}-{end_str}"
                else:
                    time_display = f"{start_str}-now"
            except:
                time_display = "time unknown"

        # Format duration
        if duration is not None:
            duration_str = self.format_duration(duration)
            return f"{time_display} | {intention} ({duration_str})"
        else:
            return f"{time_display} | {intention} (in progress...)"

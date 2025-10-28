"""
History management functionality for the dashboard
"""

import json
import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QLinearGradient

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

    @staticmethod
    def _extract_inverted_values(record):
        """Return inverted score values (0-1, where 1 = focused) from record samples"""
        if not record:
            return []

        samples = record.get("score_samples") or []
        values = []
        for sample in samples:
            if isinstance(sample, dict):
                score = sample.get("score")
            else:
                score = sample
            try:
                raw = float(score)
            except (TypeError, ValueError):
                continue
            inverted = max(0.0, min(1.0, 1.0 - raw))
            values.append(inverted)

        return values

    @staticmethod
    def _color_for_ratio(ratio: float) -> QColor:
        """Return QColor for 0.0 (poor) -> red, 0.5 -> yellow, 1.0 (excellent) -> green"""
        ratio = max(0.0, min(1.0, ratio))

        # Define key colors
        red = (255, 94, 87)  # #FF5E57
        yellow = (255, 214, 10)  # #FFD60A
        green = (40, 167, 69)  # #28A745

        if ratio <= 0.5:
            t = ratio / 0.5
            r = int(red[0] + (yellow[0] - red[0]) * t)
            g = int(red[1] + (yellow[1] - red[1]) * t)
            b = int(red[2] + (yellow[2] - red[2]) * t)
        else:
            t = (ratio - 0.5) / 0.5
            r = int(yellow[0] + (green[0] - yellow[0]) * t)
            g = int(yellow[1] + (green[1] - yellow[1]) * t)
            b = int(yellow[2] + (green[2] - yellow[2]) * t)

        return QColor(r, g, b)

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

        sparkline_width = 70
        sparkline_height = 18
        average_width = 46
        right_margin = 14

        for i, item in enumerate(visible_items):
            y_pos = margin_top + (i * item_height)
            record_index = start_index + i
            record = (
                self.intention_records[record_index]
                if 0 <= record_index < len(self.intention_records)
                else None
            )
            raw_values = record.get("score_samples") if record else []
            resampled_values = HistoryManager._resample_scores(raw_values)
            if resampled_values:
                inverted_values = [max(0.0, min(1.0, 1.0 - val)) for val in resampled_values]
            else:
                inverted_values = []

            if len(inverted_values) > 40:
                inverted_values = inverted_values[-40:]

            average_percent = None
            if record:
                average_percent = record.get("focus_inverted_average")
            if average_percent is None and inverted_values:
                average_percent = round(sum(inverted_values) / len(inverted_values) * 100)

            if average_percent is None and inverted_values:
                avg_ratio = sum(inverted_values) / len(inverted_values)
            elif average_percent is not None:
                avg_ratio = average_percent / 100.0
            else:
                avg_ratio = 0.0
            path_color = self._color_for_ratio(avg_ratio)

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
            base_font = painter.font()
            base_font.setPointSize(11)
            painter.setFont(base_font)

            # Calculate text area (leave space for sparkline and average)
            text_x = margin_left + circle_radius * 2 + 8
            text_width = (
                self.width() - text_x - right_margin - sparkline_width - average_width
            )
            if text_width < 60:
                text_width = self.width() - text_x - right_margin

            metrics = painter.fontMetrics()
            elided_text = metrics.elidedText(
                item, Qt.TextElideMode.ElideRight, text_width
            )

            painter.drawText(
                text_x,
                y_pos + metrics.height() // 4,
                elided_text,
            )

            # Draw sparkline if samples exist
            spark_x = self.width() - right_margin - average_width - sparkline_width
            spark_top = y_pos - sparkline_height / 2
            spark_bottom = spark_top + sparkline_height
            if inverted_values:
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

                # Draw subtle baseline
                baseline_pen = QPen(QColor("#3C3C3C"), 1)
                painter.setPen(baseline_pen)
                painter.drawLine(
                    int(round(spark_x)),
                    int(round(spark_bottom)),
                    int(round(spark_x + sparkline_width)),
                    int(round(spark_bottom)),
                )

                # Draw sparkline path
                # Build segments with per-point color
                step = sparkline_width / max(1, len(inverted_values) - 1)
                prev_x = spark_x
                prev_y = spark_bottom - inverted_values[0] * sparkline_height

                for idx, value in enumerate(inverted_values[1:], 1):
                    cur_x = spark_x + step * idx
                    cur_y = spark_bottom - value * sparkline_height

                    # Color based on midpoint value
                    midpoint = (inverted_values[idx - 1] + value) / 2.0
                    color = self._color_for_ratio(midpoint)
                    seg_pen = QPen(color, 2)
                    seg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    painter.setPen(seg_pen)
                    painter.drawLine(
                        int(round(prev_x)),
                        int(round(prev_y)),
                        int(round(cur_x)),
                        int(round(cur_y)),
                    )

                    prev_x, prev_y = cur_x, cur_y

                # If only one point, draw a short horizontal line
                if len(inverted_values) == 1:
                    base_color = self._color_for_ratio(inverted_values[0])
                    base_pen = QPen(base_color, 2)
                    base_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    painter.setPen(base_pen)
                    painter.drawLine(
                        int(round(prev_x - 1)),
                        int(round(prev_y)),
                        int(round(prev_x + 1)),
                        int(round(prev_y)),
                    )

                painter.restore()

            # Draw average percentage on the right
            avg_text = "--" if average_percent is None else f"{int(average_percent):02d}%"
            avg_font = QFont(base_font)
            avg_font.setPointSize(10)
            painter.setFont(avg_font)
            avg_metrics = painter.fontMetrics()
            avg_x = self.width() - right_margin - avg_metrics.horizontalAdvance(avg_text)
            painter.drawText(
                avg_x,
                y_pos + avg_metrics.height() // 4,
                avg_text,
            )

            # Restore base font for next iteration
            painter.setFont(base_font)

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
            for record in self.real_intention_history:
                if "score_samples" not in record:
                    record["score_samples"] = []
                if "focus_inverted_average" not in record:
                    record["focus_inverted_average"] = self._compute_inverted_average(
                        record.get("score_samples", [])
                    )

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
            "score_samples": [],
            "focus_inverted_average": None,
        }
        print(f"Started session: {intention} (session_id: {session_id})")
        return self.current_session

    def record_focus_score(self, raw_score, timestamp=None):
        """Record a raw focus score sample for the current session"""
        if not self.current_session:
            return

        try:
            raw_value = float(raw_score)
        except (TypeError, ValueError):
            return

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        sample = {"timestamp": timestamp, "score": raw_value}
        samples = self.current_session.setdefault("score_samples", [])
        samples.append(sample)

    @staticmethod
    def _resample_scores(samples, max_points=40):
        """Resample score list to even time buckets (default 1-minute granularity)."""
        if not samples:
            return []

        # Convert ISO timestamps to datetime objects
        converted = []
        for entry in samples:
            if isinstance(entry, dict):
                ts = entry.get("timestamp")
                score = entry.get("score")
            else:
                ts, score = entry
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts)
                converted.append((dt, float(score)))
            except Exception:
                continue

        if not converted:
            return []

        converted.sort(key=lambda x: x[0])
        start, end = converted[0][0], converted[-1][0]
        duration = (end - start).total_seconds()

        # If duration is tiny or points already small, just return raw values
        if duration <= 60 or len(converted) <= max_points:
            return [max(0.0, min(1.0, val)) for _, val in converted]

        # Determine bucket size (seconds) to keep <= max_points
        bucket_seconds = max(60, duration / max_points)

        buckets = []
        bucket_start = start
        bucket_scores = []
        idx = 0
        total = len(converted)

        while bucket_start <= end:
            bucket_end = bucket_start + timedelta(seconds=bucket_seconds)
            bucket_scores.clear()

            while idx < total and converted[idx][0] < bucket_end:
                bucket_scores.append(converted[idx][1])
                idx += 1

            if bucket_scores:
                buckets.append(sum(bucket_scores) / len(bucket_scores))
            else:
                # Carry last known value to avoid gaps
                last_value = buckets[-1] if buckets else converted[-1][1]
                buckets.append(last_value)

            bucket_start = bucket_end

            if idx >= total and bucket_start > end:
                break

        return [max(0.0, min(1.0, val)) for val in buckets]

    @staticmethod
    def _compute_inverted_average(samples):
        """Compute inverted average percentage from raw samples"""
        if not samples:
            return None

        values = []
        for sample in samples:
            if isinstance(sample, dict):
                score = sample.get("score")
            else:
                score = sample
            try:
                value = float(score)
            except (TypeError, ValueError):
                continue
            values.append(value)

        if not values:
            return None

        inverted_values = [max(0.0, min(1.0, 1.0 - val)) for val in values]
        if not inverted_values:
            return None

        return round(sum(inverted_values) / len(inverted_values) * 100)

    def end_intention_session(self):
        """End the current intention session"""
        if self.current_session:
            end_time = datetime.now()
            start_time = datetime.fromisoformat(self.current_session["start_time"])
            duration = end_time - start_time
            duration_minutes = round(duration.total_seconds() / 60, 1)

            self.current_session["end_time"] = end_time.isoformat()
            self.current_session["duration_minutes"] = duration_minutes

            # Compute inverted average (0 -> 100, 1 -> 0)
            samples = self.current_session.get("score_samples", [])
            inverted_average = self._compute_inverted_average(samples)
            self.current_session["focus_inverted_average"] = inverted_average

            # Add to history (most recent first)
            record_copy = self.current_session.copy()
            # Ensure score samples are copied by value
            record_copy["score_samples"] = [
                sample.copy() for sample in self.current_session.get("score_samples", [])
            ]
            self.real_intention_history.insert(0, record_copy)

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

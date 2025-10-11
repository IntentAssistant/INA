import io
import os
import sys
import glob
import json
import subprocess
import base64
import requests
from datetime import datetime
from PIL import Image


from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QWidget, QApplication


class IndicatorWidget(QWidget):
    def __init__(self, geometry):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(geometry.width(), geometry.height())
        self.setGeometry(geometry)

        # macOS-specific window configuration
        if sys.platform == "darwin":
            try:
                from AppKit import (
                    NSApp,
                    NSWindow,
                    NSScreenSaverWindowLevel,
                    NSWindowCollectionBehaviorCanJoinAllSpaces,
                    NSWindowCollectionBehaviorStationary,
                    NSWindowCollectionBehaviorIgnoresCycle,
                )

                self.show()
                windows = NSApp.windows()
                if windows:
                    window = windows[-1]
                    window.setLevel_(NSScreenSaverWindowLevel + 1)

                    behavior = (
                        NSWindowCollectionBehaviorCanJoinAllSpaces
                        | NSWindowCollectionBehaviorStationary
                        | NSWindowCollectionBehaviorIgnoresCycle
                    )
                    window.setCollectionBehavior_(behavior)

                    window.setStyleMask_(window.styleMask() & ~(1 << 3))

                    window.setHidesOnDeactivate_(False)
            except ImportError:
                self.show()
        else:
            self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor(255, 0, 0, 150))
        pen.setWidth(2)
        painter.setPen(pen)

        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

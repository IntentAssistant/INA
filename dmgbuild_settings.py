# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

# --- Basic Settings (Hardcoded for Intent Assistant) ---
app_name = "Intent Assistant"
application = f"dist/{app_name}.app"
appname = os.path.basename(application)

# --- Files and Symlinks ---
files = [application]
symlinks = {"Applications": "/Applications"}

# --- Icon Settings ---
icon = "src/assets/INA.png"

# --- Window Configuration ---
background = "build_assets/dmg_background.png"
window_rect = ((100, 100), (640, 280))
default_view = "icon-view"

# --- Icon View Settings ---
icon_size = 128
text_size = 16
icon_locations = {appname: (140, 120), "Applications": (500, 120)}

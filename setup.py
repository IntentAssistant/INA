from setuptools import setup
import os

# --- App Configuration (Hardcoded for INA) ---
APP_NAME = "INA"
APP_SCRIPT = "main.py"
BUNDLE_ID = "com.ina.app"
ICON_PATH = "src/assets/INA.png"
APP_VERSION = "0.5.0"

# --- Collect all asset files ---
assets_dir = "src/assets"
asset_files = []
if os.path.exists(assets_dir):
    asset_files = [
        os.path.join(assets_dir, f)
        for f in os.listdir(assets_dir)
        if os.path.isfile(os.path.join(assets_dir, f))
    ]
DATA_FILES = [("assets", asset_files)] if asset_files else []

# Add a placeholder for the config directory.
# This ensures that py2app creates a 'config' folder in the Resources directory
# of the .app bundle, where runtime-generated files can be stored.
DATA_FILES.append((".config", []))

# --- py2app Options ---
OPTIONS = {
    "argv_emulation": True,
    "iconfile": ICON_PATH,
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": APP_VERSION,
        "CFBundleShortVersionString": APP_VERSION,
        "LSMinimumSystemVersion": "10.15",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "NSHumanReadableCopyright": "Copyright © 2025 Intentional Computing . All rights reserved.",
        "NSScreenCaptureUsageDescription": "INA captures your screen to help you stay focused on your intentions.",
    },
    # Standard packages that are easy for py2app to find
    "packages": [
        "rumps",
        "PyQt6",
        "desktop_notifier",
        "psutil",
        "requests",
        "charset_normalizer",
        "certifi",
        "sentencepiece",
    ],
    # Force-include modules/packages that py2app has trouble finding
    "includes": [
        "src",
        "desktop_notifier.resources",
        "google.auth",
        "google.api_core",
        "google.ai.generativelanguage",
        "google.generativeai",
        "google.genai",
        "objc",
    ],
    "site_packages": True,
}

# Add optional frameworks (e.g., libffi) if provided
frameworks = []
libffi_path = os.environ.get("LIBFFI_PATH")
if libffi_path:
    if os.path.exists(libffi_path):
        frameworks.append(libffi_path)
    else:
        print(f"[WARN] LIBFFI_PATH was set but not found: {libffi_path}")
        print("[WARN] The packaged app may fail to load _ctypes without libffi.")
if frameworks:
    OPTIONS["frameworks"] = frameworks

# --- Setup ---
setup(
    name=APP_NAME,
    app=[APP_SCRIPT],
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

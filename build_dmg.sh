#!/bin/bash

# --- INA App DMG Builder (Simplified) ---
# Usage: ./build_dmg.sh

# --- 0. Determine Python interpreter ---
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
else
    PYTHON_BIN="$(command -v python3)"
fi

if [ ! -x "$PYTHON_BIN" ]; then
    echo "❌ Could not locate a Python interpreter. Activate your virtual environment first."
    exit 1
fi

echo "Using Python interpreter: $PYTHON_BIN"

# --- 1. Cleanup ---
echo "Cleaning previous build files..."
rm -rf dist build
sudo rm -rf "/Applications/INA.app" 2>/dev/null
tccutil reset All "com.ina.app" 2>/dev/null
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# --- 2. Generate DMG Background ---
if [ -f "create_dmg_background.py" ]; then
    echo "Generating DMG background image..."
    "$PYTHON_BIN" create_dmg_background.py
fi

# --- 3. Locate libffi (required for _ctypes inside the app bundle) ---
LIBFFI_PATH=$("$PYTHON_BIN" - <<'PY'
import sys
from pathlib import Path

candidates = []
exe = Path(sys.executable).resolve()

# Search upwards from the Python executable for a lib directory containing libffi
for parent in exe.parents:
    lib_dir = parent / "lib"
    for name in ("libffi.8.dylib", "libffi.7.dylib", "libffi.dylib"):
        candidate = lib_dir / name
        if candidate.exists():
            print(candidate)
            raise SystemExit

# Check common Homebrew locations
for base in (Path("/opt/homebrew/opt/libffi/lib"), Path("/usr/local/opt/libffi/lib")):
    for name in ("libffi.8.dylib", "libffi.dylib"):
        candidate = base / name
        if candidate.exists():
            print(candidate)
            raise SystemExit

# Nothing found
PY
)

if [ -n "$LIBFFI_PATH" ]; then
    export LIBFFI_PATH
    echo "Found libffi at: ${LIBFFI_PATH}"
else
    echo "⚠️  Could not automatically locate libffi."
    echo "    Set LIBFFI_PATH to the full path of libffi.dylib before rerunning this script."
fi

# --- 5. Build the App ---
echo "Building INA.app..."
"$PYTHON_BIN" setup.py py2app

# --- 6. Build the DMG ---
if [ -d "dist/INA.app" ]; then
    APP_VERSION=$("$PYTHON_BIN" -c "from src.config.constants import APP_VERSION; print(APP_VERSION)")
    echo "Building DMG file for INA v${APP_VERSION}..."
    "$PYTHON_BIN" -m dmgbuild -s dmgbuild_settings.py "INA" "dist/INA-v${APP_VERSION}.dmg"
    echo "✅ INA DMG created successfully!"
else
    echo "❌ Build failed: INA.app was not created."
    exit 1
fi

# --- 7. Final Summary ---
echo ""
echo "🎉 Build complete!"
echo "You can find the DMG in the 'dist/' directory."
ls -la dist/*.dmg

#!/bin/bash

# --- Intent Assistant DMG Builder ---
# Usage: ./build_dmg.sh

# --- 0. Load code signing configuration (optional) ---
if [ -f "codesign_config.sh" ]; then
    echo "Loading code signing configuration..."
    source codesign_config.sh
    ENABLE_CODESIGN=true
else
    ENABLE_CODESIGN=false
fi

# --- 1. Determine Python interpreter ---
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [ -d ".venv" ] && [ -x ".venv/bin/python" ]; then
    echo "⚠️  Virtual environment found but not activated!"
    echo "   Activating .venv automatically..."
    source .venv/bin/activate
    PYTHON_BIN=".venv/bin/python"
else
    PYTHON_BIN="$(command -v python3)"
    echo "⚠️  WARNING: Using system Python. This may fail if dependencies are not installed."
    echo "   Consider activating a virtual environment first: source .venv/bin/activate"
fi

if [ ! -x "$PYTHON_BIN" ]; then
    echo "❌ Could not locate a Python interpreter."
    exit 1
fi

echo "Using Python interpreter: $PYTHON_BIN"

# Verify required packages are installed
if ! "$PYTHON_BIN" -c "import rumps" 2>/dev/null; then
    echo "❌ Required package 'rumps' not found!"
    echo "   Please activate your virtual environment:"
    echo "   source .venv/bin/activate"
    echo "   Or install dependencies:"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# --- 2. Cleanup ---
echo "Cleaning previous build files..."
rm -rf dist build
sudo rm -rf "/Applications/Intent Assistant.app" 2>/dev/null
sudo rm -rf "/Applications/INA.app" 2>/dev/null  # Remove old name if exists
tccutil reset All "com.intentassistant.app" 2>/dev/null
tccutil reset All "com.ina.app" 2>/dev/null  # Reset old bundle ID
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# --- 3. Generate DMG Background ---
if [ -f "create_dmg_background.py" ]; then
    echo "Generating DMG background image..."
    "$PYTHON_BIN" create_dmg_background.py
fi

# --- 4. Locate libffi (required for _ctypes inside the app bundle) ---
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
echo "Building Intent Assistant.app..."
"$PYTHON_BIN" setup.py py2app

# --- 6. Code Sign the App ---
if [ "$ENABLE_CODESIGN" = true ] && [ -d "dist/Intent Assistant.app" ]; then
    echo "Signing Intent Assistant.app..."
    
    # Create entitlements file
    ENTITLEMENTS_FILE="build/entitlements.plist"
    mkdir -p build
    cat > "$ENTITLEMENTS_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
EOF
    
    # Sign all libraries and frameworks RECURSIVELY
    echo "  - Signing all binaries (this may take several minutes)..."
    
    # Find ALL binary files: .dylib, .so, and executable files in frameworks
    echo "    Finding all binary files..."

    # Handle binaries vendored inside zipped Python stdlib archives (e.g. Pillow .dylibs)
    PYTHON_LIB_DIR="dist/Intent Assistant.app/Contents/Resources/lib"
    if [ -d "$PYTHON_LIB_DIR" ]; then
        find "$PYTHON_LIB_DIR" -maxdepth 1 -name "python*.zip" -print0 | while IFS= read -r -d '' python_zip; do
            echo "    Preparing $(basename "$python_zip") for signing..."
            ZIP_TMP=$(mktemp -d "/tmp/intent_zip_sign.XXXXXX")
            if ditto -x -k "$python_zip" "$ZIP_TMP" 2>/dev/null; then
                find "$ZIP_TMP" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 | while IFS= read -r -d '' inner_file; do
                    if file "$inner_file" | grep -q "Mach-O"; then
                        codesign --force --sign "$CODESIGN_IDENTITY" --timestamp --options runtime "$inner_file" 2>&1 | grep -v "replacing existing signature" || true
                    fi
                done
                SIGNED_ZIP="${python_zip}.signed"
                ZIP_SRC="$ZIP_TMP" ZIP_TARGET="$SIGNED_ZIP" "$PYTHON_BIN" - <<'PY'
import os
import zipfile
from pathlib import Path

src = Path(os.environ["ZIP_SRC"])
target = Path(os.environ["ZIP_TARGET"])

with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for path in src.rglob("*"):
        if path.is_file():
            zf.write(path, path.relative_to(src))
PY
                if [ -f "$SIGNED_ZIP" ]; then
                    mv "$SIGNED_ZIP" "$python_zip"
                else
                    echo "      ⚠️ Failed to rebuild $(basename "$python_zip"); keeping original archive."
                fi
            else
                echo "      ⚠️ Failed to extract $(basename "$python_zip"); skipping embedded binaries."
            fi
            rm -rf "$ZIP_TMP"
        done
    fi
    
    # Sign ALL .dylib and .so files recursively
    echo "    Signing all .dylib and .so files..."
    BINARY_COUNT=$(find "dist/Intent Assistant.app" -type f \( -name "*.dylib" -o -name "*.so" \) | wc -l | tr -d ' ')
    echo "    Found $BINARY_COUNT library files to sign"
    
    find "dist/Intent Assistant.app" -type f \( -name "*.dylib" -o -name "*.so" \) | while read -r file; do
        codesign --force --sign "$CODESIGN_IDENTITY" --timestamp --options runtime "$file" 2>&1 | grep -v "replacing existing signature" || true
    done
    
    echo "    ✓ Library files signed"
    
    # Sign Framework executables (files without extension inside Frameworks)
    echo "    Signing Framework executables..."
    find "dist/Intent Assistant.app" -type f -path "*/Frameworks/*.framework/Versions/*/Qt*" ! -name "*.dylib" ! -name "*.so" | while read -r file; do
        if file "$file" | grep -q "Mach-O"; then
            codesign --force --sign "$CODESIGN_IDENTITY" --timestamp --options runtime "$file" 2>&1 | grep -v "replacing existing signature" || true
        fi
    done
    
    # Also sign other executables in Qt6/lib frameworks
    echo "    Signing Qt6 framework binaries..."
    find "dist/Intent Assistant.app/Contents/Resources/lib/python3.11/PyQt6/Qt6/lib" -type f ! -name "*.dylib" ! -name "*.so" ! -name "*.plist" ! -name "*.qml" | while read -r file; do
        if file "$file" | grep -q "Mach-O"; then
            codesign --force --sign "$CODESIGN_IDENTITY" --timestamp --options runtime "$file" 2>&1 | grep -v "replacing existing signature" || true
        fi
    done
    
    echo "    ✓ All binaries signed"
    
    # Sign the app bundle with entitlements
    echo "  - Signing app bundle..."
    if codesign --force --deep --sign "$CODESIGN_IDENTITY" \
        --timestamp --options runtime \
        --entitlements "$ENTITLEMENTS_FILE" \
        "dist/Intent Assistant.app" 2>&1; then
        
        echo "  - Verifying signature..."
        if codesign --verify --deep --strict --verbose=2 "dist/Intent Assistant.app" 2>&1; then
            echo "✅ Code signing completed and verified"
        else
            echo "⚠️  Signature verification failed!"
            echo "   Continuing anyway, but notarization may fail."
        fi
    else
        echo "❌ Code signing failed!"
        exit 1
    fi
    
    # Cleanup
    rm -f "$ENTITLEMENTS_FILE"
fi

# --- 7. Build the DMG ---
if [ -d "dist/Intent Assistant.app" ]; then
    APP_VERSION=$("$PYTHON_BIN" -c "from src.config.constants import APP_VERSION; print(APP_VERSION)")
    DMG_FILE="dist/IntentAssistant-v${APP_VERSION}.dmg"
    
    echo "Building DMG file for Intent Assistant v${APP_VERSION}..."
    "$PYTHON_BIN" -m dmgbuild -s dmgbuild_settings.py "Intent Assistant" "$DMG_FILE"
    echo "✅ Intent Assistant DMG created successfully!"
    
    # --- 8. Sign and Notarize DMG ---
    if [ "$ENABLE_CODESIGN" = true ]; then
        echo "Signing DMG..."
        if codesign --force --sign "$CODESIGN_IDENTITY" --timestamp "$DMG_FILE" 2>&1; then
            echo "✅ DMG signed"
        else
            echo "❌ DMG signing failed!"
            exit 1
        fi
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🔐 Submitting for notarization..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Submit and capture the submission ID immediately
        echo "Uploading to Apple..."
        SUBMIT_OUTPUT=$(xcrun notarytool submit "$DMG_FILE" \
            --apple-id "$APPLE_ID" \
            --password "$APPLE_APP_PASSWORD" \
            --team-id "$APPLE_TEAM_ID" 2>&1)
        
        echo "$SUBMIT_OUTPUT"
        
        # Extract submission ID
        SUBMISSION_ID=$(echo "$SUBMIT_OUTPUT" | grep "id:" | head -1 | awk '{print $2}')
        
        if [ -z "$SUBMISSION_ID" ]; then
            echo ""
            echo "❌ Failed to submit for notarization!"
            echo "   Check your Apple ID credentials in codesign_config.sh"
            exit 1
        fi
        
        # Save submission ID to file for later check
        SUBMISSION_FILE="dist/.notarization_id"
        echo "$SUBMISSION_ID" > "$SUBMISSION_FILE"
        
        echo ""
        echo "✅ Uploaded successfully!"
        echo "   Submission ID: $SUBMISSION_ID"
        echo "   (Saved to: $SUBMISSION_FILE)"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "⏳ Waiting for Apple to process (typically 5-15 minutes)..."
        echo "   Press Ctrl+C to skip waiting (you can check later)"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Wait for notarization to complete (can be interrupted)
        NOTARIZE_OUTPUT=$(xcrun notarytool wait "$SUBMISSION_ID" \
            --apple-id "$APPLE_ID" \
            --password "$APPLE_APP_PASSWORD" \
            --team-id "$APPLE_TEAM_ID" 2>&1)
        
        WAIT_EXIT_CODE=$?
        
        # If interrupted (Ctrl+C), provide instructions
        if [ $WAIT_EXIT_CODE -ne 0 ]; then
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "⏸️  Waiting interrupted or failed"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            echo "Your DMG has been uploaded and is being processed by Apple."
            echo "To check status later, run:"
            echo ""
            echo "  xcrun notarytool info $SUBMISSION_ID \\"
            echo "    --apple-id $APPLE_ID \\"
            echo "    --password $APPLE_APP_PASSWORD \\"
            echo "    --team-id $APPLE_TEAM_ID"
            echo ""
            echo "Once status is 'Accepted', staple the ticket:"
            echo ""
            echo "  xcrun stapler staple \"$DMG_FILE\""
            echo ""
            exit 0
        fi
        
        echo "$NOTARIZE_OUTPUT"
        
        # Check if notarization succeeded
        if echo "$NOTARIZE_OUTPUT" | grep -q "status: Accepted"; then
            echo ""
            echo "✅ Notarization successful!"
            
            echo "Stapling notarization ticket..."
            if xcrun stapler staple "$DMG_FILE" 2>&1; then
                echo "✅ Ticket stapled successfully!"
                xcrun stapler validate "$DMG_FILE"
                
                echo ""
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo "🎉 DMG signed, notarized, and ready for distribution!"
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            else
                echo "⚠️  Stapling failed, but notarization succeeded."
                echo "   Users can still download and install, but may need internet connection first time."
            fi
        else
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "❌ Notarization FAILED!"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            # Extract submission ID for detailed logs
            SUBMISSION_ID=$(echo "$NOTARIZE_OUTPUT" | grep "id:" | head -1 | awk '{print $2}')
            
            if [ -n "$SUBMISSION_ID" ]; then
                echo ""
                echo "To see detailed error logs, run:"
                echo "  xcrun notarytool log $SUBMISSION_ID \\"
                echo "    --apple-id $APPLE_ID \\"
                echo "    --password $APPLE_APP_PASSWORD \\"
                echo "    --team-id $APPLE_TEAM_ID"
            fi
            
            echo ""
            echo "⚠️  DMG is signed but NOT notarized."
            echo "   Users will see security warnings when opening."
            exit 1
        fi
    fi
else
    echo "❌ Build failed: Intent Assistant.app was not created."
    exit 1
fi

# --- 9. Final Summary ---
echo ""
echo "🎉 Build complete!"
echo "You can find the DMG in the 'dist/' directory."
ls -la dist/*.dmg

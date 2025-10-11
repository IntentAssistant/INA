"""
Auto-login setup utility for Intention App
Automatically adds the app to macOS Login Items on first launch
"""

import os
import sys
import subprocess
import textwrap


def ensure_login_item(app_name="Intention(new)"):
    """
    Ensure the app is added to macOS Login Items

    Args:
        app_name (str): Name of the app to register
    """
    try:
        # Determine .app bundle path when running as a PyInstaller executable
        exec_path = os.path.abspath(sys.argv[0])
        bundle_path = exec_path

        # Ascend directories until we reach the .app bundle
        while not bundle_path.endswith(".app") and bundle_path != "/":
            bundle_path = os.path.dirname(bundle_path)

        # If the bundle cannot be found (for direct Python execution)
        if not bundle_path.endswith(".app"):
            print(
                "[LOGIN] Running from Python directly - skipping login item registration"
            )
            return

        print(f"[LOGIN] App bundle path: {bundle_path}")

        # Check if it is already registered
        login_db = os.path.expanduser(
            "~/Library/Preferences/com.apple.loginitems.plist"
        )
        try:
            if os.path.exists(login_db):
                with open(login_db, "rb") as f:
                    if bundle_path.encode() in f.read():
                        print(f"[LOGIN] {app_name} already registered in login items")
                        return  # Already registered; nothing to do
        except Exception as e:
            print(f"[LOGIN] Could not check existing login items: {e}")
            pass  # Ignore plist parse failures

        # Add to login items via AppleScript
        print(f"[LOGIN] Adding {app_name} to login items...")

        escaped_app_name = app_name.replace('"', '\\"')
        escaped_bundle_path = bundle_path.replace('"', '\\"')

        ascript = textwrap.dedent(
            f'''
            tell application "System Events"
                if not (exists login item "{escaped_app_name}") then
                    make login item at end with properties {{name:"{escaped_app_name}", path:"{escaped_bundle_path}", kind:"Application", hidden:false}}
                end if
            end tell
            '''
        ).strip()

        # Run AppleScript
        result = subprocess.run(
            ["osascript", "-e", ascript], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            print(f"[LOGIN] ✅ Successfully added {app_name} to login items")
            print("[LOGIN] The app will start automatically on next login")
        else:
            print(f"[LOGIN] ❌ Failed to add login item: {result.stderr}")

    except subprocess.TimeoutExpired:
        print(
            "[LOGIN] ⚠️  Timeout waiting for AppleScript - user may need to grant permission"
        )
    except Exception as e:
        print(f"[LOGIN] ❌ Error setting up login item: {e}")


def remove_login_item(app_name="Intention"):
    """
    Remove the app from macOS Login Items

    Args:
        app_name (str): Name of the app to remove
    """
    try:
        print(f"[LOGIN] Removing {app_name} from login items...")

        ascript = f'tell application "System Events" to delete login item "{app_name}"'

        result = subprocess.run(
            ["osascript", "-e", ascript], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            print(f"[LOGIN] ✅ Successfully removed {app_name} from login items")
        else:
            print(
                f"[LOGIN] ⚠️  {app_name} was not found in login items (already removed)"
            )

    except Exception as e:
        print(f"[LOGIN] ❌ Error removing login item: {e}")


if __name__ == "__main__":
    # For manual testing
    ensure_login_item("Intention Test")

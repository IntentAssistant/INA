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
        # PyInstaller 실행 파일 → .app 번들 경로 계산
        exec_path = os.path.abspath(sys.argv[0])
        bundle_path = exec_path

        # .app 번들까지 경로를 찾아 올라감
        while not bundle_path.endswith(".app") and bundle_path != "/":
            bundle_path = os.path.dirname(bundle_path)

        # .app 번들을 찾지 못한 경우 (Python으로 직접 실행 시)
        if not bundle_path.endswith(".app"):
            print(
                "[LOGIN] Running from Python directly - skipping login item registration"
            )
            return

        print(f"[LOGIN] App bundle path: {bundle_path}")

        # 이미 등록되어 있는지 확인
        login_db = os.path.expanduser(
            "~/Library/Preferences/com.apple.loginitems.plist"
        )
        try:
            if os.path.exists(login_db):
                with open(login_db, "rb") as f:
                    if bundle_path.encode() in f.read():
                        print(f"[LOGIN] {app_name} already registered in login items")
                        return  # 이미 있음 → 아무것도 하지 않음
        except Exception as e:
            print(f"[LOGIN] Could not check existing login items: {e}")
            pass  # plist 파싱 실패 시 그냥 진행

        # AppleScript로 로그인 항목에 추가
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

        # AppleScript 실행
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
    # 테스트용
    ensure_login_item("Intention Test")

import subprocess
import Quartz


def get_frontmost_app():
    """Get frontmost app name, with URL if it's a browser"""
    script = 'tell application "System Events" to get name of first process whose frontmost is true'
    result = subprocess.run(
        ["osascript", "-e", script], stdout=subprocess.PIPE, text=True
    )
    app_name = result.stdout.strip()

    # Try to get URL if it's a browser
    url = get_browser_url(app_name)

    if url:
        return f"{app_name} - {url}"
    else:
        return app_name


def get_browser_url(app_name):
    """Get current tab URL from browsers"""
    try:
        if "Google Chrome" in app_name or "Chrome" in app_name:
            script = 'tell application "Google Chrome" to get URL of active tab of front window'
        elif "Safari" in app_name:
            script = (
                'tell application "Safari" to get URL of current tab of front window'
            )
        elif "Firefox" in app_name:
            script = """
            tell application "Firefox"
                tell front window
                    get URL of current tab
                end tell
            end tell
            """
        elif "Microsoft Edge" in app_name or "Edge" in app_name:
            script = 'tell application "Microsoft Edge" to get URL of active tab of front window'
        elif "Arc" in app_name:
            script = 'tell application "Arc" to get URL of active tab of front window'
        elif "Whale" in app_name:
            script = 'tell application "Whale" to get URL of active tab of front window'
        else:
            return None

        result = subprocess.run(
            ["osascript", "-e", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,  # 2-second timeout
        )

        if result.returncode == 0 and result.stdout.strip():
            url = result.stdout.strip()
            # Truncate very long URLs
            if len(url) > 100:
                return url[:97] + "..."
            return url
        else:
            return None

    except Exception as e:
        print(f"Error getting browser URL: {e}")
        return None


def get_chrome_url():
    script = """
    tell application "Google Chrome"
        if not (exists window 1) then return ""
        set currentTab to active tab of front window
        return URL of currentTab
    end tell
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error getting Chrome URL: {e}")
        return ""


def get_safari_url():
    script = """
    tell application "Safari"
        if not (exists window 1) then return ""
        set currentTab to current tab of front window
        return URL of currentTab
    end tell
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error getting Safari URL: {e}")
        return ""


def get_top_app_in_display(display_id):
    try:
        # Get bounds of the display
        display_bounds = Quartz.CGDisplayBounds(display_id)

        # Get all windows on screen
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
        )

        # Iterate and find windows within the display
        for window in window_list:
            bounds = window.get("kCGWindowBounds", {})
            window_x = bounds.get("X", 0)
            window_y = bounds.get("Y", 0)

            if (
                display_bounds.origin.x
                <= window_x
                <= display_bounds.origin.x + display_bounds.size.width
                and display_bounds.origin.y
                <= window_y
                <= display_bounds.origin.y + display_bounds.size.height
            ):
                app_name = window.get("kCGWindowOwnerName", "")
                window_name = window.get("kCGWindowName", "")
                return f"{app_name} - {window_name}" if window_name else app_name

        return "Unknown"
    except Exception as e:
        print(f"Error getting display app: {e}")
        return "Unknown"


def get_current_app_name():
    """Get the name of the current running app (this intention app)"""
    try:
        # Method 1: Use Python's process information first
        import os
        import sys
        import psutil

        # Get current process info
        current_process = psutil.Process(os.getpid())
        process_name = current_process.name()

        # Clean up process name
        if process_name.endswith(".py"):
            process_name = process_name[:-3]

        # If it's a generic python process, try to get more specific info
        if process_name.lower() in ["python", "python3"]:
            # Try to get the script name from command line arguments
            try:
                cmdline = current_process.cmdline()
                if len(cmdline) > 1:
                    script_path = cmdline[1]
                    script_name = os.path.basename(script_path)
                    if script_name.endswith(".py"):
                        script_name = script_name[:-3]
                    if script_name and script_name != "python":
                        process_name = script_name
            except:
                pass

        print(f"[CURRENT_APP] Got current app name via psutil: '{process_name}'")

        # If we still have a generic name, try to make it more specific
        if process_name.lower() in ["python", "python3", "main"]:
            # Try to get app name from sys.argv
            if hasattr(sys, "argv") and len(sys.argv) > 0:
                script_name = os.path.basename(sys.argv[0])
                if script_name.endswith(".py"):
                    script_name = script_name[:-3]
                if script_name and script_name not in ["python", "python3"]:
                    process_name = script_name

        return process_name

    except Exception as e:
        print(f"[CURRENT_APP] Error getting current app name: {e}")

        # Fallback method
        try:
            import os
            import sys

            # Get process name from sys.argv[0] or current process
            if hasattr(sys, "argv") and len(sys.argv) > 0:
                process_name = os.path.basename(sys.argv[0])
                if process_name.endswith(".py"):
                    process_name = process_name[:-3]  # Remove .py extension
                print(f"[CURRENT_APP] Fallback to process name: '{process_name}'")
                return process_name

            # Method 3: Last resort - generic name
            print("[CURRENT_APP] Using generic fallback name")
            return "Python"

        except Exception as e2:
            print(f"[CURRENT_APP] Fallback error: {e2}")
            return "Python"  # Fallback to generic name

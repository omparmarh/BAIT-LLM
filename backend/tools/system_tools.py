import os
import subprocess
import pyautogui
import base64
from io import BytesIO

def open_app(app_name: str):
    """Open a macOS application by name."""
    try:
        subprocess.run(["open", "-a", app_name], check=True)
        return f"Successfully opened {app_name}."
    except Exception as e:
        return f"Error opening {app_name}: {str(e)}"

def take_screenshot(filename: str = "screenshot.png"):
    """Take a screenshot and save it to a file. Returns the path."""
    try:
        # For M1 Mac, pyautogui works well or we can use screencapture via shell
        subprocess.run(["screencapture", filename], check=True)
        return f"Screenshot saved to {filename}."
    except Exception as e:
        return f"Error taking screenshot: {str(e)}"

def list_apps():
    """List common applications installed on the system."""
    apps_path = "/Applications"
    try:
        apps = [f.replace(".app", "") for f in os.listdir(apps_path) if f.endswith(".app")]
        return ", ".join(apps[:20]) # Limit to first 20 for briefity
    except Exception as e:
        return f"Error listing apps: {str(e)}"

if __name__ == "__main__":
    print(list_apps())

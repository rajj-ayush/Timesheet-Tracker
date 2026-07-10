import pystray
from PIL import Image, ImageDraw
import subprocess
import webbrowser
import os
import sys
import threading

# --- Force the working directory to this exact folder ---
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Global variables
streamlit_process = None
tracker_process = None

def get_bat_path():
    """Helper function to get the exact path of the Windows Startup folder."""
    startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    return os.path.join(startup_folder, 'AIAssistantBot.bat')

def get_tracker_path():
    return "tracker.py"

def create_icon_image():
    """Generates a simple blue robot-like circle for your taskbar icon."""
    image = Image.new('RGB', (64, 64), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=(0, 122, 204))
    draw.ellipse((24, 24, 40, 40), fill=(255, 255, 255))
    return image

def open_assistant(icon, item):
    """Opens the Streamlit UI."""
    webbrowser.open("http://localhost:8501")

def exit_action(icon, item):
    """Safely shuts down absolutely everything and closes the app."""
    global streamlit_process, tracker_process
    if streamlit_process: streamlit_process.terminate()
    if tracker_process: tracker_process.terminate()
    icon.stop()

def ensure_autostart():
    """Silently forces the bot to run on Windows Startup every time it boots."""
    bat_path = get_bat_path()
    if not os.path.exists(bat_path):
        python_exe = sys.executable.replace("python.exe", "pythonw.exe")
        script_path = os.path.abspath(__file__)
        with open(bat_path, "w") as f:
            f.write(f'start "" "{python_exe}" "{script_path}"')

def start_background_tasks():
    global streamlit_process, tracker_process
    
    # 1. Always Start Tracker Automatically
    tracker_path = get_tracker_path()
    if os.path.exists(tracker_path):
        tracker_process = subprocess.Popen([sys.executable, tracker_path])
    
    # 2. Always Start Streamlit (headless) Automatically
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.headless=true"]
    )

def main():
    # Force auto-start invisibly in the background
    ensure_autostart() 
    
    # Start tracking and UI
    threading.Thread(target=start_background_tasks, daemon=True).start()

    # The clean, 2-button menu
    menu = pystray.Menu(
        pystray.MenuItem("Open Assistant", open_assistant, default=True),
        pystray.MenuItem("Exit", exit_action)
    )

    icon = pystray.Icon("AI_Assistant", create_icon_image(), "AI Work Assistant", menu)
    icon.run()

if __name__ == "__main__":
    main()
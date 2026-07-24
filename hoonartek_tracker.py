import os
import sys
import time
import json
import threading
import webbrowser
import hashlib
import subprocess
import requests
from datetime import datetime, timedelta
import pystray
from PIL import Image, ImageDraw
import psycopg2
import tkinter as tk
from tkinter import simpledialog, messagebox
import keyboard
import pyautogui
import pyperclip

last_used_date = None

try:
    import win32gui
except ImportError:
    print("win32gui not found. Please run: pip install pywin32")
    sys.exit(1)

# --- 1. CONFIGURATION ---
DB_URL = "postgresql://neondb_owner:npg_dR8FY4hIcnbw@ep-gentle-water-atoky22j.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"
STREAMLIT_URL = "https://timesheet-tracker-hoonartek.streamlit.app"

# Disable the corner mouse fail-safe so typing isn't interrupted
pyautogui.FAILSAFE = False

# Auto-Updater Configuration
def get_internal_version():
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        version_file = os.path.join(base_path, 'updates', 'version.txt')
        
        with open(version_file, 'r') as f:
            return float(f.read().strip())
    except Exception as e:
        print(f"⚠️ Version file missing, defaulting to fallback. Error: {e}")
        return 0.0

CURRENT_VERSION = get_internal_version()
GITHUB_TOKEN = "" 
GITHUB_USER = "rajj-ayush" 
GITHUB_REPO = "Timesheet-Tracker" 

VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/updates/version.txt"
EXE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/updates/hoonartek_tracker.exe"

# Local App Data
APP_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'HoonartekTracker')
os.makedirs(APP_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APP_DIR, "user_config.json")
is_tracking = True

# --- 2. AUTO-UPDATER LOGIC ---
def check_for_updates():
    print("Checking cloud for updates...")
    
    headers = {}
    if GITHUB_TOKEN:
         headers["Authorization"] = f"token {GITHUB_TOKEN}"
         
    try:
        response = requests.get(VERSION_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            latest_version = float(response.text.strip())
            
            if latest_version > CURRENT_VERSION:
                print(f"🚀 Update found! Downloading v{latest_version}...")
                
                exe_response = requests.get(EXE_URL, headers=headers, stream=True)
                if exe_response.status_code == 200:
                    with open("app_new.exe", "wb") as f:
                        for chunk in exe_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    exe_name = os.path.basename(sys.executable)
                    
                    bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
move /Y app_new.exe "{exe_name}"
start "" "{exe_name}"
del "%~f0"
"""
                    with open("update.bat", "w") as f:
                        f.write(bat_content)
                        
                    print("🔄 Restarting to apply update...")
                    subprocess.Popen("update.bat", shell=True)
                    os._exit(0) 
        else:
            print("✅ App is up to date.")
    except Exception as e:
        print(f"⚠️ Update check bypassed (No internet or bad token): {e}")

# --- 3. AUTHENTICATION & SETUP ---
def ensure_autostart():
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        bat_path = os.path.join(startup_folder, 'HoonartekTracker.bat')
        
        if not os.path.exists(bat_path):
            with open(bat_path, "w") as f:
                f.write(f'@echo off\nstart "" "{exe_path}"')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_employee_credentials():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            if "employee_email" in config:
                return config.get("employee_email")
    
    root = tk.Tk()
    root.withdraw() 
    root.attributes('-topmost', True) 
    
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
    except Exception as e:
        messagebox.showerror("Network Error", "Could not connect to database.")
        sys.exit(1)

    while True:
        email = simpledialog.askstring("Hoonartek Tracker", "Enter your Hoonartek email:", parent=root)
        if not email: sys.exit(1)
        email = email.strip().lower()
        
        if not email.endswith("@hoonartek.com"):
            messagebox.showerror("Invalid Email", "Must use a Hoonartek email address.")
            continue

        cursor.execute("SELECT password_hash, name FROM users WHERE email = %s", (email,))
        user_record = cursor.fetchone()

        if user_record:
            db_password_hash = user_record[0]
            user_name = user_record[1]
            password = simpledialog.askstring("Welcome Back!", f"Account found for {user_name}.\n\nEnter password:", show="*", parent=root)
            if not password: sys.exit(1)
            
            if hash_password(password) == db_password_hash:
                messagebox.showinfo("Success", f"Welcome back, {user_name}!")
                break
            else:
                messagebox.showerror("Error", "Incorrect password.")
                continue
        else:
            messagebox.showerror("Account Not Found", "You must register on the Web Portal first before using the desktop app.\n\nPlease visit the Timesheet Portal to create your account.")
            sys.exit(1)

    with open(CONFIG_FILE, "w") as f:
        json.dump({"employee_email": email}, f)
    
    cursor.close()
    conn.close()
    root.destroy()
    return email

# --- 4. TRACKER LOGIC ---
def get_active_window_title():
    try:
        window = win32gui.GetForegroundWindow()
        if window == 0: return ""
        return win32gui.GetWindowText(window)
    except Exception as e:
        print(f"⚠️ Window Error: {e}") 
        return ""

def tracking_loop(email):
    global is_tracking
    
    check_for_updates()
    print(f"✅ Tracking started for: {email}")
    last_update_check = time.time()
    
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return

    app_durations = {}
    bucket_start_time = time.time()
    BUCKET_LIMIT = 30 * 60

    while is_tracking:
        try:
            current_app = get_active_window_title()
            
            if current_app:
                if current_app in app_durations:
                    app_durations[current_app] += 10
                else:
                    app_durations[current_app] = 10

            current_time = time.time()
            
            if current_time - bucket_start_time >= BUCKET_LIMIT:
                summary_parts = []
                for app, seconds in app_durations.items():
                    if seconds >= 60: 
                        mins = seconds // 60
                        summary_parts.append(f"{app}: {mins}m")

                summary_string = " | ".join(summary_parts)

                if summary_string:
                    now = datetime.now()
                    
                    if conn.closed != 0:
                        conn = psycopg2.connect(DB_URL)
                        cursor = conn.cursor()
                        
                    cursor.execute(
                        "INSERT INTO activity_logs (employee_email, timestamp, active_application) VALUES (%s, %s, %s)",
                        (email, now, summary_string)
                    )
                    conn.commit()
                    print(f"💾 30-Min Bucket Saved: {summary_string}")

                app_durations.clear()
                bucket_start_time = current_time
                
            if time.time() - last_update_check > 3600:
                check_for_updates()
                last_update_check = time.time()

            time.sleep(10)
            
        except psycopg2.Error as db_error:
            print(f"⚠️ DB Error (Trying to reconnect): {db_error}")
            try:
                if 'conn' in locals() and conn: conn.close()
                conn = psycopg2.connect(DB_URL)
                cursor = conn.cursor()
            except:
                pass
            time.sleep(10)
            
        except Exception as e:
            print(f"💥 Temporary Loop Error: {e}")
            time.sleep(10) 

    if 'cursor' in locals() and cursor: cursor.close()
    if 'conn' in locals() and conn: conn.close()

# --- 5. TIMESHEET AUTOFILL LOGIC ---
def autofill_keka_timesheet(email):
    """Fetches the saved AI summary from Neon DB and copies it to the clipboard."""
    global last_used_date 
    
    # 1. Smart Default Logic
    today = datetime.now()
    if last_used_date:
        suggested_date = last_used_date + timedelta(days=1)
    else:
        suggested_date = today
        
    suggested_str = suggested_date.strftime("%Y-%m-%d")
    
    prompt_text = (
        "Bulk Fetch: Press Enter for the next consecutive day.\n"
        "Or type a specific day (e.g., '15' for the 15th, '06-15' for June 15).\n\n"
        "Enter date:"
    )
    
    raw_input = pyautogui.prompt(
        text=prompt_text, 
        title='Fetch Timesheet', 
        default=suggested_str
    )
    
    if not raw_input:
        return 

    # --- SMART DATE PARSING LOGIC ---
    raw_input = raw_input.strip().lower()
    target_date_str = raw_input 
    
    try:
        if raw_input in ['y', 'yesterday']:
            parsed_date = today - timedelta(days=1)
        elif raw_input.isdigit() and 1 <= int(raw_input) <= 31:
            parsed_date = today.replace(day=int(raw_input))
        elif len(raw_input) <= 5 and '-' in raw_input: 
            month, day = map(int, raw_input.split('-'))
            parsed_date = today.replace(month=month, day=day)
        else:
            parsed_date = datetime.strptime(raw_input, "%Y-%m-%d")
            
        target_date_str = parsed_date.strftime("%Y-%m-%d")
        last_used_date = parsed_date 
        
    except Exception as e:
        print(f"Date formatting error: {e}")

    try:
        # 2. Connect to Neon and fetch the saved summary
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        query = "SELECT summary FROM daily_summaries WHERE email = %s AND log_date = %s"
        cursor.execute(query, (email, target_date_str))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # 3. Handle the result with a popup
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        if result:
            summary_text = result[0]
            # Copy to clipboard instantly
            pyperclip.copy(summary_text)
            messagebox.showinfo(" Copied!", f"Timesheet for {target_date_str} has been copied to your clipboard.\n\nYou can now paste (Ctrl+V) it anywhere.", parent=root)
        else:
            messagebox.showwarning("⚠️ Not Found", f"No summary found for {target_date_str}.\nRun the Streamlit dashboard to generate it!", parent=root)
            
        root.destroy()
            
    except Exception as e:
        print(f"Database error during fetch: {e}")


# --- 6. SYSTEM TRAY LOGIC ---
def create_icon_image():
    image = Image.new('RGB', (64, 64), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=(0, 122, 204))
    draw.ellipse((24, 24, 40, 40), fill=(255, 255, 255))
    return image

def open_dashboard(icon, item):
    webbrowser.open(STREAMLIT_URL)

def exit_action(icon, item):
    global is_tracking
    is_tracking = False 
    icon.stop()

# --- 7. MAIN EXECUTION ---
def main():
    ensure_autostart()
    print("⏳ Launching login portal...")
    
    # Get the email securely and pass it to the tracking and autofill systems
    email = get_employee_credentials()
    
    if not email:
        sys.exit(1)
        
    print("✅ Starting background threads...")
    tracker_thread = threading.Thread(target=tracking_loop, args=(email,), daemon=True)
    tracker_thread.start()
    
    # Register the hotkey to pass the dynamically logged-in email
    keyboard.add_hotkey('ctrl+alt+t', autofill_keka_timesheet, args=[email])
    print(f"📋 Timesheet fetcher ready for {email}. Press Ctrl+Alt+T anywhere to copy.")

    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", open_dashboard, default=True),
        pystray.MenuItem("Exit", exit_action)
    )

    icon = pystray.Icon("AI_Assistant", create_icon_image(), "Hoonartek Tracker", menu)
    
    # This keeps the app running continuously (replacing keyboard.wait())
    icon.run()

if __name__ == "__main__":
    main()
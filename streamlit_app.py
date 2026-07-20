import streamlit as st
import os
import json
import hashlib
import smtplib
import random
from email.mime.text import MIMEText
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from google import genai
import psycopg2
from streamlit_cookies_controller import CookieController

# Import your clean prompt logic
from prompts.system_prompt import get_timesheet_prompt

# --- Configuration & Setup ---
st.set_page_config(page_title="AI Timesheet Assistant", page_icon="🤖", layout="wide")
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize cookie manager
controller = CookieController()

# Helper function to securely encrypt passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Helper function to send OTP securely from the server
def send_otp_email(receiver_email, otp_code):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    msg = MIMEText(f"Your Hoonartek Timesheet verification code is: {otp_code}\n\nDo not share this code with anyone.")
    msg['Subject'] = 'Hoonartek Timesheet - Verification Code'
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        return str(e)

# --- SESSION MANAGEMENT ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "generated_report" not in st.session_state:
    st.session_state.generated_report = ""
if "signup_stage" not in st.session_state:
    st.session_state.signup_stage = 1
if "signup_email" not in st.session_state:
    st.session_state.signup_email = ""
if "signup_otp" not in st.session_state:
    st.session_state.signup_otp = ""

# --- AGGRESSIVE COOKIE RECOVERY (Fixes the refresh bug) ---
cookie_email = controller.get('user_email')
cookie_name = controller.get('user_name')

# If session is empty but the cookie finally loaded, restore it and force a rerun to fix the screen
if st.session_state.user_email is None and cookie_email:
    st.session_state.user_email = cookie_email
    st.session_state.user_name = cookie_name
    st.rerun()


# ==========================================
# 🔒 THE SECURE AUTHENTICATION PORTAL
# ==========================================
if st.session_state.user_email is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔒 Timesheet Portal")
        st.markdown("Secure access to your automated timesheets.")
        
        tab1, tab2 = st.tabs(["Log In", "Sign Up (New Users)"])
        
        # --- TAB 1: LOG IN ---
        with tab1:
            with st.form("login_form"):
                login_email = st.text_input("Company Email")
                login_pass = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Log In", type="primary", use_container_width=True)
                
                if submit_login:
                    clean_email = login_email.strip().lower()
                    try:
                        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                        cursor = conn.cursor()
                        cursor.execute("SELECT name, password_hash FROM users WHERE email = %s", (clean_email,))
                        user_record = cursor.fetchone()
                        cursor.close()
                        conn.close()
                        
                        if user_record and user_record[1] == hash_password(login_pass):
                            st.session_state.user_email = clean_email
                            st.session_state.user_name = user_record[0]
                            
                            controller.set('user_email', clean_email)
                            controller.set('user_name', user_record[0])
                            
                            st.rerun()
                        else:
                            st.error("❌ Invalid email or password.")
                    except Exception as e:
                        st.error(f"Database Error: {e}")

        # --- TAB 2: SIGN UP ---
        with tab2:
            if st.session_state.signup_stage == 1:
                st.info("First time here? Verify your email to create an account.")
                with st.form("email_form"):
                    reg_name = st.text_input("Full Name (e.g., Ayush Raj)")
                    reg_email = st.text_input("Company Email (@hoonartek.com)")
                    send_otp_btn = st.form_submit_button("Send Verification Code", use_container_width=True)
                    
                    if send_otp_btn:
                        if "@hoonartek.com" not in reg_email.lower():
                            st.error("Please use a valid Hoonartek email address.")
                        elif len(reg_name) < 2:
                            st.error("Please enter your full name.")
                        else:
                            generated_otp = str(random.randint(100000, 999999))
                            st.session_state.signup_otp = generated_otp
                            st.session_state.signup_email = reg_email.strip().lower()
                            st.session_state.signup_name = reg_name.strip()
                            
                            with st.spinner("Sending email..."):
                                result = send_otp_email(st.session_state.signup_email, generated_otp)
                                if result is True:
                                    st.session_state.signup_stage = 2
                                    st.rerun()
                                else:
                                    st.error(f"Failed to send email. Error: {result}")
            
            elif st.session_state.signup_stage == 2:
                st.success(f"Verification code sent to **{st.session_state.signup_email}**")
                with st.form("password_form"):
                    entered_otp = st.text_input("Enter Verification Code")
                    new_password = st.text_input("Create Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    
                    col_back, col_submit = st.columns(2)
                    with col_back:
                        if st.form_submit_button("Go Back"):
                            st.session_state.signup_stage = 1
                            st.rerun()
                    with col_submit:
                        create_account_btn = st.form_submit_button("Create Account", type="primary")
                    
                    if create_account_btn:
                        if entered_otp != st.session_state.signup_otp:
                            st.error("Incorrect verification code.")
                        elif len(new_password) < 6:
                            st.error("Password must be at least 6 characters.")
                        elif new_password != confirm_password:
                            st.error("Passwords do not match.")
                        else:
                            try:
                                conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                                cursor = conn.cursor()
                                hashed_pw = hash_password(new_password)
                                
                                cursor.execute("SELECT email FROM users WHERE email = %s", (st.session_state.signup_email,))
                                if cursor.fetchone():
                                    st.error("An account with this email already exists! Please log in.")
                                    st.session_state.signup_stage = 1
                                else:
                                    cursor.execute(
                                        "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
                                        (st.session_state.signup_email, st.session_state.signup_name, hashed_pw)
                                    )
                                    conn.commit()
                                    st.success("Account created successfully! You can now log in.")
                                    st.session_state.signup_stage = 1
                                    
                                cursor.close()
                                conn.close()
                            except Exception as e:
                                st.error(f"Database Error: {e}")

# ==========================================
# 📊 THE MAIN DASHBOARD (Protected)
# ==========================================
else:
    st.title("🤖 AI Timesheet Assistant")

    # --- SIDEBAR: REARRANGED LAYOUT ---
    with st.sidebar:
        st.header("Dashboard")
        st.markdown(f"### 👋 Hi, {st.session_state.user_name}")
        st.divider()
        
        # 1. GENERATE REPORT MOVED TO TOP
        st.subheader("Generate Report")
        
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                retention_limit = config.get("retention_days", 30)
        except Exception:
            retention_limit = 30
            
        today = date.today()
        cutoff_date = today - timedelta(days=retention_limit)
        
        report_type = st.radio("Select Report Type", ["Daily Report", "Custom Range"])
        
        trigger_generation = False
        start_target = ""
        end_target = ""
        
        if report_type == "Daily Report":
            selected_date = st.date_input(
                "Select Date", 
                value=today,
                min_value=cutoff_date, 
                max_value=today,
                label_visibility="collapsed"
            )
            if st.button(f" Draft {selected_date.strftime('%b %d')}", type="primary", use_container_width=True):
                trigger_generation = True
                start_target = selected_date.strftime('%Y-%m-%d')
                end_target = start_target
                
        else:
            selected_dates = st.date_input(
                "Select Custom Range", 
                value=(), 
                min_value=cutoff_date, 
                max_value=today
            )
            if len(selected_dates) == 2:
                start_date, end_date = selected_dates
                if st.button(f" Draft {start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}", type="primary", use_container_width=True):
                    trigger_generation = True
                    start_target = start_date.strftime('%Y-%m-%d')
                    end_target = end_date.strftime('%Y-%m-%d')
            elif len(selected_dates) == 1:
                st.info("Please select an end date to complete the range.")
        
        st.divider()
        
        # 2. DESKTOP TRACKER MOVED TO BOTTOM
        st.markdown("### Desktop Tracker")
        st.markdown("Run this lightweight app in the background to automatically log your work.")
        # Replace with your actual GitHub Raw or Google Drive link
        st.link_button(
            " Download ", 
            "https://github.com/ayushraj-hoonartek/ai-timesheet-db/raw/main/updates/Hoonartek_Tracker_v1.zip", 
            use_container_width=True
        )
        
        st.divider()
        
        # 3. LOG OUT MOVED TO VERY BOTTOM
        if st.button("Log Out", type="secondary", use_container_width=True):
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.generated_report = ""
            
            controller.remove('user_email')
            controller.remove('user_name')
            
            st.rerun()

    # --- TIMESHEET GENERATION LOGIC ---
    if trigger_generation:
        with st.spinner(f" Generating professional timesheet for {start_target}..."):
            final_answer = ""
            start_date_obj = datetime.strptime(start_target, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_target, "%Y-%m-%d").date()
            
            logs = []
            try:
                db_url = os.getenv("DATABASE_URL")
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT timestamp, active_application 
                    FROM activity_logs 
                    WHERE DATE(timestamp) >= %s AND DATE(timestamp) <= %s
                    AND employee_email = %s
                    ORDER BY timestamp ASC
                """, (start_date_obj, end_date_obj, st.session_state.user_email))
                
                rows = cursor.fetchall()
                for row in rows:
                    logs.append({
                        "timestamp": str(row[0]), 
                        "active_application": row[1]
                    })
                    
                cursor.close()
                conn.close()
            except Exception as e:
                st.error(f"Database Query Error: {e}")
            
            if not logs:
                if start_target == end_target:
                    final_answer = f"No work activity logs found for **{start_target}**."
                else:
                    final_answer = f"No work activity logs found from **{start_target}** to **{end_target}**."
            else:
                try:
                    prompt = get_timesheet_prompt(logs, start_target, end_target)
                    response = client.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt)
                    final_answer = response.text
                except Exception as e:
                    final_answer = f"❌ Timesheet Agent Error: {e}"

            st.session_state.generated_report = final_answer

    # --- MAIN DISPLAY AREA ---
    if st.session_state.generated_report:
        st.markdown(st.session_state.generated_report)
        st.divider()
        st.download_button(
            label=" Download as Text File",
            data=st.session_state.generated_report,
            file_name=f"Timesheet_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            type="secondary"
        )
    else:
        st.info(" Select a date on the left menu and click 'Draft' to generate your automated timesheet.")
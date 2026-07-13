import streamlit as st
import os
import json
import hashlib
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from google import genai
import psycopg2

# Import your clean prompt logic
from prompts.system_prompt import get_timesheet_prompt

# --- Configuration & Setup ---
st.set_page_config(page_title="AI Timesheet Assistant", page_icon="🤖", layout="wide")
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Helper function to securely encrypt passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- SESSION MANAGEMENT ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "generated_report" not in st.session_state:
    st.session_state.generated_report = ""

# ==========================================
# 🔒 THE SECURE LOGIN SCREEN (Sign-up Removed)
# ==========================================
if st.session_state.user_email is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔒 Timesheet Portal")
        st.markdown("Secure access to your automated timesheets.")
        
        # New instructional banner for employees
        st.info("ℹ️ **Account Setup:** Registration is handled directly through your Desktop Tracker. Please log in using the credentials you created there.")
        
        # --- LOGIN FORM ---
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
                        st.rerun()
                    else:
                        st.error("❌ Invalid email or password.")
                except Exception as e:
                    st.error(f"Database Error: {e}")

# ==========================================
# 📊 THE MAIN DASHBOARD (Protected)
# ==========================================
else:
    st.title("🤖 AI Timesheet Assistant")

    # --- SIDEBAR: DASHBOARD ---
    with st.sidebar:
        st.header("Dashboard")
        
        st.markdown(f"### 👋 Hi {st.session_state.user_name}")
        
        # LOGOUT LOGIC
        if st.button("Log Out", type="secondary", use_container_width=True):
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.session_state.generated_report = ""
            st.rerun()
            
        st.divider()
        
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
            if st.button(f"📝 Draft {selected_date.strftime('%b %d')}", type="primary", use_container_width=True):
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
                if st.button(f"📝 Draft {start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}", type="primary", use_container_width=True):
                    trigger_generation = True
                    start_target = start_date.strftime('%Y-%m-%d')
                    end_target = end_date.strftime('%Y-%m-%d')
            elif len(selected_dates) == 1:
                st.info("Please select an end date to complete the range.")

    # --- TIMESHEET GENERATION LOGIC ---
    if trigger_generation:
        with st.spinner(f"📝 Generating professional timesheet for {start_target}..."):
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
            label="📥 Download as Text File",
            data=st.session_state.generated_report,
            file_name=f"Timesheet_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            type="secondary"
        )
    else:
        st.info(" Select a date on the left menu and click 'Draft' to generate your automated timesheet.")
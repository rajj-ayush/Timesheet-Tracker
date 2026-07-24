import os
import sys
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai

from prompts.system_prompt import get_timesheet_prompt

load_dotenv()

DB_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://neondb_owner:npg_dR8FY4hIcnbw@ep-gentle-water-atoky22j.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

def generate_ai_task_summary(rows, target_date_str):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    formatted_logs = [
        {"timestamp": str(row[0]), "active_application": row[1] if len(row) > 1 else ""} 
        for row in rows
    ]

    prompt = get_timesheet_prompt(
        logs=formatted_logs, 
        start_date_str=target_date_str, 
        end_date_str=target_date_str
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite", 
        contents=prompt
    )
    
    return response.text.strip()


def process_all_employees_summary(target_date_str=None):
    if not target_date_str:
        target_date = (datetime.now() - timedelta(days=1)).date()
        target_date_str = target_date.strftime("%Y-%m-%d")

    print(f" Master Summarizer starting for date: {target_date_str}")

    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()

        # 1. Find every unique employee who logged activity on this date
        cursor.execute("""
            SELECT DISTINCT employee_email 
            FROM activity_logs 
            WHERE DATE(timestamp) = %s
        """, (target_date_str,))
        
        emails = [row[0] for row in cursor.fetchall()]

        if not emails:
            print(f"⚠️ No activity logs found in the database for {target_date_str}.")
            return

        print(f"👥 Found logs for {len(emails)} employee(s). Processing...\n")

        # 2. Loop through each employee and generate their specific summary
        for email in emails:
            print(f"➡️ Processing timesheet for: {email}")
            
            cursor.execute("""
                SELECT timestamp, active_application 
                FROM activity_logs 
                WHERE DATE(timestamp) = %s AND employee_email = %s
                ORDER BY timestamp ASC
            """, (target_date_str, email))

            rows = cursor.fetchall()
            
            summary_text = generate_ai_task_summary(rows, target_date_str)

            # 3. Save to database
            upsert_query = """
                INSERT INTO daily_summaries (email, log_date, summary)
                VALUES (%s, %s, %s)
                ON CONFLICT (email, log_date) 
                DO UPDATE SET summary = EXCLUDED.summary;
            """
            cursor.execute(upsert_query, (email, target_date_str, summary_text))
            conn.commit()
            print(f"   ✅ Saved summary for {email}\n")

        print("🎉 ALL EMPLOYEES PROCESSED SUCCESSFULLY!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error during master summarization: {e}")


if __name__ == "__main__":
    passed_date = sys.argv[1] if len(sys.argv) > 1 else None
    process_all_employees_summary(target_date_str=passed_date)
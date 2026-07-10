import psycopg2

# 1. Configuration (Update these!)
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
NEON_DB_URL = "postgresql://neondb_owner:npg_dR8FY4hIcnbw@ep-gentle-water-atoky22j.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"
MY_EMAIL = "ayush@hoonartek.com" # This will be attached to all your historical logs

def migrate():
    print("🚀 Starting data migration...")
    
    try:
        # Connect to Local DB
        local_conn = psycopg2.connect(LOCAL_DB_URL)
        local_cursor = local_conn.cursor()
        
        # Connect to Neon DB
        neon_conn = psycopg2.connect(NEON_DB_URL)
        neon_cursor = neon_conn.cursor()
        
        # Fetch all old logs
        print("📥 Fetching logs from local database...")
        local_cursor.execute("SELECT timestamp, active_application FROM activity_logs")
        rows = local_cursor.fetchall()
        
        if not rows:
            print("No local logs found. Migration complete.")
            return

        # Insert into Neon DB
        print(f"📤 Pushing {len(rows)} logs to Neon for {MY_EMAIL}...")
        
        insert_query = """
            INSERT INTO activity_logs (employee_email, timestamp, active_application) 
            VALUES (%s, %s, %s)
        """
        
        for row in rows:
            timestamp = row[0]
            application = row[1]
            neon_cursor.execute(insert_query, (MY_EMAIL, timestamp, application))
            
        # Save the changes to the cloud
        neon_conn.commit()
        print("✅ Migration successful! All your data is in the cloud.")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        
    finally:
        # Clean up connections
        if 'local_cursor' in locals(): local_cursor.close()
        if 'local_conn' in locals(): local_conn.close()
        if 'neon_cursor' in locals(): neon_cursor.close()
        if 'neon_conn' in locals(): neon_conn.close()

if __name__ == "__main__":
    migrate()
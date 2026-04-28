import sqlite3
import chromadb
from datetime import datetime

#Stores every single ticket (Success, Escalate, Failed) so humans can review them on the dashboard.

# Initialize SQLite
def setup_database():
    conn = sqlite3.connect('itsm_portal.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            timestamp TEXT,
            queue TEXT,
            ticket_type TEXT,
            priority TEXT,
            original_description TEXT,
            proposed_resolution TEXT,
            final_status TEXT
        )
    ''')
    conn.commit()
    conn.close()

setup_database()
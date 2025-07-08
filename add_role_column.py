import sqlite3

DB_PATH = 'instance/chatbot.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check if 'role' column exists
cursor.execute("PRAGMA table_info(users);")
columns = [col[1] for col in cursor.fetchall()]

if 'role' not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN role TEXT;")
    print("'role' column added to users table.")
else:
    print("'role' column already exists in users table.")

conn.commit()
conn.close() 
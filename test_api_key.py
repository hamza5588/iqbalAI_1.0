#!/usr/bin/env python3
"""
Test script to check API key retrieval from database
"""
import os
import sys
import sqlite3

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_database_connection(db_path, db_name):
    """Test database connection and API key retrieval"""
    try:
        print(f"\nConnecting to {db_name}: {db_path}")
        
        if not os.path.exists(db_path):
            print(f"Database file not found: {db_path}")
            return False
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Check if users table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print(f"Users table not found in {db_name}")
            return False
            
        # Get all users and their API keys
        cursor = conn.execute("SELECT id, username, useremail, groq_api_key FROM users")
        users = cursor.fetchall()
        
        print(f"Found {len(users)} users in {db_name}:")
        for user in users:
            api_key = user['groq_api_key']
            api_key_preview = api_key[:10] + "..." if api_key else "None"
            print(f"  User ID: {user['id']}, Username: {user['username']}, Email: {user['useremail']}, API Key: {api_key_preview}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error with {db_name}: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing database connection and API key retrieval...")
    
    # Test both database files
    app_sqlite = os.path.join('instance', 'app.sqlite')
    chatbot_db = os.path.join('instance', 'chatbot.db')
    
    test_database_connection(app_sqlite, "app.sqlite")
    test_database_connection(chatbot_db, "chatbot.db") 
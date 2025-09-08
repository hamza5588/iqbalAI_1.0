import os
import sqlite3

# Resolve DB path similar to app.config.Config.DATABASE
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'chatbot.db')

DDL_ADD_COLUMN = 'ALTER TABLE lessons ADD COLUMN has_child_version BOOLEAN DEFAULT FALSE'
DML_BACKFILL = 'UPDATE lessons SET has_child_version = COALESCE(has_child_version, FALSE)'


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        # row: cid, name, type, notnull, dflt_value, pk
        if row[1] == column:
            return True
    return False


def main() -> None:
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"Database not found at: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA busy_timeout = 30000')

        if not column_exists(conn, 'lessons', 'has_child_version'):
            print('Adding has_child_version column to lessons...')
            conn.execute(DDL_ADD_COLUMN)
            conn.commit()
        else:
            print('Column has_child_version already exists. Skipping DDL.')

        # Backfill defaults (safe to run multiple times)
        print('Backfilling defaults for has_child_version...')
        conn.execute(DML_BACKFILL)
        conn.commit()
        print('Migration complete.')
    finally:
        conn.close()


if __name__ == '__main__':
    main()


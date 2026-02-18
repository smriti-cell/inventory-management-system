import sqlite3

DB_NAME = "inventory.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with open("schema.sql", "r") as f:
        conn = get_db()
        conn.executescript(f.read())
        conn.commit()
        conn.close()

if __name__ == "__main__":
    init_db()

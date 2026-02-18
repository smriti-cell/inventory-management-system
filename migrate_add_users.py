from database import get_db
db = get_db()
db.execute("""
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL
)
""")
db.commit()
print("users table OK")

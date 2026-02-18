# migrate_add_categories.py
from database import get_db
db = get_db()

try:
    # create categories table (if not exists)
    db.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    # add column to products if missing
    # SQLite ALTER TABLE ADD COLUMN is simple; if column exists it will throw.
    try:
        db.execute("ALTER TABLE products ADD COLUMN category_id INTEGER")
    except Exception as e:
        # column likely exists already
        print("Note:", e)
    db.commit()

    print("Migration complete.")
except Exception as e:
    print("Migration error:", e)

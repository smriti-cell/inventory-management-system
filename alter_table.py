from database import get_db

db = get_db()

try:
    db.execute("ALTER TABLE products ADD COLUMN image_path TEXT;")
    db.commit()
    print("Column 'image_path' added successfully!")
except Exception as e:
    print("Error:", e)

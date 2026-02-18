# app.py
from flask import Flask, render_template, request, redirect, session, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

from barcode import Code128
from barcode.writer import ImageWriter

import os, random, string, io
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "replace_this_with_a_random_secret"

# folders
PRODUCT_IMG_FOLDER = "static/product_images"
BARCODE_FOLDER = "static/barcodes"
os.makedirs(PRODUCT_IMG_FOLDER, exist_ok=True)
os.makedirs(BARCODE_FOLDER, exist_ok=True)

def generate_barcode():
    return ''.join(random.choices(string.digits, k=12))


# --- AUTH ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        hashed = generate_password_hash(password)
        try:
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
            db.commit()
            return redirect("/login")
        except Exception as e:
            return f"Error: {e}", 400
    return render_template("auth_register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        return "Invalid creds", 401
    return render_template("auth_login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            return redirect("/login")
        return fn(*a, **kw)
    return wrapper


# --- HOME & SEARCH ---
@app.route("/")
@login_required
def index():
    db = get_db()
    products = db.execute("""
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.id DESC
    """).fetchall()
    categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render_template("index.html", products=products, categories=categories)

@app.route("/api/search")
@login_required
def api_search():
    q = request.args.get("q","").strip()
    db = get_db()
    if q == "":
        rows = db.execute("SELECT id, name, barcode FROM products LIMIT 50").fetchall()
    else:
        like = f"%{q}%"
        rows = db.execute("SELECT id, name, barcode FROM products WHERE name LIKE ? OR barcode LIKE ? LIMIT 50", (like, like)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/category/<int:cat_id>")
@login_required
def category_view(cat_id):
    db = get_db()
    products = db.execute("SELECT * FROM products WHERE category_id = ? ORDER BY id DESC", (cat_id,)).fetchall()
    categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render_template("index.html", products=products, categories=categories, active_category=cat_id)


# --- ADD PRODUCT ---
@app.route("/add_product", methods=["POST"])
@login_required
def add_product():
    name = request.form["name"]
    quantity = request.form.get("quantity",0)
    threshold = request.form.get("threshold", 5)
    category_id = request.form.get("category_id") or None

    barcode_value = generate_barcode()

    image_file = request.files.get("image")
    image_filename = None
    if image_file and image_file.filename != "":
        original_name = secure_filename(image_file.filename)
        image_filename = f"{barcode_value}_{original_name}"
        image_file.save(os.path.join(PRODUCT_IMG_FOLDER, image_filename))

    db = get_db()
    db.execute(
        "INSERT INTO products (name, barcode, quantity, low_stock_threshold, image_path, category_id) VALUES (?, ?, ?, ?, ?, ?)",
        (name, barcode_value, quantity, threshold, image_filename, category_id)
    )
    db.commit()

    Code128(barcode_value, writer=ImageWriter()).save(os.path.join(BARCODE_FOLDER, barcode_value))
    return redirect("/")


# --- EDIT PRODUCT ---
@app.route("/edit_product/<int:product_id>", methods=["GET","POST"])
@login_required
def edit_product(product_id):
    db = get_db()
    if request.method == "POST":
        name = request.form["name"]
        quantity = request.form.get("quantity",0)
        threshold = request.form.get("threshold",5)
        category_id = request.form.get("category_id") or None

        image_file = request.files.get("image")
        if image_file and image_file.filename != "":
            original_name = secure_filename(image_file.filename)
            prod = db.execute("SELECT barcode, image_path FROM products WHERE id = ?", (product_id,)).fetchone()
            new_filename = f"{prod['barcode']}_{original_name}"
            image_file.save(os.path.join(PRODUCT_IMG_FOLDER, new_filename))
            if prod["image_path"]:
                try: os.remove(os.path.join(PRODUCT_IMG_FOLDER, prod["image_path"]))
                except: pass
            db.execute("UPDATE products SET image_path = ? WHERE id = ?", (new_filename, product_id))

        db.execute("UPDATE products SET name=?, quantity=?, low_stock_threshold=?, category_id=? WHERE id=?",
                   (name, quantity, threshold, category_id, product_id))
        db.commit()
        return redirect(f"/product/{product_id}")

    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render_template("edit_product.html", product=product, categories=categories)


# --- PRODUCT PAGE & UPDATE ---
@app.route("/product/<int:product_id>")
@login_required
def product_page(product_id):
    db = get_db()
    product = db.execute("SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.id = ?", (product_id,)).fetchone()
    return render_template("product.html", product=product)

@app.route("/update_quantity/<int:product_id>", methods=["POST"])
@login_required
def update_quantity(product_id):
    amount = int(request.form["amount"])
    action = request.form["action"]
    db = get_db()
    if action == "REMOVE":
        amount = -abs(amount)
    else:
        amount = abs(amount)
    db.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (amount, product_id))
    db.execute("INSERT INTO transactions (product_id, change_amount, transaction_type) VALUES (?, ?, ?)", (product_id, amount, action))
    db.commit()
    return redirect(f"/product/{product_id}")


# --- DELETE ---
@app.route("/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    db = get_db()
    prod = db.execute("SELECT barcode, image_path FROM products WHERE id = ?", (product_id,)).fetchone()
    if prod:
        if prod["image_path"]:
            try: os.remove(os.path.join(PRODUCT_IMG_FOLDER, prod["image_path"]))
            except: pass
        try: os.remove(os.path.join(BARCODE_FOLDER, prod["barcode"] + ".png"))
        except: pass
    db.execute("DELETE FROM transactions WHERE product_id = ?", (product_id,))
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    return redirect("/")


# --- LOW STOCK ---
@app.route("/low_stock")
@login_required
def low_stock():
    db = get_db()
    items = db.execute("SELECT * FROM products WHERE quantity <= low_stock_threshold").fetchall()
    return render_template("low_stock.html", items=items)


# --- SCANNER ---
@app.route("/scan/<barcode>")
@login_required
def scan_barcode(barcode):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE barcode = ?", (barcode,)).fetchone()
    if product:
        return redirect(f"/product/{product['id']}")
    return "Product not found", 404

@app.route("/scan_page")
@login_required
def scan_page():
    return render_template("scan.html")


# --- DASHBOARD ---
@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    total_products = db.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
    low_count = db.execute("SELECT COUNT(*) as c FROM products WHERE quantity <= low_stock_threshold").fetchone()["c"]
    low_items = db.execute("SELECT name, quantity FROM products ORDER BY quantity ASC LIMIT 8").fetchall()
    rows = db.execute("SELECT DATE(timestamp) as d, SUM(change_amount) as s FROM transactions WHERE transaction_type='REMOVE' GROUP BY DATE(timestamp) ORDER BY d DESC LIMIT 30").fetchall()
    chart_data = [{"date": r["d"], "value": -r["s"] if r["s"] else 0} for r in rows]
    return render_template("dashboard.html", total_products=total_products, low_count=low_count, low_items=low_items, chart_data=chart_data)


# --- EXPORT ---
@app.route("/export_products")
@login_required
def export_products():
    db = get_db()
    rows = db.execute("SELECT p.id, p.name, p.barcode, p.quantity, p.low_stock_threshold, c.name as category FROM products p LEFT JOIN categories c ON p.category_id=c.id").fetchall()
    df = pd.DataFrame([dict(r) for r in rows])
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    filename = f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# --- CATEGORIES ---
@app.route("/add_category", methods=["POST"])
@login_required
def add_category():
    name = request.form["name"].strip()
    if name:
        db = get_db()
        try:
            db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            db.commit()
        except:
            pass
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)

DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS transactions;

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    barcode TEXT UNIQUE,
    quantity INTEGER DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 5
);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    change_amount INTEGER,
    transaction_type TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

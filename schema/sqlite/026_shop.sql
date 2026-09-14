CREATE TABLE IF NOT EXISTS shop_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name_vi TEXT NOT NULL,
    description_vi TEXT,
    price_vnd INTEGER NOT NULL CHECK (price_vnd >= 0),
    stock_qty INTEGER NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
    image_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_shop_products_active
    ON shop_products(is_active, id DESC);

CREATE TABLE IF NOT EXISTS shop_cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES shop_products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE (user_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_shop_cart_user
    ON shop_cart_items(user_id);

CREATE TABLE IF NOT EXISTS shop_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_status TEXT NOT NULL DEFAULT 'placed',
    total_vnd INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_shop_orders_user
    ON shop_orders(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS shop_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES shop_orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES shop_products(id) ON DELETE SET NULL,
    name_vi TEXT NOT NULL,
    unit_price_vnd INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);

CREATE INDEX IF NOT EXISTS idx_shop_order_items_order
    ON shop_order_items(order_id);

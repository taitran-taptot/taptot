CREATE TABLE IF NOT EXISTS shop_products (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(150) UNIQUE NOT NULL,
    name_vi VARCHAR(255) NOT NULL,
    description_vi TEXT,
    price_vnd INT NOT NULL CHECK (price_vnd >= 0),
    stock_qty INT NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
    image_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shop_products_active
    ON shop_products(is_active, id DESC);

CREATE TABLE IF NOT EXISTS shop_cart_items (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES shop_products(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE (user_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_shop_cart_user
    ON shop_cart_items(user_id);

CREATE TABLE IF NOT EXISTS shop_orders (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_status VARCHAR(20) NOT NULL DEFAULT 'placed',
    total_vnd INT NOT NULL DEFAULT 0,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shop_orders_user
    ON shop_orders(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS shop_order_items (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES shop_orders(id) ON DELETE CASCADE,
    product_id INT REFERENCES shop_products(id) ON DELETE SET NULL,
    name_vi VARCHAR(255) NOT NULL,
    unit_price_vnd INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0)
);

CREATE INDEX IF NOT EXISTS idx_shop_order_items_order
    ON shop_order_items(order_id);

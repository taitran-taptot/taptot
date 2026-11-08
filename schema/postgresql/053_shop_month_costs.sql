CREATE TABLE IF NOT EXISTS shop_month_costs (
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    operating_vnd INTEGER NOT NULL DEFAULT 0,
    marketing_vnd INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (year, month)
);

CREATE TABLE IF NOT EXISTS shop_month_product_costs (
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    product_id INTEGER NOT NULL REFERENCES shop_products(id) ON DELETE CASCADE,
    cost_vnd INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (year, month, product_id)
);

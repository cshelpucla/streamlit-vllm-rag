-- Items table definition
-- Contains order line items that link orders to products
CREATE TABLE ITEMS (
    item_id INT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    discount_percent DECIMAL(5, 2) DEFAULT 0.00,
    subtotal DECIMAL(10, 2) GENERATED ALWAYS AS (quantity * unit_price * (1 - discount_percent/100)) STORED,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES ORDERS(order_id),
    FOREIGN KEY (product_id) REFERENCES PRODUCTS(product_id)
);

-- Create indexes for faster joins and lookups
CREATE INDEX idx_items_order ON ITEMS(order_id);
CREATE INDEX idx_items_product ON ITEMS(product_id);

-- Prevent negative quantities
ALTER TABLE ITEMS ADD CONSTRAINT check_positive_quantity CHECK (quantity > 0);

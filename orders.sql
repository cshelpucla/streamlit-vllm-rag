-- Orders table definition
-- Tracks all customer orders placed in the system
CREATE TABLE ORDERS (
    order_id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATETIME NOT NULL,
    total_amount DECIMAL(10, 2) DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    shipping_address TEXT,
    shipping_method VARCHAR(50),
    tracking_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES CUSTOMERS(customer_id)
);

-- Create indexes to improve query performance
CREATE INDEX idx_orders_customer ON ORDERS(customer_id);
CREATE INDEX idx_orders_date ON ORDERS(order_date);
CREATE INDEX idx_orders_status ON ORDERS(status);

-- Orders audit trigger
CREATE TRIGGER after_order_update
AFTER UPDATE ON ORDERS
FOR EACH ROW
BEGIN
    INSERT INTO order_history (order_id, field_changed, old_value, new_value, changed_at)
    VALUES (NEW.order_id, 'status', OLD.status, NEW.status, NOW());
END;

-- Products table definition
-- Stores all product information available in the inventory
CREATE TABLE PRODUCTS (
    product_id INT PRIMARY KEY,
    supplier_id INT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    price DECIMAL(10, 2) NOT NULL,
    cost DECIMAL(10, 2),
    stock_quantity INT NOT NULL DEFAULT 0,
    reorder_level INT DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    sku VARCHAR(50) UNIQUE,
    weight DECIMAL(8, 2),
    dimensions VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES SUPPLIERS(supplier_id)
);

-- Create indexes for better performance
CREATE INDEX idx_products_supplier ON PRODUCTS(supplier_id);
CREATE INDEX idx_products_category ON PRODUCTS(category);
CREATE INDEX idx_products_active ON PRODUCTS(is_active);

-- Add a full text search index for product search
CREATE FULLTEXT INDEX idx_product_search ON PRODUCTS(product_name, description);

-- Prevent negative prices
ALTER TABLE PRODUCTS ADD CONSTRAINT check_positive_price CHECK (price >= 0);

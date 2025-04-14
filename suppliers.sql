-- Suppliers table definition
-- Contains information about product suppliers and vendors
CREATE TABLE SUPPLIERS (
    supplier_id INT PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    contact_name VARCHAR(100),
    contact_title VARCHAR(50),
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    fax VARCHAR(20),
    address_line1 VARCHAR(100),
    address_line2 VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(50),
    payment_terms VARCHAR(100),
    tax_id VARCHAR(50),
    supplier_rating DECIMAL(3,2),
    is_active BOOLEAN DEFAULT TRUE,
    website VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create indexes for common supplier lookups
CREATE INDEX idx_suppliers_name ON SUPPLIERS(company_name);
CREATE INDEX idx_suppliers_location ON SUPPLIERS(country, state, city);
CREATE INDEX idx_suppliers_active ON SUPPLIERS(is_active);

-- Add view for active suppliers with good ratings
CREATE VIEW premium_suppliers AS
SELECT * FROM SUPPLIERS
WHERE is_active = TRUE AND supplier_rating > 4.0;

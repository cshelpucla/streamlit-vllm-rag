-- Customers table definition
-- Stores customer information for order processing and CRM
CREATE TABLE CUSTOMERS (
    customer_id INT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address_line1 VARCHAR(100),
    address_line2 VARCHAR(100),
    city VARCHAR(50),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'USA',
    password_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    loyalty_points INT DEFAULT 0,
    date_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    notes TEXT
);

-- Create indexes for common customer lookups
CREATE INDEX idx_customers_name ON CUSTOMERS(last_name, first_name);
CREATE INDEX idx_customers_city ON CUSTOMERS(city);
CREATE INDEX idx_customers_active ON CUSTOMERS(is_active);

-- Ensure valid email format
ALTER TABLE CUSTOMERS ADD CONSTRAINT check_email_format 
CHECK (email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$');

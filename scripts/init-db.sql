-- iqromax.uz OTP Bot - Database Initialization Script
-- This script is run automatically when the PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE iqromax_otp TO postgres;

-- Create indexes for better performance (if tables exist)
-- Note: Tables are created by SQLAlchemy, this is for additional optimizations

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully for iqromax.uz OTP Bot';
END $$;

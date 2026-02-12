-- iqromax.uz OTP Bot - Database Initialization (Local PostgreSQL)
-- For Docker: Integer schema. For Supabase use supabase/migrations/001_initial_schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

GRANT ALL PRIVILEGES ON DATABASE iqromax_otp TO postgres;

-- Legacy schema (Integer ids) for local PostgreSQL
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(20),
    language VARCHAR(8) DEFAULT 'uz',
    is_active BOOLEAN DEFAULT TRUE,
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW(),
    website_registered_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram_username ON users(telegram_username);

DO $$ BEGIN
    CREATE TYPE otpstatus AS ENUM ('pending', 'verified', 'expired', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS otp_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp_hash VARCHAR(255) NOT NULL,
    request_source VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    status otpstatus DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_otp_user_status ON otp_requests(user_id, status);

CREATE TABLE IF NOT EXISTS otp_statistics (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL UNIQUE,
    total_sent INTEGER DEFAULT 0,
    total_verified INTEGER DEFAULT 0,
    total_expired INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_logs (
    id SERIAL PRIMARY KEY,
    admin_telegram_id BIGINT NOT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admin_logs_telegram ON admin_logs(admin_telegram_id);

DO $$
BEGIN
    RAISE NOTICE 'Database initialized for iqromax.uz OTP Bot (legacy schema)';
END $$;

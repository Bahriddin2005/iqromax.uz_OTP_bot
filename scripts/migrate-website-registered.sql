-- Migration: Add website_registered_at for One Telegram = One Account
-- Run this if you have existing database before the update

-- PostgreSQL
ALTER TABLE users ADD COLUMN IF NOT EXISTS website_registered_at TIMESTAMP;

-- SQLite (run separately if using SQLite)
-- ALTER TABLE users ADD COLUMN website_registered_at DATETIME;

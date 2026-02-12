# Supabase Setup Guide

## 1. Run Schema Migration

1. Open [Supabase Dashboard](https://supabase.com/dashboard) → your project
2. Go to **SQL Editor**
3. Copy the contents of `supabase/migrations/001_initial_schema.sql`
4. Paste and **Run** the SQL

This creates:
- `public.users` (synced from `auth.users` via trigger)
- `organizations`, `organization_members`
- `otp_requests`, `audit_logs`, `sessions`
- `otp_statistics`, `admin_logs`
- RLS policies

## 2. Configure Environment

Add to your `.env`:

```env
# Use Supabase Database URL (Project Settings → Database → Connection string)
# Use "Transaction" or "Session" mode
DATABASE_URL=postgresql://postgres.[ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres

# Required for creating Telegram users (Project Settings → API)
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

**Where to find:**
- **DATABASE_URL**: Project Settings → Database → Connection string → URI
- **SUPABASE_URL**: Project Settings → API → Project URL
- **SUPABASE_SERVICE_ROLE_KEY**: Project Settings → API → service_role (secret)

## 3. Install Dependencies

```bash
pip install supabase
```

## 4. Redis (unchanged)

Keep Redis for:
- OTP code lookup (`otp:code:{code}` → telegram_id)
- Rate limiting
- Cooldown

## 5. Docker with Supabase

In `.env` or docker-compose:
```env
DATABASE_URL=postgresql://postgres.[ref]:[pw]@aws-0-[region].pooler.supabase.com:6543/postgres
USE_SUPABASE=1
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
```

## 6. Docker with local PostgreSQL

Default: `USE_SUPABASE=0`, tables created by `scripts/init-db.sql` (Integer schema).
If you see "integer and uuid" error: your DB has wrong schema. Fix:
```bash
docker-compose down -v   # remove volumes
docker-compose up -d     # fresh start with correct schema
```

## 7. Verify

1. Start the app
2. Send `/start` to the Telegram bot
3. Request OTP via API or bot
4. Verify OTP

First Telegram user triggers `auth.users` creation via Admin API; trigger syncs to `public.users`.

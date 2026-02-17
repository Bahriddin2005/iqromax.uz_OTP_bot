# IQROMAX Registration System — Production Architecture

> Senior Backend Architect Design  
> Phone → Telegram OTP → Supabase Auth | 100k+ users ready

---

## 1. Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  WEBSITE (iqromax.uz)                                                             │
│  1. User enters phone → POST /api/v1/register/send-otp { phone }                  │
│  2. (Generic success response - no enumeration)                                   │
│  3. User receives OTP in Telegram bot                                             │
│  4. User enters OTP → POST /api/v1/register/verify-otp { otp }                    │
│  5. Success → Supabase session JWT → Redirect to dashboard                        │
└─────────────────────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────────┐            ┌─────────────────────┐
│  FastAPI Backend    │            │  Telegram Bot       │
│  - Lookup phone     │───────────▶│  - Send OTP         │
│  - Create OTP       │            │  - No frontend link  │
│  - Verify OTP       │            └─────────────────────┘
│  - Create Auth      │
└─────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SUPABASE                                                                        │
│  auth.users ←─ trigger ─→ public.users                                           │
│  otp_requests (phone, telegram_user_id, otp_hash, ...)                           │
│  audit_logs                                                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Critical constraint:** Phone must be linked to Telegram *before* website registration. Users share phone via the Telegram bot first. `public.users.phone_number` + `telegram_id` is the source of truth.

---

## 2. Full Database Schema (SQL)

```sql
-- ============================================
-- EXTENSIONS
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- PUBLIC.USERS (Synced from auth.users)
-- ============================================
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    telegram_id BIGINT,
    telegram_username VARCHAR(64),
    first_name VARCHAR(128),
    last_name VARCHAR(128),
    phone_number VARCHAR(20),
    language VARCHAR(8) DEFAULT 'uz',
    avatar_url TEXT,
    raw_user_meta_data JSONB,
    raw_app_meta_data JSONB,
    is_suspended BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    website_registered_at TIMESTAMPTZ,
    last_activity TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_sign_in_at TIMESTAMPTZ
);

-- Phone → Telegram lookup (registration flow)
CREATE UNIQUE INDEX idx_users_phone ON public.users(phone_number) WHERE phone_number IS NOT NULL;
CREATE UNIQUE INDEX idx_users_telegram_id ON public.users(telegram_id) WHERE telegram_id IS NOT NULL;
CREATE INDEX idx_users_telegram_username ON public.users(telegram_username) WHERE telegram_username IS NOT NULL;
CREATE INDEX idx_users_email ON public.users(email) WHERE email IS NOT NULL;

-- ============================================
-- OTP_REQUESTS (Phone-first registration)
-- ============================================
CREATE TYPE public.otp_status AS ENUM ('pending', 'verified', 'expired', 'failed');

CREATE TABLE public.otp_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Phone + Telegram for lookup (before user may exist in auth)
    phone_number VARCHAR(20) NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    -- Optional FK when user exists
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    -- Security
    otp_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    status otp_status NOT NULL DEFAULT 'pending',
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 5,
    verified BOOLEAN DEFAULT FALSE,
    -- Metadata
    request_source VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Critical indexes
CREATE INDEX idx_otp_phone_status ON public.otp_requests(phone_number, status);
CREATE INDEX idx_otp_telegram_status ON public.otp_requests(telegram_user_id, status);
CREATE INDEX idx_otp_expires_pending ON public.otp_requests(expires_at) WHERE status = 'pending';
CREATE INDEX idx_otp_created ON public.otp_requests(created_at DESC);

-- Rate limit lookup: recent requests per phone
CREATE INDEX idx_otp_phone_created ON public.otp_requests(phone_number, created_at DESC);

-- ============================================
-- RATE_LIMIT_TRACKING (Optional - Redis preferred)
-- ============================================
CREATE TABLE public.rate_limit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(64) NOT NULL,  -- SHA256(phone + ip or ip only)
    key_type VARCHAR(20) NOT NULL,  -- 'phone', 'ip', 'phone_ip'
    attempted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rate_limit_key_time ON public.rate_limit_log(key_hash, attempted_at DESC);

-- ============================================
-- AUDIT_LOGS
-- ============================================
CREATE TABLE public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_user_created ON public.audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_action_created ON public.audit_logs(action, created_at DESC);
CREATE INDEX idx_audit_created ON public.audit_logs(created_at DESC);

-- RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.otp_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own profile" ON public.users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users update own profile" ON public.users FOR UPDATE USING (auth.uid() = id);

-- OTP: Service role only (backend); users never direct INSERT/SELECT
CREATE POLICY "Service role manages otp" ON public.otp_requests
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Users read own audit" ON public.audit_logs FOR SELECT
    USING (user_id = auth.uid());
```

---

## 3. Phone → Telegram Matching

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Bot Flow (prerequisite)                                                 │
│  User starts bot → Shares contact → phone + telegram_id stored           │
│  in public.users (or create auth.users + public.users via Admin API)     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Website Flow                                                            │
│  POST /register/send-otp { phone: "+998901234567" }                      │
│                                                                         │
│  1. Normalize phone: +998901234567                                       │
│  2. SELECT id, telegram_id FROM public.users                             │
│     WHERE phone_number = :phone AND telegram_id IS NOT NULL              │
│     LIMIT 1                                                              │
│  3. If not found → return GENERIC success (prevent enumeration)          │
│  4. If found → create OTP, send to telegram_id, return GENERIC success   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Normalization:** Store phone in E.164 (`+998901234567`). Strip spaces, leading zeros. Use `libphonenumbers` in production.

---

## 4. Secure OTP Generation & Storage

```python
# OTP flow - NEVER store plain OTP
import secrets
import hashlib
from datetime import datetime, timezone, timedelta

def generate_otp(length: int = 6) -> str:
    max_val = 10 ** length
    return str(secrets.randbelow(max_val)).zfill(length)

def hash_otp(otp: str, salt: str) -> str:
    return hashlib.sha256(f"{otp}:{salt}".encode()).hexdigest()

def verify_otp(plain: str, salt: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(plain, salt), stored_hash)

# Store in DB:
# otp_hash = hash_otp(otp, salt)
# salt = secrets.token_hex(32)
# Never log or return plain OTP except to Telegram
```

- **Expiration:** `expires_at = now() + timedelta(minutes=5)`
- **Max attempts:** 5; increment `attempts` on each verify; mark `failed` if exceeded
- **One-time:** Mark `verified=true`, `status='verified'` on success; reject reuse

---

## 5. Verification Endpoint Logic

```
POST /api/v1/register/verify-otp
Body: { "otp": "492817" }
Headers: X-API-Key, X-Request-ID (idempotency)

1. Validate OTP format (6 digits)
2. Brute-force check: Redis/IP lockout (5 wrong → 15 min lockout)
3. Lookup: Redis otp:code:{otp} → request_id (optional fast path)
   OR: SELECT * FROM otp_requests WHERE status='pending' AND expires_at > NOW()
       AND verify_otp(:otp, salt, otp_hash) = true LIMIT 1
4. If not found: record failed attempt, return generic error (same as wrong code)
5. If found:
   - Check attempts < max_attempts
   - Create auth.users (Supabase Admin API) if not exists
   - Update public.users (telegram_id, phone, website_registered_at)
   - Mark otp_request verified
   - Log audit
   - Return Supabase session (signInWithPassword or custom token)
6. Redirect: frontend receives JWT → set cookie/localStorage → redirect /dashboard
```

---

## 6. Enumeration Prevention

| Scenario | Response |
|----------|----------|
| Phone not linked | Same as success: "If this number is linked, you'll receive a code" |
| Rate limited | 429 with retry_after |
| Wrong OTP | "Invalid or expired code" (no hint) |
| Correct OTP | JWT + success |
| Expired OTP | "Invalid or expired code" |

Use constant-time string compare for OTP. Same HTTP status (200/400) for "not found" vs "invalid" where possible.

---

## 7. Rate Limiting (Redis)

```
Keys:
  otp:send:phone:{normalized_phone}     → count, TTL 1h   (max 5/hour per phone)
  otp:send:ip:{ip}                     → count, TTL 1h   (max 10/hour per IP)
  otp:send:phone_ip:{phone}:{ip}       → exists, TTL 60s (cooldown 60s same combo)
  otp:attempts:ip:{ip}                 → count, TTL 15m  (5 wrong → lockout 15m)
```

---

## 8. SQLAlchemy Models

```python
# models/otp_request.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, BigInteger, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from uuid import uuid4

class OTPStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"

class OTPRequest(Base):
    __tablename__ = "otp_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    phone_number = Column(String(20), nullable=False, index=True)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="SET NULL"))

    otp_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    status = Column(Enum(OTPStatus), default=OTPStatus.PENDING)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    verified = Column(Boolean, default=False)

    request_source = Column(String(100))
    ip_address = Column(INET)
    user_agent = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

## 9. Telegram Bot Logic

```python
# Bot responsibilities (minimal for registration):
# 1. On /start + share contact: store phone + telegram_id in public.users
# 2. On API request: send OTP message to telegram_id (no user interaction)

# Sending OTP (from FastAPI, not from bot handler):
async def send_otp_to_telegram(telegram_id: int, otp_code: str, lang: str = "uz") -> bool:
    text = get_otp_message(lang, otp_code)  # e.g. "Sizning OTP kodingiz: 492817"
    try:
        await bot.send_message(telegram_id, text)
        return True
    except Exception:
        return False
```

- **No link between website session and bot.** Website only knows phone; backend resolves telegram_id from DB.
- **Single OTP per pending request.** Invalidate previous pending OTP for same phone before creating new one.

---

## 10. Folder Structure

```
iqromax-otp-bot/
├── src/
│   ├── api/
│   │   ├── app.py              # FastAPI app
│   │   ├── routes.py           # Legacy: telegram_id/username OTP
│   │   ├── register_routes.py  # NEW: phone-first /register/send-otp, /verify-otp
│   │   └── schemas.py          # Request/response models
│   ├── bot/
│   │   ├── bot.py
│   │   ├── handlers.py         # /start, contact share
│   │   └── locales.py
│   ├── services/
│   │   ├── otp_service.py      # create_otp, verify_otp, hash, lookup
│   │   ├── registration_service.py  # NEW: phone lookup, auth creation
│   │   └── supabase_auth.py    # create_telegram_user, sign_in
│   ├── models/
│   │   ├── database.py
│   │   ├── supabase_models.py
│   │   └── redis_client.py
│   ├── utils/
│   │   ├── security.py         # brute_force, validate_phone
│   │   └── rate_limit.py       # Redis rate limits
│   └── config/
│       └── settings.py
├── supabase/
│   └── migrations/
│       └── 002_otp_phone_schema.sql
├── scripts/
│   └── cleanup_expired_otp.py  # Cron: DELETE FROM otp_requests WHERE status='pending' AND expires_at < NOW()
└── docs/
    ├── PRODUCTION-ARCHITECTURE.md
    └── REGISTRATION-ARCHITECTURE.md  # This file
```

---

## 11. Background Tasks

| Task | Frequency | Action |
|------|-----------|--------|
| Expired OTP cleanup | Every 5 min | `UPDATE otp_requests SET status='expired' WHERE status='pending' AND expires_at < NOW()` |
| Rate limit log trim | Daily | Delete `rate_limit_log` older than 24h |
| Audit log partition | Monthly | Partition by month for 100k+ scale |

Use `asyncio` background task or Celery for cleanup. For 100k users, consider pg_cron or external scheduler.

---

## 12. Production Best Practices

1. **Connection pooling:** SQLAlchemy `create_async_engine` with `pool_size=20`, `max_overflow=10`
2. **Idempotency:** `X-Idempotency-Key` on verify to avoid double-apply
3. **Logging:** Never log OTP, tokens, or full phone numbers (mask: `+998***4567`)
4. **Health:** `/health` checks DB, Redis, Supabase connectivity
5. **CORS:** Restrict to iqromax.uz origins
6. **Helmet/security headers:** HSTS, X-Content-Type-Options
7. **Migrations:** Alembic for all schema changes; never manual ALTER in prod

---

## 13. Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Returning "phone not found" | Enumeration attack | Generic success message |
| Storing plain OTP | DB leak = full compromise | Always hash with salt |
| Trusting frontend identity | Spoofing | Resolve from OTP/DB only |
| No rate limit on send | SMS/Telegram abuse | Per-phone + per-IP limits |
| No brute-force on verify | 6-digit brute force | 5 attempts → 15 min lockout |
| otp_requests.user_id NOT NULL | Can't create OTP before auth | Make user_id nullable |
| Single pending OTP per user | Blocks resend | One pending per phone; invalidate on new send |
| Sync cleanup job | Blocks API | Async or separate worker |

---

## 14. Scalability (100k+ Users)

- **Read replicas:** Use for audit_logs, analytics; write to primary
- **Redis cluster:** For rate limits and OTP caching (optional)
- **Indexes:** All lookup paths indexed (phone, telegram_id, expires_at)
- **Partitioning:** `audit_logs` by `created_at` monthly
- **Stateless API:** No in-memory sessions; horizontal scaling
- **CDN:** Static assets; API behind load balancer

---

## 15. API Contract Summary

```
POST /api/v1/register/send-otp
  Body: { "phone": "+998901234567" }
  Headers: X-API-Key
  Response: { "success": true, "message": "..." }  # Always same structure

POST /api/v1/register/verify-otp
  Body: { "otp": "492817" }
  Headers: X-API-Key, X-Idempotency-Key (optional)
  Response: { "success": true, "data": { "access_token", "refresh_token", "user": {...} } }
  # Or Supabase session URL for redirect
```

---

*Document version: 1.0 | IQROMAX Production Registration*

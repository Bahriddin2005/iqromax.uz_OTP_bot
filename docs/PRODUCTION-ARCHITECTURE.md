# Production-Grade SaaS Architecture
## FastAPI + Supabase + Multi-Tenant + OTP + Telegram

> Senior Backend Architect Design — Production-ready, scalable, maintainable

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                      │
│  Web App │ Mobile App │ Telegram Bot │ API Clients                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY / LOAD BALANCER                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│  FastAPI #1   │          │  FastAPI #2   │          │  FastAPI #N   │
│  (Stateless)  │          │  (Stateless)  │          │  (Stateless)  │
└───────────────┘          └───────────────┘          └───────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SUPABASE (PostgreSQL + Auth)                      │
│  auth.users  ←── trigger ──→  public.users  ←── FK ──→  app tables       │
│  RLS enabled │ Triggers for sync │ UUID everywhere                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│    Redis      │          │  Celery/Worker│          │  Telegram API │
│  Cache/Queue  │          │  Background   │          │  Webhook      │
└───────────────┘          └───────────────┘          └───────────────┘
```

**Key Principles:**
- **Stateless API** — No in-memory sessions; scale horizontally
- **auth.users = Source of Truth** — Auth handled by Supabase; we sync to public.users
- **Event-Driven Sync** — DB triggers keep public.users in sync with auth.users
- **UUID Everywhere** — No integer IDs; safe for distributed systems

---

## 2. Full SQL Schema (Supabase)

```sql
-- ============================================
-- EXTENSIONS
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- PUBLIC.USERS (Synced from auth.users)
-- ============================================
-- Sync via trigger; never insert directly from app
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    telegram_id BIGINT UNIQUE,
    telegram_username VARCHAR(64),
    first_name VARCHAR(128),
    last_name VARCHAR(128),
    avatar_url TEXT,
    raw_user_meta_data JSONB,
    raw_app_meta_data JSONB,
    is_suspended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_sign_in_at TIMESTAMPTZ
);

-- Index for Telegram lookups (OTP routing)
CREATE UNIQUE INDEX idx_users_telegram_id ON public.users(telegram_id) WHERE telegram_id IS NOT NULL;
CREATE INDEX idx_users_telegram_username ON public.users(telegram_username) WHERE telegram_username IS NOT NULL;
CREATE INDEX idx_users_email ON public.users(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_updated_at ON public.users(updated_at);

COMMENT ON TABLE public.users IS '1:1 sync with auth.users. Synced via trigger.';

-- ============================================
-- SYNC TRIGGER: auth.users → public.users
-- ============================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.users (id, email, raw_user_meta_data, raw_app_meta_data, last_sign_in_at)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data,
        NEW.raw_app_meta_data,
        NEW.last_sign_in_at
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        raw_user_meta_data = EXCLUDED.raw_user_meta_data,
        raw_app_meta_data = EXCLUDED.raw_app_meta_data,
        last_sign_in_at = EXCLUDED.last_sign_in_at,
        updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Trigger on auth.users insert (EXECUTE PROCEDURE for PG < 14 compatibility)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT OR UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE PROCEDURE public.handle_new_user();

-- Backfill existing auth.users (run once)
INSERT INTO public.users (id, email, raw_user_meta_data, raw_app_meta_data, last_sign_in_at)
SELECT id, email, raw_user_meta_data, raw_app_meta_data, last_sign_in_at
FROM auth.users
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- ORGANIZATIONS (Multi-Tenant)
-- ============================================
CREATE TABLE public.organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON public.organizations(slug);

-- ============================================
-- ORGANIZATION_MEMBERS
-- ============================================
CREATE TYPE public.org_role AS ENUM ('owner', 'admin', 'member', 'viewer');

CREATE TABLE public.organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role org_role NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

CREATE INDEX idx_org_members_org ON public.organization_members(organization_id);
CREATE INDEX idx_org_members_user ON public.organization_members(user_id);

-- ============================================
-- OTP_REQUESTS
-- ============================================
CREATE TYPE public.otp_status AS ENUM ('pending', 'verified', 'expired', 'failed');

CREATE TABLE public.otp_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    otp_hash VARCHAR(255) NOT NULL,
    status otp_status NOT NULL DEFAULT 'pending',
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 5,
    request_source VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Critical indexes for OTP
CREATE INDEX idx_otp_user_status ON public.otp_requests(user_id, status);
CREATE INDEX idx_otp_expires_at ON public.otp_requests(expires_at) WHERE status = 'pending';
CREATE INDEX idx_otp_created_at ON public.otp_requests(created_at);

-- Prevent multiple pending OTPs per user (optional, enforce in app)
-- CREATE UNIQUE INDEX idx_otp_one_pending_per_user ON public.otp_requests(user_id) WHERE status = 'pending';

-- ============================================
-- AUDIT_LOGS
-- ============================================
CREATE TABLE public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_org_created ON public.audit_logs(organization_id, created_at DESC);
CREATE INDEX idx_audit_user_created ON public.audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_action ON public.audit_logs(action, created_at DESC);
CREATE INDEX idx_audit_created ON public.audit_logs(created_at DESC);

-- ============================================
-- SESSIONS (Optional custom tracking)
-- ============================================
CREATE TABLE public.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON public.sessions(user_id);
CREATE INDEX idx_sessions_expires ON public.sessions(expires_at);
CREATE UNIQUE INDEX idx_sessions_token ON public.sessions(token_hash);

-- ============================================
-- UPDATED_AT TRIGGER
-- ============================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();
CREATE TRIGGER orgs_updated_at BEFORE UPDATE ON public.organizations
    FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();
```

---

## 3. Row Level Security (RLS) Policies

```sql
-- ============================================
-- ENABLE RLS ON ALL TABLES
-- ============================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.otp_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;

-- ============================================
-- USERS
-- ============================================
-- Users can read their own row
CREATE POLICY "Users can read own profile"
    ON public.users FOR SELECT
    USING (auth.uid() = id);

-- Users can update their own row (limited columns via app)
CREATE POLICY "Users can update own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

-- Service role bypasses RLS (FastAPI uses service key for backend ops)

-- ============================================
-- ORGANIZATIONS
-- ============================================
CREATE POLICY "Members can read org"
    ON public.organizations FOR SELECT
    USING (
        id IN (
            SELECT organization_id FROM public.organization_members
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Admins can update org"
    ON public.organizations FOR UPDATE
    USING (
        id IN (
            SELECT organization_id FROM public.organization_members
            WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
        )
    );

-- ============================================
-- ORGANIZATION_MEMBERS
-- ============================================
CREATE POLICY "Members can read org members"
    ON public.organization_members FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM public.organization_members
            WHERE user_id = auth.uid()
        )
    );

-- ============================================
-- OTP_REQUESTS
-- ============================================
-- Users can only see their own OTP requests (read for status check)
CREATE POLICY "Users can read own otp"
    ON public.otp_requests FOR SELECT
    USING (user_id = auth.uid());

-- INSERT/UPDATE: Typically done by service role only (backend)
-- No direct user INSERT for security

-- ============================================
-- AUDIT_LOGS
-- ============================================
CREATE POLICY "Members can read org audit"
    ON public.audit_logs FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM public.organization_members
            WHERE user_id = auth.uid()
        )
        OR user_id = auth.uid()
    );

-- ============================================
-- SESSIONS
-- ============================================
CREATE POLICY "Users can read own sessions"
    ON public.sessions FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can delete own sessions"
    ON public.sessions FOR DELETE
    USING (user_id = auth.uid());
```

---

## 4. SQLAlchemy Models (Python)

```python
# models/base.py
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import declarative_base

Base = declarative_base()

def uuid_column(default=None):
    from uuid import uuid4
    return Column(UUID(as_uuid=True), primary_key=True, default=default or uuid4)

# models/user.py
from sqlalchemy import Column, String, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True)  # FK to auth.users
    email = Column(String)
    telegram_id = Column(BigInteger, unique=True, index=True)
    telegram_username = Column(String(64), index=True)
    first_name = Column(String(128))
    last_name = Column(String(128))
    avatar_url = Column(String)
    raw_user_meta_data = Column(JSONB)
    raw_app_meta_data = Column(JSONB)
    is_suspended = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_sign_in_at = Column(DateTime(timezone=True))

# models/organization.py
class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    settings = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# models/organization_member.py
import enum
class OrgRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        {"schema": "public"},
        UniqueConstraint("organization_id", "user_id", name="uq_org_member")
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    organization_id = Column(UUID(as_uuid=True), ForeignKey("public.organizations.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"))
    role = Column(Enum(OrgRole), default=OrgRole.MEMBER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# models/otp_request.py
class OTPStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"

class OTPRequest(Base):
    __tablename__ = "otp_requests"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    otp_hash = Column(String(255), nullable=False)
    status = Column(Enum(OTPStatus), default=OTPStatus.PENDING)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    request_source = Column(String(100))
    ip_address = Column(INET)
    user_agent = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

## 5. OTP System Design (Production)

| Aspect | Implementation |
|--------|----------------|
| **Storage** | `otp_hash` = SHA-256(otp + salt). Never store plain OTP. |
| **Expiration** | 5 min (`expires_at`). Cleanup job deletes expired. |
| **Rate limiting** | Redis: `otp:rate:{user_id}` — max 5/hour. |
| **Cooldown** | Redis: `otp:cooldown:{user_id}` — 60s between requests. |
| **Brute-force** | Redis: `otp:attempts:{ip}` — lockout after 10 wrong OTPs. |
| **Lookup by code** | Redis: `otp:code:{code}` → `user_id` (TTL 5 min). Website sends only code. |
| **Indexes** | `(user_id, status)`, `(expires_at) WHERE status='pending'`. |

```python
# OTP flow
# 1. send_otp: username (routing) → lookup user_id → generate OTP → hash → save DB + Redis
# 2. verify_otp: code only → Redis lookup user_id → verify hash → check attempts → mark used
# 3. Identity from DB only, never from frontend
```

---

## 6. Index Strategy Summary

| Table | Index | Purpose |
|-------|-------|---------|
| users | `telegram_id` UNIQUE | OTP routing lookup |
| users | `telegram_username` | Lookup by @handle |
| users | `email` | Auth sync |
| otp_requests | `(user_id, status)` | Active OTP lookup |
| otp_requests | `expires_at` WHERE pending | Cleanup job |
| organization_members | `(organization_id)` | List members |
| organization_members | `(user_id)` | List user's orgs |
| audit_logs | `(organization_id, created_at DESC)` | Org audit trail |
| audit_logs | `(user_id, created_at DESC)` | User activity |
| sessions | `token_hash` UNIQUE | Session lookup |

---

## 7. Common Mistakes to Avoid

| Mistake | Why Bad | Fix |
|---------|---------|-----|
| Direct FK to auth.users from app tables | Schema coupling; Supabase manages auth | Use public.users as bridge |
| Integer IDs | Not safe for distributed/merge | UUID everywhere |
| Storing plain OTP | DB leak = full compromise | Always hash |
| Trusting frontend for identity | Spoofing | Resolve from OTP/DB only |
| No RLS | Any user can read all rows | RLS + least privilege |
| Synchronous sync auth→public | Race conditions | Trigger-based |
| One Redis key for all OTPs | No isolation | Per-user keys |
| Missing expiration index | Full table scan on cleanup | Partial index on expires_at |

---

## 8. Production Best Practices

1. **Use Supabase Service Role** for backend FastAPI; never expose to frontend.
2. **JWT validation** at API gateway; pass `user_id` in context.
3. **Connection pooling** — SQLAlchemy `QueuePool`, size = 10–20.
4. **Read replicas** — Use for audit/analytics; write to primary.
5. **Idempotency** — OTP create/verify with idempotency keys for retries.
6. **Structured logging** — `structlog`; never log OTP or tokens.
7. **Health checks** — `/health` for DB, Redis, Supabase.
8. **Migrations** — Alembic; never manual ALTER in prod.

---

## 9. Relationship Diagram (Text)

```
auth.users (Supabase)
    │
    │ trigger: handle_new_user
    ▼
public.users ◄──────────────────┐
    │                           │
    │ 1:N                       │ N:1
    ▼                           │
organization_members ───────────┘
    │
    │ N:1
    ▼
organizations

public.users
    │ 1:N
    ├──► otp_requests
    ├──► sessions
    └──► audit_logs (as user_id)

organizations
    │ 1:N
    └──► audit_logs (as organization_id)
```

---

## 10. Event-Based Sync (auth.users → public.users)

- **Trigger** runs on `INSERT`/`UPDATE` of `auth.users`.
- **`handle_new_user()`** inserts or updates `public.users` with `ON CONFLICT DO UPDATE`.
- **Backfill** script for existing users: one-time `INSERT ... SELECT FROM auth.users`.
- **Telegram link** — app updates `public.users.telegram_id` after OTP verify; no direct link to auth.

This keeps `auth.users` as source of truth while giving the app a stable `public.users` table for joins and RLS.

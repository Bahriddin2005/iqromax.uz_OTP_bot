-- ============================================
-- iqromax OTP Bot - Supabase Production Schema
-- Run in Supabase Dashboard → SQL Editor
-- ============================================

-- Extensions
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

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT OR UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE PROCEDURE public.handle_new_user();

-- Backfill existing auth.users
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

CREATE INDEX idx_otp_user_status ON public.otp_requests(user_id, status);
CREATE INDEX idx_otp_expires_at ON public.otp_requests(expires_at) WHERE status = 'pending';
CREATE INDEX idx_otp_created_at ON public.otp_requests(created_at);

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
-- SESSIONS (Optional)
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
-- OTP_STATISTICS (admin dashboard)
-- ============================================
CREATE TABLE public.otp_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL UNIQUE,
    total_sent INT DEFAULT 0,
    total_verified INT DEFAULT 0,
    total_expired INT DEFAULT 0,
    total_failed INT DEFAULT 0,
    unique_users INT DEFAULT 0,
    new_users INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ADMIN_LOGS (audit trail)
-- ============================================
CREATE TABLE public.admin_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_telegram_id BIGINT NOT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_admin_logs_telegram ON public.admin_logs(admin_telegram_id);
CREATE INDEX idx_admin_logs_created ON public.admin_logs(created_at DESC);

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

DROP TRIGGER IF EXISTS users_updated_at ON public.users;
CREATE TRIGGER users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();

DROP TRIGGER IF EXISTS orgs_updated_at ON public.organizations;
CREATE TRIGGER orgs_updated_at BEFORE UPDATE ON public.organizations
    FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.otp_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;

-- USERS
CREATE POLICY "Users can read own profile"
    ON public.users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

-- ORGANIZATIONS
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

-- ORGANIZATION_MEMBERS
CREATE POLICY "Members can read org members"
    ON public.organization_members FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM public.organization_members
            WHERE user_id = auth.uid()
        )
    );

-- OTP_REQUESTS
CREATE POLICY "Users can read own otp"
    ON public.otp_requests FOR SELECT
    USING (user_id = auth.uid());

-- AUDIT_LOGS
CREATE POLICY "Members can read org audit"
    ON public.audit_logs FOR SELECT
    USING (
        organization_id IN (
            SELECT organization_id FROM public.organization_members
            WHERE user_id = auth.uid()
        )
        OR user_id = auth.uid()
    );

-- SESSIONS
CREATE POLICY "Users can read own sessions"
    ON public.sessions FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can delete own sessions"
    ON public.sessions FOR DELETE
    USING (user_id = auth.uid());

"""
Production-ready SQLAlchemy models for Supabase (PostgreSQL).
Use with: DATABASE_URL = postgresql://... (Supabase connection string)

Drop-in replacement when migrating from SQLite to Supabase.
"""

from datetime import datetime
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, Boolean, Integer, BigInteger, Text, DateTime, ForeignKey,
    UniqueConstraint, Enum as SQLEnum, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


# --- Enums ---
class OrgRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OTPStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"


class Language(str, enum.Enum):
    UZ = "uz"
    EN = "en"
    RU = "ru"
    KK = "kk"
    KY = "ky"
    TG = "tg"


# --- Models ---
class User(Base):
    """1:1 sync with auth.users. Synced via Supabase trigger."""
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String)
    telegram_id = Column(BigInteger, unique=True, index=True)
    telegram_username = Column(String(64), index=True)
    first_name = Column(String(128))
    last_name = Column(String(128))
    phone_number = Column(String(20))
    language = Column(String(8), default="uz")
    avatar_url = Column(String)
    website_registered_at = Column(DateTime(timezone=True))
    raw_user_meta_data = Column(JSONB)
    raw_app_meta_data = Column(JSONB)
    is_suspended = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_sign_in_at = Column(DateTime(timezone=True))

    # Relationships
    otp_requests = relationship("OTPRequest", back_populates="user", lazy="dynamic")
    org_memberships = relationship("OrganizationMember", back_populates="user")
    sessions = relationship("Session", back_populates="user")


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    settings = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    members = relationship("OrganizationMember", back_populates="organization")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        {"schema": "public"},
        UniqueConstraint("organization_id", "user_id", name="uq_org_member")
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("public.organizations.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"))
    role = Column(SQLEnum(OrgRole), default=OrgRole.MEMBER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="org_memberships")


class OTPRequest(Base):
    __tablename__ = "otp_requests"
    __table_args__ = (
        {"schema": "public"},
        Index("idx_otp_user_status", "user_id", "status"),
        Index("idx_otp_expires_at", "expires_at", postgresql_where=text("status = 'pending'")),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"))
    otp_hash = Column(String(255), nullable=False)
    status = Column(SQLEnum(OTPStatus), default=OTPStatus.PENDING)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    request_source = Column(String(100))
    ip_address = Column(INET)
    user_agent = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="otp_requests")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("public.organizations.id", ondelete="SET NULL"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(UUID(as_uuid=True))
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    """Optional custom session tracking."""
    __tablename__ = "sessions"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"))
    token_hash = Column(String(255), nullable=False, unique=True)
    ip_address = Column(INET)
    user_agent = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sessions")

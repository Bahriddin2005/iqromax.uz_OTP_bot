"""
iqromax.uz OTP Bot - Database Models and Connection
SQLAlchemy ORM - PostgreSQL (Supabase) or SQLite (dev)
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.config import settings

# Detect backend: Supabase = USE_SUPABASE env, or URL contains supabase, or SUPABASE_URL set
# Local PostgreSQL (Docker db) → use legacy Integer schema
_url = settings.DATABASE_URL.lower()
USE_SUPABASE = (
    settings.USE_SUPABASE
    or ("postgres" in _url and ("supabase.co" in _url or "pooler.supabase.com" in _url or "supabase.com" in _url))
    or ("postgres" in _url and bool(settings.SUPABASE_URL))
)

if USE_SUPABASE:
    from src.models.supabase_models import (
        Base, User, OTPRequest, OTPStatistics, AdminLog,
        Organization, OrganizationMember, AuditLog, Session as SessionModel,
        OTPStatus, Language, OrgRole
    )
else:
    from datetime import datetime
    import enum
    from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Text, Index, ForeignKey, Enum as SQLEnum
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import relationship

    Base = declarative_base()

    class OTPStatus(enum.Enum):
        PENDING = "pending"
        VERIFIED = "verified"
        EXPIRED = "expired"
        FAILED = "failed"

    class Language(enum.Enum):
        UZ = "uz"
        EN = "en"
        RU = "ru"
        KK = "kk"
        KY = "ky"
        TG = "tg"

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True, autoincrement=True)
        telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
        telegram_username = Column(String(255), nullable=True, index=True)
        first_name = Column(String(255), nullable=True)
        last_name = Column(String(255), nullable=True)
        phone_number = Column(String(20), nullable=True)
        language = Column(SQLEnum(Language), default=Language.UZ)
        is_active = Column(Boolean, default=True)
        is_blocked = Column(Boolean, default=False)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        last_activity = Column(DateTime, default=datetime.utcnow)
        website_registered_at = Column(DateTime, nullable=True)
        otp_requests = relationship("OTPRequest", back_populates="user", lazy="dynamic")

    class OTPRequest(Base):
        __tablename__ = "otp_requests"
        id = Column(Integer, primary_key=True, autoincrement=True)
        user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
        otp_hash = Column(String(255), nullable=False)
        request_source = Column(String(100), nullable=True)
        ip_address = Column(String(45), nullable=True)
        user_agent = Column(Text, nullable=True)
        status = Column(SQLEnum(OTPStatus), default=OTPStatus.PENDING)
        attempts = Column(Integer, default=0)
        max_attempts = Column(Integer, default=3)
        created_at = Column(DateTime, default=datetime.utcnow)
        expires_at = Column(DateTime, nullable=False)
        verified_at = Column(DateTime, nullable=True)
        user = relationship("User", back_populates="otp_requests")

        @property
        def is_expired(self) -> bool:
            return datetime.utcnow() > self.expires_at

        @property
        def has_attempts_left(self) -> bool:
            return self.attempts < self.max_attempts

    class OTPStatistics(Base):
        __tablename__ = "otp_statistics"
        id = Column(Integer, primary_key=True, autoincrement=True)
        date = Column(DateTime, nullable=False, unique=True, index=True)
        total_sent = Column(Integer, default=0)
        total_verified = Column(Integer, default=0)
        total_expired = Column(Integer, default=0)
        total_failed = Column(Integer, default=0)
        unique_users = Column(Integer, default=0)
        new_users = Column(Integer, default=0)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class AdminLog(Base):
        __tablename__ = "admin_logs"
        id = Column(Integer, primary_key=True, autoincrement=True)
        admin_telegram_id = Column(BigInteger, nullable=False, index=True)
        action = Column(String(100), nullable=False)
        details = Column(Text, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)

    Organization = OrganizationMember = AuditLog = SessionModel = OrgRole = None  # Not used for SQLite


engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database. For PostgreSQL/Supabase, schema is managed by migrations."""
    if USE_SUPABASE:
        # Schema created via supabase/migrations/001_initial_schema.sql
        return
    Base.metadata.create_all(bind=engine)
    _migrate_add_website_registered_at()


def _migrate_add_website_registered_at():
    if USE_SUPABASE:
        return
    from sqlalchemy import inspect
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("users")]
    if "website_registered_at" in cols:
        return
    col_type = "DATETIME" if "sqlite" in str(engine.url) else "TIMESTAMP"
    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE users ADD COLUMN website_registered_at {col_type}"))
        conn.commit()


def drop_db():
    Base.metadata.drop_all(bind=engine)

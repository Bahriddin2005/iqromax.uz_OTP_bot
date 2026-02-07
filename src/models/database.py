"""
iqromax.uz OTP Bot - Database Models and Connection
SQLAlchemy ORM with PostgreSQL
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, 
    DateTime, Boolean, Text, Index, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool
import enum

from src.config import settings


# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Enable connection health checks
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class OTPStatus(enum.Enum):
    """OTP verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"


class Language(enum.Enum):
    """Supported languages"""
    UZ = "uz"   # O'zbek tili
    EN = "en"   # Ingliz tili
    RU = "ru"   # Rus tili
    KK = "kk"   # Qozoq tili
    KY = "ky"   # Qirg'iz tili
    TG = "tg"   # Tojik tili


class User(Base):
    """
    Telegram users who have interacted with the bot
    """
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
    website_registered_at = Column(DateTime, nullable=True)  # One Telegram = One Account
    
    # Relationships
    otp_requests = relationship("OTPRequest", back_populates="user", lazy="dynamic")
    
    __table_args__ = (
        Index("idx_user_telegram_username", "telegram_username"),
    )
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.telegram_username})>"


class OTPRequest(Base):
    """
    OTP verification requests
    """
    __tablename__ = "otp_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # OTP data (hash stored, not plain text)
    otp_hash = Column(String(255), nullable=False)
    
    # Request metadata
    request_source = Column(String(100), nullable=True)  # e.g., "web_registration"
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(SQLEnum(OTPStatus), default=OTPStatus.PENDING)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="otp_requests")
    
    __table_args__ = (
        Index("idx_otp_user_status", "user_id", "status"),
        Index("idx_otp_created_at", "created_at"),
        Index("idx_otp_expires_at", "expires_at"),
    )
    
    def __repr__(self):
        return f"<OTPRequest(id={self.id}, user_id={self.user_id}, status={self.status})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if OTP has expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def has_attempts_left(self) -> bool:
        """Check if user has attempts remaining"""
        return self.attempts < self.max_attempts


class OTPStatistics(Base):
    """
    Daily OTP statistics for admin dashboard
    """
    __tablename__ = "otp_statistics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    
    # Counts
    total_sent = Column(Integer, default=0)
    total_verified = Column(Integer, default=0)
    total_expired = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    
    # Unique users
    unique_users = Column(Integer, default=0)
    new_users = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<OTPStatistics(date={self.date}, sent={self.total_sent}, verified={self.total_verified})>"


class AdminLog(Base):
    """
    Admin action logs for audit trail
    """
    __tablename__ = "admin_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_telegram_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AdminLog(admin={self.admin_telegram_id}, action={self.action})>"


# Database utility functions
def get_db() -> Session:
    """
    Get database session (dependency injection for FastAPI)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables
    """
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all database tables (use with caution!)
    """
    Base.metadata.drop_all(bind=engine)

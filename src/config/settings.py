"""
iqromax.uz OTP Bot - Configuration Settings
Production-ready configuration with environment variables
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "iqromax.uz OTP Bot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production")
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = Field(..., description="Telegram Bot Token from @BotFather")
    TELEGRAM_WEBHOOK_URL: Optional[str] = Field(default=None, description="Webhook URL for production")
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Webhook secret token")
    
    # Database - PostgreSQL
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/iqromax_otp",
        description="PostgreSQL connection string"
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    
    # OTP Settings
    OTP_LENGTH: int = Field(default=6, ge=4, le=8)
    OTP_EXPIRY_MINUTES: int = Field(default=3, ge=1, le=10)
    OTP_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=5)
    OTP_RATE_LIMIT_MINUTES: int = Field(default=1, description="Minimum time between OTP requests")
    OTP_MAX_REQUESTS_PER_HOUR: int = Field(default=5, description="Maximum OTP requests per hour per user")
    
    # Security
    API_SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production",
        description="Secret key for API authentication"
    )
    ALLOWED_ORIGINS: str = Field(
        default="https://iqromax.uz,https://www.iqromax.uz",
        description="Comma-separated list of allowed CORS origins"
    )
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    
    # Admin
    ADMIN_TELEGRAM_IDS: str = Field(
        default="",
        description="Comma-separated list of admin Telegram IDs"
    )
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: Optional[str] = Field(default="logs/app.log")
    
    # Server
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins from comma-separated string"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
    
    @property
    def admin_telegram_ids_list(self) -> list[int]:
        """Parse admin Telegram IDs from comma-separated string"""
        if not self.ADMIN_TELEGRAM_IDS:
            return []
        return [int(id.strip()) for id in self.ADMIN_TELEGRAM_IDS.split(",") if id.strip()]


# Global settings instance
settings = Settings()


# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

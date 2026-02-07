"""
iqromax.uz OTP Bot - API Schemas
Pydantic models for request/response validation
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

from src.config import settings


# ==========================================
# Request Schemas
# ==========================================

class SendOTPRequest(BaseModel):
    """
    Request schema for sending OTP
    """
    telegram_id: Optional[int] = Field(
        None,
        description="User's Telegram ID",
        examples=[123456789]
    )
    telegram_username: Optional[str] = Field(
        None,
        description="User's Telegram username (without @)",
        examples=["johndoe"]
    )
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="User's name for personalization",
        examples=["John Doe"]
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="User's phone number (optional)",
        examples=["+998901234567"]
    )
    source: str = Field(
        default="web_registration",
        max_length=100,
        description="Request source identifier",
        examples=["web_registration", "password_reset"]
    )
    
    @field_validator("telegram_username")
    @classmethod
    def validate_username(cls, v):
        if v:
            # Remove @ if present
            v = v.lstrip("@")
            if len(v) < 5 or len(v) > 32:
                raise ValueError("Username must be 5-32 characters")
        return v
    
    @field_validator("telegram_id", "telegram_username")
    @classmethod
    def validate_identifier(cls, v, info):
        # At least one identifier must be provided (checked in endpoint)
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "telegram_id": 123456789,
                "telegram_username": "johndoe",
                "name": "John Doe",
                "phone": "+998901234567",
                "source": "web_registration"
            }
        }


class VerifyOTPRequest(BaseModel):
    """
    Request schema for verifying OTP.
    Website sends ONLY OTP code - identity comes from backend (Telegram data).
    """
    otp: str = Field(
        ...,
        min_length=settings.OTP_LENGTH,
        max_length=settings.OTP_LENGTH,
        description=f"OTP code ({settings.OTP_LENGTH} digits) - ONLY field from website",
        examples=["492817"]
    )
    
    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v):
        if not v or not v.isdigit():
            raise ValueError("OTP must contain only digits")
        if len(v) != settings.OTP_LENGTH:
            raise ValueError(f"OTP must be exactly {settings.OTP_LENGTH} digits")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {"otp": "492817"}
        }


class ResendOTPRequest(BaseModel):
    """
    Request schema for resending OTP
    """
    telegram_id: Optional[int] = Field(
        None,
        description="User's Telegram ID"
    )
    telegram_username: Optional[str] = Field(
        None,
        description="User's Telegram username"
    )
    source: str = Field(
        default="web_registration",
        description="Request source"
    )


# ==========================================
# Response Schemas
# ==========================================

class BaseResponse(BaseModel):
    """
    Base response schema
    """
    success: bool = Field(description="Operation success status")
    message: str = Field(description="Human-readable message")
    code: str = Field(description="Machine-readable status code")


class SendOTPResponse(BaseResponse):
    """
    Response schema for send OTP
    """
    data: Optional[dict] = Field(
        None,
        description="Additional response data"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "OTP yuborildi",
                "code": "otp_sent",
                "data": {
                    "expires_in": 180,
                    "max_attempts": 3
                }
            }
        }


class VerifyOTPResponse(BaseResponse):
    """
    Response schema for verify OTP.
    Contains real Telegram identity from backend (never from frontend).
    """
    data: Optional[dict] = Field(
        None,
        description="Verification result: telegram_id, telegram_username, first_name from Telegram"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "OTP tasdiqlandi",
                "code": "verified",
                "data": {
                    "telegram_id": 123456789,
                    "telegram_username": "johndoe",
                    "first_name": "John",
                    "verified_at": "2024-01-15T10:30:00Z"
                }
            }
        }


class OTPStatusResponse(BaseResponse):
    """
    Response schema for OTP status
    """
    data: Optional[dict] = Field(
        None,
        description="Current OTP status"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "OTP holati",
                "code": "status",
                "data": {
                    "status": "pending",
                    "attempts": 1,
                    "max_attempts": 3,
                    "remaining_attempts": 2,
                    "expires_in_seconds": 120
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Error response schema
    """
    success: bool = Field(default=False)
    message: str = Field(description="Error message")
    code: str = Field(description="Error code")
    details: Optional[dict] = Field(
        None,
        description="Additional error details"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "Rate limit exceeded",
                "code": "rate_limit",
                "details": {
                    "retry_after": 60
                }
            }
        }


class HealthResponse(BaseModel):
    """
    Health check response schema
    """
    status: Literal["healthy", "unhealthy"] = Field(
        description="Service health status"
    )
    version: str = Field(description="Application version")
    timestamp: datetime = Field(description="Current server time")
    services: dict = Field(description="Status of dependent services")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "database": "connected",
                    "redis": "connected",
                    "telegram_bot": "running"
                }
            }
        }


class StatisticsResponse(BaseModel):
    """
    Statistics response schema (admin only)
    """
    success: bool = True
    data: dict = Field(description="Statistics data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total_users": 1500,
                    "active_today": 250,
                    "otp_sent_today": 180,
                    "otp_verified_today": 165,
                    "success_rate": 91.7
                }
            }
        }

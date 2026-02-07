"""API module"""
from .app import app
from .routes import router
from .schemas import (
    SendOTPRequest, SendOTPResponse,
    VerifyOTPRequest, VerifyOTPResponse,
    ErrorResponse, HealthResponse
)

__all__ = [
    "app", "router",
    "SendOTPRequest", "SendOTPResponse",
    "VerifyOTPRequest", "VerifyOTPResponse",
    "ErrorResponse", "HealthResponse"
]

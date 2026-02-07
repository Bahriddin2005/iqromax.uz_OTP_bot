"""
iqromax.uz OTP Bot - API Routes
FastAPI REST API endpoints for OTP operations
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session

from src.config import settings
from src.models import get_db, redis_client, User
from src.services import get_otp_service
from src.utils import (
    verify_api_key, validate_telegram_id, validate_telegram_username,
    validate_otp_code, get_client_ip, brute_force
)
from src.bot import telegram_bot
from src.api.schemas import (
    SendOTPRequest, SendOTPResponse,
    VerifyOTPRequest, VerifyOTPResponse,
    ResendOTPRequest, OTPStatusResponse,
    ErrorResponse, HealthResponse, StatisticsResponse
)


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["OTP"])


# ==========================================
# Dependencies
# ==========================================

async def verify_api_key_header(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> bool:
    """
    Verify API key from header
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "API key required",
                "code": "missing_api_key"
            }
        )
    
    if not verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Invalid API key",
                "code": "invalid_api_key"
            }
        )
    
    return True


async def check_brute_force(request: Request):
    """
    Check for brute force attacks
    """
    client_ip = get_client_ip(request)
    is_locked, remaining = brute_force.is_locked_out(client_ip)
    
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "success": False,
                "message": "Too many failed attempts. Please try again later.",
                "code": "locked_out",
                "details": {"retry_after": remaining}
            }
        )


# ==========================================
# OTP Endpoints
# ==========================================

@router.post(
    "/send-otp",
    response_model=SendOTPResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Send OTP Code",
    description="Send a one-time password to user's Telegram"
)
async def send_otp(
    request: Request,
    body: SendOTPRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_key_header)
):
    """
    Send OTP to user's Telegram
    
    - Requires either telegram_id or telegram_username
    - Rate limited to prevent abuse
    - OTP expires after configured time
    """
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")
    
    # Validate that at least one identifier is provided
    if not body.telegram_id and not body.telegram_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Either telegram_id or telegram_username is required",
                "code": "missing_identifier"
            }
        )
    
    # Get telegram_id from username if not provided
    telegram_id = body.telegram_id
    
    if not telegram_id and body.telegram_username:
        # Look up user by username
        username = validate_telegram_username(body.telegram_username)
        if not username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "Invalid Telegram username format",
                    "code": "invalid_username"
                }
            )
        
        user = db.query(User).filter(User.telegram_username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "message": "User not found. User must start the bot first.",
                    "code": "user_not_found"
                }
            )
        telegram_id = user.telegram_id
    
    # Validate telegram_id
    telegram_id = validate_telegram_id(telegram_id)
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Invalid Telegram ID",
                "code": "invalid_telegram_id"
            }
        )
    
    # Create OTP (identity from DB only - body.name NOT trusted)
    otp_service = get_otp_service(db)
    otp_code, otp_request, status_msg = await otp_service.create_otp_request(
        telegram_id=telegram_id,
        request_source=body.source,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    # Handle different statuses
    if status_msg == "user_blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "User is blocked",
                "code": "user_blocked"
            }
        )
    
    if status_msg.startswith("cooldown:"):
        wait_seconds = int(status_msg.split(":")[1])
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "success": False,
                "message": f"Please wait {wait_seconds} seconds before requesting a new code",
                "code": "cooldown",
                "details": {"retry_after": wait_seconds}
            }
        )
    
    if status_msg.startswith("rate_limit:"):
        wait_seconds = int(status_msg.split(":")[1])
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "success": False,
                "message": "Rate limit exceeded. Please try again later.",
                "code": "rate_limit",
                "details": {"retry_after": wait_seconds}
            }
        )
    
    if status_msg != "success" or not otp_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Failed to create OTP",
                "code": "otp_creation_failed"
            }
        )
    
    # Send OTP via Telegram bot
    user = await otp_service.get_user_by_telegram_id(telegram_id)
    lang = user.language.value if user and user.language else "uz"
    
    sent = await telegram_bot.send_otp_message(telegram_id, otp_code, lang)
    
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Failed to send OTP message. User may have blocked the bot.",
                "code": "message_send_failed"
            }
        )
    
    logger.info(f"OTP sent to {telegram_id} from {client_ip}")
    
    return SendOTPResponse(
        success=True,
        message="OTP yuborildi",
        code="otp_sent",
        data={
            "expires_in": settings.OTP_EXPIRY_MINUTES * 60,
            "max_attempts": settings.OTP_MAX_ATTEMPTS
        }
    )


@router.post(
    "/verify-otp",
    response_model=VerifyOTPResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse}
    },
    summary="Verify OTP Code",
    description="Verify OTP - website sends ONLY code. Identity from Telegram backend."
)
async def verify_otp(
    request: Request,
    body: VerifyOTPRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_key_header),
    __: None = Depends(check_brute_force)
):
    """
    Verify OTP code. Website sends ONLY OTP - no telegram_id/username.
    Backend resolves identity from OTP record. One Telegram = One account.
    """
    client_ip = get_client_ip(request)
    otp_code = validate_otp_code(body.otp)
    
    if not otp_code:
        brute_force.record_attempt(client_ip, success=False)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Invalid OTP format",
                "code": "invalid_otp_format"
            }
        )
    
    otp_service = get_otp_service(db)
    is_valid, status_msg, user, otp_request = await otp_service.verify_otp_by_code(otp_code)
    
    if is_valid and user:
        # Duplicate check: One Telegram = One account
        if user.website_registered_at:
            brute_force.record_attempt(client_ip, success=False)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "This Telegram account is already registered",
                    "code": "already_registered"
                }
            )
        
        await otp_service.mark_website_registered(user.telegram_id)
        brute_force.record_attempt(client_ip, success=True)
        logger.info(f"OTP verified for {user.telegram_id}, account created")
        
        return VerifyOTPResponse(
            success=True,
            message="OTP tasdiqlandi",
            code="verified",
            data={
                "telegram_id": user.telegram_id,
                "telegram_username": user.telegram_username or None,
                "first_name": user.first_name or None,
                "verified_at": datetime.utcnow().isoformat()
            }
        )
    
    # Handle verification failure (is_valid=False or user=None)
    brute_force.record_attempt(client_ip, success=False)
    
    if status_msg == "otp_not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "No active OTP found. Please request a new code.",
                "code": "otp_not_found"
            }
        )
    
    if status_msg == "otp_expired":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "OTP has expired. Please request a new code.",
                "code": "otp_expired"
            }
        )
    
    if status_msg == "max_attempts_exceeded":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "success": False,
                "message": "Maximum attempts exceeded. Please request a new code.",
                "code": "max_attempts"
            }
        )
    
    if status_msg.startswith("invalid_otp:"):
        remaining = int(status_msg.split(":")[1])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": f"Invalid OTP. {remaining} attempts remaining.",
                "code": "invalid_otp",
                "details": {"remaining_attempts": remaining}
            }
        )
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "success": False,
            "message": "Verification failed",
            "code": "verification_failed"
        }
    )


@router.post(
    "/resend-otp",
    response_model=SendOTPResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse}
    },
    summary="Resend OTP Code",
    description="Resend OTP code (invalidates previous code)"
)
async def resend_otp(
    request: Request,
    body: ResendOTPRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_key_header)
):
    """
    Resend OTP code
    
    - Invalidates any existing OTP
    - Subject to rate limiting
    """
    # Reuse send_otp logic
    send_request = SendOTPRequest(
        telegram_id=body.telegram_id,
        telegram_username=body.telegram_username,
        source=body.source
    )
    
    return await send_otp(request, send_request, db)


@router.get(
    "/otp-status/{telegram_id}",
    response_model=OTPStatusResponse,
    responses={
        404: {"model": ErrorResponse}
    },
    summary="Get OTP Status",
    description="Check current OTP status for a user"
)
async def get_otp_status(
    telegram_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_api_key_header)
):
    """
    Get current OTP status
    
    - Returns remaining attempts and expiry time
    - Returns 404 if no active OTP
    """
    otp_service = get_otp_service(db)
    status_data = await otp_service.get_otp_status(telegram_id)
    
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "No active OTP found",
                "code": "otp_not_found"
            }
        )
    
    return OTPStatusResponse(
        success=True,
        message="OTP holati",
        code="status",
        data=status_data
    )


# ==========================================
# Health & Info Endpoints
# ==========================================

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health Check",
    description="Check service health status"
)
async def health_check():
    """
    Health check endpoint
    
    - Checks database connectivity
    - Checks Redis connectivity
    - Checks bot status
    """
    services = {}
    overall_healthy = True
    
    # Check database
    try:
        from src.models import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        services["database"] = "connected"
    except Exception as e:
        services["database"] = f"error: {str(e)}"
        overall_healthy = False
    
    # Check Redis
    try:
        redis_ok = await redis_client.ping()
        services["redis"] = "connected" if redis_ok else "disconnected"
        if not redis_ok:
            overall_healthy = False
    except Exception as e:
        services["redis"] = f"error: {str(e)}"
        overall_healthy = False
    
    # Check bot
    services["telegram_bot"] = "running" if telegram_bot.is_running else "stopped"
    
    return HealthResponse(
        status="healthy" if overall_healthy else "unhealthy",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        services=services
    )

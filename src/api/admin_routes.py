"""
iqromax.uz OTP Bot - Admin API Routes
Administrative endpoints for monitoring and management
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.config import settings
from src.models import get_db, redis_client, User, OTPRequest, OTPStatus, AdminLog
from src.utils import verify_api_key
from src.api.schemas import StatisticsResponse, ErrorResponse


logger = logging.getLogger(__name__)

# Create admin router
admin_router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ==========================================
# Admin Authentication
# ==========================================

async def verify_admin_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_admin_id: Optional[str] = Header(None, alias="X-Admin-ID")
) -> int:
    """
    Verify admin API key and admin ID
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "API key required", "code": "missing_api_key"}
        )
    
    if not verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Invalid API key", "code": "invalid_api_key"}
        )
    
    if not x_admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Admin ID required", "code": "missing_admin_id"}
        )
    
    try:
        admin_id = int(x_admin_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "Invalid Admin ID", "code": "invalid_admin_id"}
        )
    
    if admin_id not in settings.admin_telegram_ids_list:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "Not authorized as admin", "code": "not_admin"}
        )
    
    return admin_id


# ==========================================
# Statistics Endpoints
# ==========================================

@admin_router.get(
    "/statistics",
    response_model=StatisticsResponse,
    summary="Get System Statistics",
    description="Get comprehensive system statistics"
)
async def get_statistics(
    db: Session = Depends(get_db),
    admin_id: int = Depends(verify_admin_api_key)
):
    """
    Get system statistics
    
    Returns:
    - User statistics
    - OTP statistics
    - Daily/weekly/monthly trends
    """
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # User statistics
    total_users = db.query(func.count(User.id)).scalar()
    active_users_today = db.query(func.count(User.id)).filter(
        User.last_activity >= today_start
    ).scalar()
    active_users_week = db.query(func.count(User.id)).filter(
        User.last_activity >= week_start
    ).scalar()
    new_users_today = db.query(func.count(User.id)).filter(
        User.created_at >= today_start
    ).scalar()
    new_users_week = db.query(func.count(User.id)).filter(
        User.created_at >= week_start
    ).scalar()
    blocked_users = db.query(func.count(User.id)).filter(
        User.is_blocked == True
    ).scalar()
    
    # OTP statistics - today
    otp_sent_today = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= today_start
    ).scalar()
    otp_verified_today = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= today_start,
        OTPRequest.status == OTPStatus.VERIFIED
    ).scalar()
    otp_expired_today = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= today_start,
        OTPRequest.status == OTPStatus.EXPIRED
    ).scalar()
    otp_failed_today = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= today_start,
        OTPRequest.status == OTPStatus.FAILED
    ).scalar()
    
    # OTP statistics - week
    otp_sent_week = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= week_start
    ).scalar()
    otp_verified_week = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= week_start,
        OTPRequest.status == OTPStatus.VERIFIED
    ).scalar()
    
    # OTP statistics - total
    total_otp_sent = db.query(func.count(OTPRequest.id)).scalar()
    total_otp_verified = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.status == OTPStatus.VERIFIED
    ).scalar()
    
    # Calculate success rates
    success_rate_today = (otp_verified_today / otp_sent_today * 100) if otp_sent_today > 0 else 0
    success_rate_week = (otp_verified_week / otp_sent_week * 100) if otp_sent_week > 0 else 0
    success_rate_total = (total_otp_verified / total_otp_sent * 100) if total_otp_sent > 0 else 0
    
    # Average verification time (for verified OTPs today)
    avg_verification_time = db.query(
        func.avg(
            func.extract('epoch', OTPRequest.verified_at) - 
            func.extract('epoch', OTPRequest.created_at)
        )
    ).filter(
        OTPRequest.created_at >= today_start,
        OTPRequest.status == OTPStatus.VERIFIED
    ).scalar()
    
    return StatisticsResponse(
        success=True,
        data={
            "users": {
                "total": total_users,
                "active_today": active_users_today,
                "active_week": active_users_week,
                "new_today": new_users_today,
                "new_week": new_users_week,
                "blocked": blocked_users
            },
            "otp": {
                "today": {
                    "sent": otp_sent_today,
                    "verified": otp_verified_today,
                    "expired": otp_expired_today,
                    "failed": otp_failed_today,
                    "success_rate": round(success_rate_today, 2)
                },
                "week": {
                    "sent": otp_sent_week,
                    "verified": otp_verified_week,
                    "success_rate": round(success_rate_week, 2)
                },
                "total": {
                    "sent": total_otp_sent,
                    "verified": total_otp_verified,
                    "success_rate": round(success_rate_total, 2)
                },
                "avg_verification_time_seconds": round(avg_verification_time or 0, 2)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@admin_router.get(
    "/statistics/daily",
    summary="Get Daily Statistics",
    description="Get statistics for the past N days"
)
async def get_daily_statistics(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    admin_id: int = Depends(verify_admin_api_key)
):
    """
    Get daily statistics for the past N days
    """
    daily_stats = []
    
    for i in range(days):
        date = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        
        sent = db.query(func.count(OTPRequest.id)).filter(
            OTPRequest.created_at >= day_start,
            OTPRequest.created_at < day_end
        ).scalar()
        
        verified = db.query(func.count(OTPRequest.id)).filter(
            OTPRequest.created_at >= day_start,
            OTPRequest.created_at < day_end,
            OTPRequest.status == OTPStatus.VERIFIED
        ).scalar()
        
        new_users = db.query(func.count(User.id)).filter(
            User.created_at >= day_start,
            User.created_at < day_end
        ).scalar()
        
        daily_stats.append({
            "date": date.isoformat(),
            "otp_sent": sent,
            "otp_verified": verified,
            "success_rate": round((verified / sent * 100) if sent > 0 else 0, 2),
            "new_users": new_users
        })
    
    return {
        "success": True,
        "data": daily_stats
    }


# ==========================================
# User Management Endpoints
# ==========================================

@admin_router.get(
    "/users",
    summary="List Users",
    description="Get paginated list of users"
)
async def list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, enum=["active", "blocked", "all"]),
    db: Session = Depends(get_db),
    admin_id: int = Depends(verify_admin_api_key)
):
    """
    Get paginated list of users with optional filters
    """
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            (User.telegram_username.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.telegram_id.cast(str).ilike(f"%{search}%"))
        )
    
    if status_filter == "active":
        query = query.filter(User.is_blocked == False)
    elif status_filter == "blocked":
        query = query.filter(User.is_blocked == True)
    
    # Get total count
    total = query.count()
    total_pages = (total + per_page - 1) // per_page
    
    # Get paginated results
    offset = (page - 1) * per_page
    users = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Format response
    users_data = []
    for user in users:
        # Get OTP count for user
        otp_count = db.query(func.count(OTPRequest.id)).filter(
            OTPRequest.user_id == user.id
        ).scalar()
        
        users_data.append({
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.telegram_username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone_number,
            "language": user.language.value if user.language else "uz",
            "is_active": user.is_active,
            "is_blocked": user.is_blocked,
            "otp_requests": otp_count,
            "created_at": user.created_at.isoformat(),
            "last_activity": user.last_activity.isoformat() if user.last_activity else None
        })
    
    return {
        "success": True,
        "data": {
            "users": users_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages
            }
        }
    }


@admin_router.get(
    "/users/{telegram_id}",
    summary="Get User Details",
    description="Get detailed information about a user"
)
async def get_user_details(
    telegram_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(verify_admin_api_key)
):
    """
    Get detailed user information
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "User not found", "code": "user_not_found"}
        )
    
    # Get OTP history
    otp_requests = db.query(OTPRequest).filter(
        OTPRequest.user_id == user.id
    ).order_by(OTPRequest.created_at.desc()).limit(10).all()
    
    otp_history = []
    for otp in otp_requests:
        otp_history.append({
            "id": otp.id,
            "status": otp.status.value,
            "attempts": otp.attempts,
            "source": otp.request_source,
            "created_at": otp.created_at.isoformat(),
            "verified_at": otp.verified_at.isoformat() if otp.verified_at else None
        })
    
    return {
        "success": True,
        "data": {
            "user": {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.telegram_username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone_number,
                "language": user.language.value if user.language else "uz",
                "is_active": user.is_active,
                "is_blocked": user.is_blocked,
                "created_at": user.created_at.isoformat(),
                "last_activity": user.last_activity.isoformat() if user.last_activity else None
            },
            "otp_history": otp_history
        }
    }


@admin_router.post(
    "/users/{telegram_id}/block",
    summary="Block User",
    description="Block a user from using the service"
)
async def block_user(
    telegram_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(verify_admin_api_key)
):
    """
    Block a user
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "User not found", "code": "user_not_found"}
        )
    
    user.is_blocked = True
    
    # Log action
    log = AdminLog(
        admin_telegram_id=admin_id,
        action="block_user",
        details=f"Blocked user: {telegram_id}"
    )
    db.add(log)
    db.commit()
    
    logger.info(f"Admin {admin_id} blocked user {telegram_id}")
    
    return {
        "success": True,
        "message": "User blocked successfully",
        "code": "user_blocked"
    }


@admin_router.post(
    "/users/{telegram_id}/unblock",
    summary="Unblock User",
    description="Unblock a previously blocked user"
)
async def unblock_user(
    telegram_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(verify_admin_api_key)
):
    """
    Unblock a user
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "User not found", "code": "user_not_found"}
        )
    
    user.is_blocked = False
    
    # Log action
    log = AdminLog(
        admin_telegram_id=admin_id,
        action="unblock_user",
        details=f"Unblocked user: {telegram_id}"
    )
    db.add(log)
    db.commit()
    
    logger.info(f"Admin {admin_id} unblocked user {telegram_id}")
    
    return {
        "success": True,
        "message": "User unblocked successfully",
        "code": "user_unblocked"
    }


# ==========================================
# Logs Endpoint
# ==========================================

@admin_router.get(
    "/logs",
    summary="Get Admin Logs",
    description="Get admin action logs"
)
async def get_admin_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin_id: int = Depends(verify_admin_api_key)
):
    """
    Get admin action logs
    """
    query = db.query(AdminLog)
    
    total = query.count()
    total_pages = (total + per_page - 1) // per_page
    
    offset = (page - 1) * per_page
    logs = query.order_by(AdminLog.created_at.desc()).offset(offset).limit(per_page).all()
    
    logs_data = []
    for log in logs:
        logs_data.append({
            "id": log.id,
            "admin_id": log.admin_telegram_id,
            "action": log.action,
            "details": log.details,
            "created_at": log.created_at.isoformat()
        })
    
    return {
        "success": True,
        "data": {
            "logs": logs_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages
            }
        }
    }

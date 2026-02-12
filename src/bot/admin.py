"""
iqromax.uz OTP Bot - Admin Functions
Administrative functions for bot management
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models import User, OTPRequest, OTPStatus, OTPStatistics, AdminLog, redis_client
from src.bot.locales import get_text
from src.utils import get_user_language


logger = logging.getLogger(__name__)


async def get_statistics_text(db: Session, lang: str = "uz") -> str:
    """
    Generate statistics text for admin panel
    
    Args:
        db: Database session
        lang: Language code
    
    Returns:
        str: Formatted statistics text
    """
    # Get today's date
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    # Total users
    total_users = db.query(func.count(User.id)).scalar()
    
    # Active users (last 24 hours)
    active_users = db.query(func.count(User.id)).filter(
        User.last_activity >= today_start
    ).scalar()
    
    # New users today
    new_users_today = db.query(func.count(User.id)).filter(
        User.created_at >= today_start
    ).scalar()
    
    # OTP statistics
    total_otp_sent = db.query(func.count(OTPRequest.id)).scalar()
    
    otp_today = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= today_start
    ).scalar()
    
    verified_today = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= today_start,
        OTPRequest.status == OTPStatus.VERIFIED
    ).scalar()
    
    expired_today = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= today_start,
        OTPRequest.status == OTPStatus.EXPIRED
    ).scalar()
    
    failed_today = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.created_at >= today_start,
        OTPRequest.status == OTPStatus.FAILED
    ).scalar()
    
    # Calculate success rate
    if otp_today > 0:
        success_rate = (verified_today / otp_today) * 100
    else:
        success_rate = 0
    
    # Get Redis stats
    try:
        redis_total_sent = await redis_client.get_stat("total:sent")
        redis_total_verified = await redis_client.get_stat("total:verified")
    except Exception:
        redis_total_sent = 0
        redis_total_verified = 0
    
    # Format text
    text = f"""
<b>📊 {get_text("statistics_title", lang)}</b>

<b>👥 {get_text("users", lang)}:</b>
├ {get_text("total", lang)}: <code>{total_users}</code>
├ {get_text("active_today", lang)}: <code>{active_users}</code>
└ {get_text("new_today", lang)}: <code>{new_users_today}</code>

<b>📨 {get_text("otp_stats", lang)}:</b>
├ {get_text("total_sent", lang)}: <code>{total_otp_sent}</code>
├ {get_text("sent_today", lang)}: <code>{otp_today}</code>
├ {get_text("verified_today", lang)}: <code>{verified_today}</code>
├ {get_text("expired_today", lang)}: <code>{expired_today}</code>
├ {get_text("failed_today", lang)}: <code>{failed_today}</code>
└ {get_text("success_rate", lang)}: <code>{success_rate:.1f}%</code>

<b>⏰ {get_text("updated_at", lang)}:</b>
<code>{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</code>
"""
    
    return text.strip()


async def get_users_text(db: Session, lang: str = "uz", page: int = 1, per_page: int = 10) -> str:
    """
    Generate users list text for admin panel
    
    Args:
        db: Database session
        lang: Language code
        page: Page number
        per_page: Users per page
    
    Returns:
        str: Formatted users text
    """
    # Get total count
    total_users = db.query(func.count(User.id)).scalar()
    total_pages = (total_users + per_page - 1) // per_page
    
    # Get users for current page
    offset = (page - 1) * per_page
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Format text
    text = f"<b>👥 {get_text('users_list', lang)}</b>\n"
    text += f"<i>{get_text('page', lang)}: {page}/{total_pages}</i>\n\n"
    
    for i, user in enumerate(users, start=offset + 1):
        username = f"@{user.telegram_username}" if user.telegram_username else "—"
        name = user.first_name or "—"
        status = "🟢" if user.is_active and not user.is_blocked else "🔴"
        
        text += f"{i}. {status} <code>{user.telegram_id}</code>\n"
        text += f"   {get_text('username', lang)}: {username}\n"
        text += f"   {get_text('name', lang)}: {name}\n"
        text += f"   {get_text('registered', lang)}: {user.created_at.strftime('%Y-%m-%d')}\n\n"
    
    if not users:
        text += f"<i>{get_text('no_users', lang)}</i>"
    
    return text.strip()


async def log_admin_action(
    db: Session,
    admin_telegram_id: int,
    action: str,
    details: Optional[str] = None
):
    """
    Log admin action for audit trail
    
    Args:
        db: Database session
        admin_telegram_id: Admin's Telegram ID
        action: Action performed
        details: Additional details
    """
    log = AdminLog(
        admin_telegram_id=admin_telegram_id,
        action=action,
        details=details
    )
    db.add(log)
    db.commit()
    
    logger.info(f"Admin action: {admin_telegram_id} - {action}")


async def block_user(db: Session, telegram_id: int, admin_id: int) -> bool:
    """
    Block a user from using the bot
    
    Args:
        db: Database session
        telegram_id: User's Telegram ID
        admin_id: Admin's Telegram ID
    
    Returns:
        bool: Success status
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        return False
    
    user.is_blocked = True
    db.commit()
    
    await log_admin_action(
        db, admin_id, "block_user",
        f"Blocked user: {telegram_id}"
    )
    
    return True


async def unblock_user(db: Session, telegram_id: int, admin_id: int) -> bool:
    """
    Unblock a user
    
    Args:
        db: Database session
        telegram_id: User's Telegram ID
        admin_id: Admin's Telegram ID
    
    Returns:
        bool: Success status
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        return False
    
    user.is_blocked = False
    db.commit()
    
    await log_admin_action(
        db, admin_id, "unblock_user",
        f"Unblocked user: {telegram_id}"
    )
    
    return True


async def get_user_details(db: Session, telegram_id: int, lang: str = "uz") -> Optional[str]:
    """
    Get detailed user information
    
    Args:
        db: Database session
        telegram_id: User's Telegram ID
        lang: Language code
    
    Returns:
        str: Formatted user details or None
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        return None
    
    # Get OTP statistics for user
    total_otps = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.user_id == user.id
    ).scalar()
    
    verified_otps = db.query(func.count(OTPRequest.id)).filter(
        OTPRequest.user_id == user.id,
        OTPRequest.status == OTPStatus.VERIFIED
    ).scalar()
    
    username = f"@{user.telegram_username}" if user.telegram_username else "—"
    status = "🟢 Active" if user.is_active and not user.is_blocked else "🔴 Blocked"
    
    text = f"""
<b>👤 {get_text('user_details', lang)}</b>

<b>ID:</b> <code>{user.telegram_id}</code>
<b>{get_text('username', lang)}:</b> {username}
<b>{get_text('name', lang)}:</b> {user.first_name or "—"} {user.last_name or ""}
<b>{get_text('phone', lang)}:</b> {user.phone_number or "—"}
<b>{get_text('language', lang)}:</b> {get_user_language(user)}
<b>{get_text('status', lang)}:</b> {status}

<b>📊 {get_text('otp_stats', lang)}:</b>
├ {get_text('total_requests', lang)}: <code>{total_otps}</code>
└ {get_text('verified', lang)}: <code>{verified_otps}</code>

<b>📅 {get_text('dates', lang)}:</b>
├ {get_text('registered', lang)}: {user.created_at.strftime('%Y-%m-%d %H:%M')}
└ {get_text('last_activity', lang)}: {user.last_activity.strftime('%Y-%m-%d %H:%M') if user.last_activity else "—"}
"""
    
    return text.strip()

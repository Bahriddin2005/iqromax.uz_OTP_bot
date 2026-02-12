"""
iqromax.uz OTP Bot - OTP Service
Core service for OTP generation, verification, and management
"""

import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union
from uuid import UUID
from sqlalchemy.orm import Session

from src.config import settings
from src.models import (
    User, OTPRequest, OTPStatus, OTPStatistics,
    redis_client, hash_otp, verify_otp_hash
)


logger = logging.getLogger(__name__)


class OTPService:
    """
    Service class for OTP operations
    Handles generation, sending, verification, and cleanup
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def generate_otp(length: int = None) -> str:
        """
        Generate a cryptographically secure random OTP
        
        Args:
            length: OTP length (default from settings)
        
        Returns:
            str: Generated OTP code
        """
        if length is None:
            length = settings.OTP_LENGTH
        
        # Generate random number with leading zeros preserved
        max_value = 10 ** length - 1
        otp = secrets.randbelow(max_value + 1)
        return str(otp).zfill(length)
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        telegram_username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> User:
        """
        Get existing user or create new one.
        For Supabase: creates auth.users via Admin API, trigger syncs to public.users.
        """
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            if telegram_username:
                user.telegram_username = telegram_username
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            if phone_number:
                user.phone_number = phone_number
            user.last_activity = datetime.now(timezone.utc)
            self.db.commit()
            return user

        # Supabase: create via auth Admin API, then update public.users
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
            from src.services.supabase_auth import create_telegram_user
            auth_user_id = await create_telegram_user(
                telegram_id=telegram_id,
                telegram_username=telegram_username,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
            )
            if auth_user_id:
                user = self.db.query(User).filter(User.id == auth_user_id).first()
                if user:
                    user.telegram_id = telegram_id
                    user.telegram_username = telegram_username
                    user.first_name = first_name
                    user.last_name = last_name
                    user.phone_number = phone_number
                    user.language = "uz"
                    user.last_activity = datetime.now(timezone.utc)
                    self.db.commit()
                    self.db.refresh(user)
                    logger.info(f"New Supabase user created: telegram_id={telegram_id}")
                    return user

        # SQLite / legacy: create directly
        user = User(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"New user created: {telegram_id}")
        return user
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID
        
        Args:
            telegram_id: User's Telegram ID
        
        Returns:
            User or None
        """
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by Telegram username
        
        Args:
            username: Telegram username (with or without @)
        
        Returns:
            User or None
        """
        # Remove @ if present
        username = username.lstrip("@")
        return self.db.query(User).filter(User.telegram_username == username).first()
    
    async def can_request_otp(self, telegram_id: int) -> Tuple[bool, str, int]:
        """
        Check if user can request a new OTP
        
        Args:
            telegram_id: User's Telegram ID
        
        Returns:
            Tuple: (can_request, reason, wait_seconds)
        """
        # Check if user is blocked or suspended
        user = await self.get_user_by_telegram_id(telegram_id)
        if user and (getattr(user, "is_blocked", False) or getattr(user, "is_suspended", False)):
            return False, "user_blocked", 0
        
        # Check cooldown (minimum time between requests)
        can_request, cooldown_remaining = await redis_client.check_cooldown(telegram_id)
        if not can_request:
            return False, "cooldown", cooldown_remaining
        
        # Check rate limit (max requests per hour)
        is_allowed, remaining = await redis_client.check_rate_limit(telegram_id)
        if not is_allowed:
            ttl = await redis_client.get_rate_limit_ttl(telegram_id)
            return False, "rate_limit", ttl
        
        return True, "allowed", 0
    
    async def create_otp_request(
        self,
        telegram_id: int,
        telegram_username: Optional[str] = None,
        first_name: Optional[str] = None,
        request_source: str = "web_registration",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[OTPRequest], str]:
        """
        Create a new OTP request
        
        Args:
            telegram_id: User's Telegram ID
            telegram_username: Telegram username
            first_name: User's first name
            request_source: Source of the request
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Tuple: (otp_code, otp_request, status_message)
        """
        # Check if can request
        can_request, reason, wait_seconds = await self.can_request_otp(telegram_id)
        if not can_request:
            if reason == "user_blocked":
                return None, None, "user_blocked"
            elif reason == "cooldown":
                return None, None, f"cooldown:{wait_seconds}"
            elif reason == "rate_limit":
                return None, None, f"rate_limit:{wait_seconds}"
        
        # Get or create user
        user = await self.get_or_create_user(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            first_name=first_name
        )
        
        # Invalidate any existing pending OTP
        await self._invalidate_pending_otps(user.id)
        
        # Generate new OTP
        otp_code = self.generate_otp()
        otp_hashed = hash_otp(otp_code)
        
        # Calculate expiry time
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        
        # Create OTP request in database
        otp_request = OTPRequest(
            user_id=user.id,
            otp_hash=otp_hashed,
            request_source=request_source,
            ip_address=ip_address,
            user_agent=user_agent,
            status=OTPStatus.PENDING,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            expires_at=expires_at
        )
        self.db.add(otp_request)
        self.db.commit()
        self.db.refresh(otp_request)
        
        # Store in Redis for fast verification
        expiry_seconds = settings.OTP_EXPIRY_MINUTES * 60
        await redis_client.store_otp(
            telegram_id=telegram_id,
            otp_hash=otp_hashed,
            request_id=otp_request.id,
            expiry_minutes=settings.OTP_EXPIRY_MINUTES
        )
        # Code->telegram_id lookup: website sends ONLY code, backend resolves identity
        await redis_client.store_otp_code_lookup(
            code=otp_code,
            telegram_id=telegram_id,
            request_id=otp_request.id,
            expiry_seconds=expiry_seconds
        )
        
        # Set cooldown
        await redis_client.set_cooldown(telegram_id)
        
        # Increment rate limit counter
        await redis_client.increment_rate_limit(telegram_id)
        
        # Update statistics
        await self._update_statistics("sent")
        
        logger.info(f"OTP created for user {telegram_id}, request_id: {otp_request.id}")
        
        return otp_code, otp_request, "success"
    
    async def verify_otp(
        self,
        telegram_id: int,
        otp_code: str
    ) -> Tuple[bool, str, Optional[OTPRequest]]:
        """
        Verify OTP code
        
        Args:
            telegram_id: User's Telegram ID
            otp_code: OTP code to verify
        
        Returns:
            Tuple: (is_valid, status_message, otp_request)
        """
        # Get OTP data from Redis
        otp_data = await redis_client.get_otp_data(telegram_id)
        
        if not otp_data:
            logger.warning(f"No OTP found for user {telegram_id}")
            return False, "otp_not_found", None
        
        # Get OTP request from database
        otp_request = self.db.query(OTPRequest).filter(
            OTPRequest.id == otp_data["request_id"]
        ).first()
        
        if not otp_request:
            logger.error(f"OTP request not found in DB: {otp_data['request_id']}")
            return False, "otp_not_found", None
        
        # Check if already verified
        if otp_request.status == OTPStatus.VERIFIED:
            return False, "already_verified", otp_request
        
        # Check if expired
        if otp_request.is_expired:
            otp_request.status = OTPStatus.EXPIRED
            self.db.commit()
            await redis_client.delete_otp(telegram_id)
            await self._update_statistics("expired")
            return False, "otp_expired", otp_request
        
        # Check attempts
        if not otp_request.has_attempts_left:
            otp_request.status = OTPStatus.FAILED
            self.db.commit()
            await redis_client.delete_otp(telegram_id)
            await self._update_statistics("failed")
            return False, "max_attempts_exceeded", otp_request
        
        # Increment attempt counter
        otp_request.attempts += 1
        await redis_client.increment_otp_attempts(telegram_id)
        
        # Verify OTP hash
        if not verify_otp_hash(otp_code, otp_data["hash"]):
            self.db.commit()
            remaining = otp_request.max_attempts - otp_request.attempts
            logger.warning(f"Invalid OTP for user {telegram_id}, {remaining} attempts left")
            
            if remaining <= 0:
                otp_request.status = OTPStatus.FAILED
                self.db.commit()
                await redis_client.delete_otp(telegram_id)
                await self._update_statistics("failed")
                return False, "max_attempts_exceeded", otp_request
            
            return False, f"invalid_otp:{remaining}", otp_request
        
        # OTP is valid
        otp_request.status = OTPStatus.VERIFIED
        otp_request.verified_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # Clean up Redis (code lookup is deleted in verify_otp_by_code)
        await redis_client.delete_otp(telegram_id)
        
        # Update statistics
        await self._update_statistics("verified")
        
        logger.info(f"OTP verified for user {telegram_id}")
        
        return True, "verified", otp_request
    
    async def verify_otp_by_code(
        self,
        otp_code: str
    ) -> Tuple[bool, str, Optional[User], Optional[OTPRequest]]:
        """
        Verify OTP by code only (website sends ONLY code - no telegram_id/username).
        Identity is resolved from OTP record.
        
        Returns:
            Tuple: (is_valid, status_message, user, otp_request)
        """
        # Look up telegram_id from code (NOT from frontend)
        lookup = await redis_client.get_otp_code_lookup(otp_code)
        if not lookup:
            logger.warning("OTP code lookup failed - wrong/expired code")
            return False, "otp_not_found", None, None
        
        telegram_id = lookup["telegram_id"]
        
        # Verify OTP
        is_valid, status_msg, otp_request = await self.verify_otp(telegram_id, otp_code)
        
        if not is_valid:
            return False, status_msg, None, otp_request
        
        # Delete code lookup (OTP used, prevent replay)
        await redis_client.delete_otp_code_lookup(otp_code)
        
        # Get user from DB (trusted source)
        user = await self.get_user_by_telegram_id(telegram_id)
        return True, "verified", user, otp_request
    
    async def is_website_registered(self, telegram_id: int) -> bool:
        """Check if Telegram user has already completed website registration"""
        user = await self.get_user_by_telegram_id(telegram_id)
        return user is not None and user.website_registered_at is not None
    
    async def mark_website_registered(self, telegram_id: int) -> Optional[User]:
        """Mark user as having completed website registration"""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            user.website_registered_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(user)
        return user
    
    async def _invalidate_pending_otps(self, user_id: Union[int, UUID]):
        """
        Invalidate all pending OTPs for a user
        
        Args:
            user_id: User's database ID
        """
        pending_otps = self.db.query(OTPRequest).filter(
            OTPRequest.user_id == user_id,
            OTPRequest.status == OTPStatus.PENDING
        ).all()
        
        for otp in pending_otps:
            otp.status = OTPStatus.EXPIRED
        
        if pending_otps:
            self.db.commit()
            logger.info(f"Invalidated {len(pending_otps)} pending OTPs for user {user_id}")
    
    async def _update_statistics(self, stat_type: str):
        """
        Update OTP statistics
        
        Args:
            stat_type: Type of statistic (sent, verified, expired, failed)
        """
        today = datetime.now(timezone.utc).date()
        today_key = f"daily:{today.isoformat()}:{stat_type}"
        
        await redis_client.increment_stat(today_key)
        await redis_client.increment_stat(f"total:{stat_type}")
    
    async def get_otp_status(self, telegram_id: int) -> Optional[dict]:
        """
        Get current OTP status for a user
        
        Args:
            telegram_id: User's Telegram ID
        
        Returns:
            dict: OTP status info or None
        """
        otp_data = await redis_client.get_otp_data(telegram_id)
        
        if not otp_data:
            return None
        
        otp_request = self.db.query(OTPRequest).filter(
            OTPRequest.id == otp_data["request_id"]
        ).first()
        
        if not otp_request:
            return None
        
        ttl = await redis_client.client.ttl(f"otp:{telegram_id}")
        
        return {
            "request_id": str(otp_request.id),
            "status": otp_request.status.value,
            "attempts": otp_request.attempts,
            "max_attempts": otp_request.max_attempts,
            "remaining_attempts": otp_request.max_attempts - otp_request.attempts,
            "expires_in_seconds": max(ttl, 0),
            "created_at": otp_request.created_at.isoformat() if otp_request.created_at else None
        }
    
    async def resend_otp(
        self,
        telegram_id: int,
        request_source: str = "web_registration",
        ip_address: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[OTPRequest], str]:
        """
        Resend OTP (creates new OTP, invalidates old one)
        
        Args:
            telegram_id: User's Telegram ID
            request_source: Source of the request
            ip_address: Client IP address
        
        Returns:
            Tuple: (otp_code, otp_request, status_message)
        """
        return await self.create_otp_request(
            telegram_id=telegram_id,
            request_source=request_source,
            ip_address=ip_address
        )
    
    def cleanup_expired_otps(self) -> int:
        """
        Clean up expired OTP requests from database
        (Should be run periodically via cron/scheduler)
        
        Returns:
            int: Number of cleaned up records
        """
        expired = self.db.query(OTPRequest).filter(
            OTPRequest.status == OTPStatus.PENDING,
            OTPRequest.expires_at < datetime.now(timezone.utc)
        ).all()
        
        count = 0
        for otp in expired:
            otp.status = OTPStatus.EXPIRED
            count += 1
        
        if count > 0:
            self.db.commit()
            logger.info(f"Cleaned up {count} expired OTP requests")
        
        return count


# Factory function
def get_otp_service(db: Session) -> OTPService:
    """
    Get OTP service instance
    
    Args:
        db: Database session
    
    Returns:
        OTPService: Service instance
    """
    return OTPService(db)

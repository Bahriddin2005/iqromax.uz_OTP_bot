"""
iqromax.uz OTP Bot - Security Utilities
Security functions for authentication, validation, and protection
"""

import re
import hmac
import hashlib
import secrets
import logging
from typing import Optional
from datetime import datetime, timedelta
from functools import wraps

from src.config import settings


logger = logging.getLogger(__name__)


# ==========================================
# API Key Authentication
# ==========================================

def generate_api_key() -> str:
    """
    Generate a secure random API key
    
    Returns:
        str: 64-character hex API key
    """
    return secrets.token_hex(32)


def verify_api_key(provided_key: str) -> bool:
    """
    Verify API key against configured secret
    
    Args:
        provided_key: API key provided in request
    
    Returns:
        bool: True if valid
    """
    if not provided_key:
        return False
    
    return hmac.compare_digest(
        provided_key,
        settings.API_SECRET_KEY
    )


def generate_webhook_secret() -> str:
    """
    Generate webhook secret for Telegram
    
    Returns:
        str: Webhook secret token
    """
    return secrets.token_urlsafe(32)


def verify_telegram_webhook(secret_token: str) -> bool:
    """
    Verify Telegram webhook secret token
    
    Args:
        secret_token: Token from X-Telegram-Bot-Api-Secret-Token header
    
    Returns:
        bool: True if valid
    """
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        return True  # Skip verification if not configured
    
    return hmac.compare_digest(
        secret_token or "",
        settings.TELEGRAM_WEBHOOK_SECRET
    )


# ==========================================
# Input Validation
# ==========================================

def validate_telegram_id(telegram_id: any) -> Optional[int]:
    """
    Validate and sanitize Telegram ID
    
    Args:
        telegram_id: Telegram ID to validate
    
    Returns:
        int: Valid Telegram ID or None
    """
    try:
        tid = int(telegram_id)
        # Telegram IDs are positive integers
        if tid > 0:
            return tid
    except (ValueError, TypeError):
        pass
    return None


def validate_telegram_username(username: str) -> Optional[str]:
    """
    Validate and sanitize Telegram username
    
    Args:
        username: Username to validate
    
    Returns:
        str: Valid username or None
    """
    if not username:
        return None
    
    # Remove @ prefix if present
    username = username.lstrip("@")
    
    # Telegram username rules:
    # - 5-32 characters
    # - Only alphanumeric and underscores
    # - Cannot start with a number
    pattern = r"^[a-zA-Z][a-zA-Z0-9_]{4,31}$"
    
    if re.match(pattern, username):
        return username.lower()
    
    return None


def validate_otp_code(otp: str) -> Optional[str]:
    """
    Validate OTP code format
    
    Args:
        otp: OTP code to validate
    
    Returns:
        str: Valid OTP or None
    """
    if not otp:
        return None
    
    # Remove any whitespace
    otp = otp.strip()
    
    # Check if it's numeric and correct length
    if otp.isdigit() and len(otp) == settings.OTP_LENGTH:
        return otp
    
    return None


def validate_phone_number(phone: str) -> Optional[str]:
    """
    Validate and normalize phone number
    
    Args:
        phone: Phone number to validate
    
    Returns:
        str: Normalized phone number or None
    """
    if not phone:
        return None
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r"[^\d+]", "", phone)
    
    # Basic validation: should start with + and have 10-15 digits
    if re.match(r"^\+?\d{10,15}$", cleaned):
        return cleaned
    
    return None


def sanitize_string(text: str, max_length: int = 255) -> str:
    """
    Sanitize string input to prevent injection attacks
    
    Args:
        text: String to sanitize
        max_length: Maximum allowed length
    
    Returns:
        str: Sanitized string
    """
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Trim to max length
    text = text[:max_length]
    
    # Basic XSS prevention
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    
    return text.strip()


# ==========================================
# IP Address Handling
# ==========================================

def get_client_ip(request) -> str:
    """
    Extract real client IP from request headers
    
    Args:
        request: FastAPI/Starlette request object
    
    Returns:
        str: Client IP address
    """
    # Check X-Forwarded-For header (for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


def is_private_ip(ip: str) -> bool:
    """
    Check if IP address is private/internal
    
    Args:
        ip: IP address to check
    
    Returns:
        bool: True if private
    """
    import ipaddress
    
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private
    except ValueError:
        return False


# ==========================================
# Admin Authorization
# ==========================================

def is_admin(telegram_id: int) -> bool:
    """
    Check if Telegram user is an admin
    
    Args:
        telegram_id: User's Telegram ID
    
    Returns:
        bool: True if admin
    """
    return telegram_id in settings.admin_telegram_ids_list


def require_admin(func):
    """
    Decorator to require admin privileges
    
    Usage:
        @require_admin
        async def admin_command(message):
            ...
    """
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            logger.warning(f"Unauthorized admin access attempt: {message.from_user.id}")
            return None
        return await func(message, *args, **kwargs)
    return wrapper


# ==========================================
# Brute Force Protection
# ==========================================

class BruteForceProtection:
    """
    Simple in-memory brute force protection
    For production, use Redis-based implementation
    """
    
    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 15):
        self.max_attempts = max_attempts
        self.lockout_minutes = lockout_minutes
        self._attempts: dict = {}
        self._lockouts: dict = {}
    
    def record_attempt(self, identifier: str, success: bool = False):
        """
        Record an authentication attempt
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            success: Whether attempt was successful
        """
        if success:
            # Clear on success
            self._attempts.pop(identifier, None)
            self._lockouts.pop(identifier, None)
            return
        
        # Record failed attempt
        now = datetime.utcnow()
        
        if identifier not in self._attempts:
            self._attempts[identifier] = []
        
        self._attempts[identifier].append(now)
        
        # Clean old attempts (older than lockout period)
        cutoff = now - timedelta(minutes=self.lockout_minutes)
        self._attempts[identifier] = [
            t for t in self._attempts[identifier] if t > cutoff
        ]
        
        # Check if should lockout
        if len(self._attempts[identifier]) >= self.max_attempts:
            self._lockouts[identifier] = now + timedelta(minutes=self.lockout_minutes)
            logger.warning(f"Brute force lockout triggered for: {identifier}")
    
    def is_locked_out(self, identifier: str) -> tuple[bool, int]:
        """
        Check if identifier is locked out
        
        Args:
            identifier: Unique identifier
        
        Returns:
            tuple: (is_locked, seconds_remaining)
        """
        if identifier not in self._lockouts:
            return False, 0
        
        lockout_until = self._lockouts[identifier]
        now = datetime.utcnow()
        
        if now >= lockout_until:
            # Lockout expired
            del self._lockouts[identifier]
            self._attempts.pop(identifier, None)
            return False, 0
        
        remaining = int((lockout_until - now).total_seconds())
        return True, remaining


# Global brute force protection instance
brute_force = BruteForceProtection()


# ==========================================
# Request Signature Verification
# ==========================================

def generate_request_signature(data: dict, secret: str) -> str:
    """
    Generate HMAC signature for request data
    
    Args:
        data: Request data dictionary
        secret: Secret key for signing
    
    Returns:
        str: HMAC signature
    """
    import json
    
    # Sort keys for consistent ordering
    sorted_data = json.dumps(data, sort_keys=True)
    
    signature = hmac.new(
        secret.encode(),
        sorted_data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def verify_request_signature(data: dict, signature: str, secret: str) -> bool:
    """
    Verify HMAC signature of request data
    
    Args:
        data: Request data dictionary
        signature: Provided signature
        secret: Secret key
    
    Returns:
        bool: True if valid
    """
    expected = generate_request_signature(data, secret)
    return hmac.compare_digest(signature, expected)

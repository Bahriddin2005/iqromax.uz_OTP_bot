"""
iqromax.uz OTP Bot - Redis Client
Redis for OTP caching, rate limiting, and session management
"""

import json
import hashlib
from datetime import timedelta
from typing import Optional, Any
import redis.asyncio as redis
from redis.asyncio import Redis

from src.config import settings


class RedisClient:
    """
    Async Redis client wrapper for OTP operations
    """
    
    # Key prefixes for organization
    PREFIX_OTP = "otp:"
    PREFIX_RATE_LIMIT = "rate:"
    PREFIX_SESSION = "session:"
    PREFIX_USER = "user:"
    PREFIX_STATS = "stats:"
    
    def __init__(self):
        self._client: Optional[Redis] = None
    
    async def connect(self) -> Redis:
        """
        Establish Redis connection
        """
        if self._client is None:
            self._client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True
            )
        return self._client
    
    async def disconnect(self):
        """
        Close Redis connection
        """
        if self._client:
            await self._client.close()
            self._client = None
    
    @property
    def client(self) -> Redis:
        """
        Get Redis client instance
        """
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client
    
    # ==========================================
    # OTP Operations
    # ==========================================
    
    def _get_otp_key(self, telegram_id: int) -> str:
        """Generate OTP cache key"""
        return f"{self.PREFIX_OTP}{telegram_id}"
    
    def _get_otp_code_key(self, code: str) -> str:
        """Generate OTP code lookup key (for verify by code only)"""
        return f"{self.PREFIX_OTP}code:{code}"
    
    async def store_otp(
        self, 
        telegram_id: int, 
        otp_hash: str,
        request_id: int,
        expiry_minutes: int = None
    ) -> bool:
        """
        Store OTP hash in Redis with expiration
        
        Args:
            telegram_id: User's Telegram ID
            otp_hash: Hashed OTP code
            request_id: Database request ID for reference
            expiry_minutes: Expiration time in minutes
        
        Returns:
            bool: Success status
        """
        if expiry_minutes is None:
            expiry_minutes = settings.OTP_EXPIRY_MINUTES
        
        key = self._get_otp_key(telegram_id)
        data = {
            "hash": otp_hash,
            "request_id": request_id,
            "attempts": 0,
            "max_attempts": settings.OTP_MAX_ATTEMPTS
        }
        
        await self.client.setex(
            key,
            timedelta(minutes=expiry_minutes),
            json.dumps(data)
        )
        return True
    
    async def store_otp_code_lookup(
        self,
        code: str,
        telegram_id: int,
        request_id: int,
        expiry_seconds: int
    ) -> bool:
        """
        Store OTP code -> telegram_id lookup (website sends ONLY code, backend looks up identity)
        """
        key = self._get_otp_code_key(code)
        data = {"telegram_id": telegram_id, "request_id": request_id}
        await self.client.setex(key, expiry_seconds, json.dumps(data))
        return True
    
    async def get_otp_code_lookup(self, code: str) -> Optional[dict]:
        """
        Get telegram_id from OTP code (for verify-otp with code only)
        """
        key = self._get_otp_code_key(code)
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def delete_otp_code_lookup(self, code: str) -> bool:
        """Remove OTP code lookup after verification"""
        key = self._get_otp_code_key(code)
        result = await self.client.delete(key)
        return result > 0
    
    async def get_otp_data(self, telegram_id: int) -> Optional[dict]:
        """
        Retrieve OTP data from Redis
        
        Args:
            telegram_id: User's Telegram ID
        
        Returns:
            dict: OTP data or None if not found/expired
        """
        key = self._get_otp_key(telegram_id)
        data = await self.client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def increment_otp_attempts(self, telegram_id: int) -> int:
        """
        Increment OTP verification attempts
        
        Args:
            telegram_id: User's Telegram ID
        
        Returns:
            int: Current attempt count
        """
        key = self._get_otp_key(telegram_id)
        data = await self.get_otp_data(telegram_id)
        
        if data:
            data["attempts"] += 1
            ttl = await self.client.ttl(key)
            if ttl > 0:
                await self.client.setex(key, ttl, json.dumps(data))
            return data["attempts"]
        return 0
    
    async def delete_otp(self, telegram_id: int) -> bool:
        """
        Delete OTP from Redis (after successful verification)
        
        Args:
            telegram_id: User's Telegram ID
        
        Returns:
            bool: Success status
        """
        key = self._get_otp_key(telegram_id)
        result = await self.client.delete(key)
        return result > 0
    
    # ==========================================
    # Rate Limiting
    # ==========================================
    
    def _get_rate_limit_key(self, telegram_id: int, action: str = "otp") -> str:
        """Generate rate limit key"""
        return f"{self.PREFIX_RATE_LIMIT}{action}:{telegram_id}"
    
    async def check_rate_limit(
        self, 
        telegram_id: int, 
        action: str = "otp",
        window_minutes: int = None,
        max_requests: int = None
    ) -> tuple[bool, int]:
        """
        Check if user is rate limited
        
        Args:
            telegram_id: User's Telegram ID
            action: Action type for rate limiting
            window_minutes: Time window in minutes
            max_requests: Maximum requests allowed in window
        
        Returns:
            tuple: (is_allowed, remaining_requests)
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, 999
        
        if window_minutes is None:
            window_minutes = 60  # 1 hour window
        if max_requests is None:
            max_requests = settings.OTP_MAX_REQUESTS_PER_HOUR
        
        key = self._get_rate_limit_key(telegram_id, action)
        
        # Get current count
        current = await self.client.get(key)
        current_count = int(current) if current else 0
        
        if current_count >= max_requests:
            return False, 0
        
        return True, max_requests - current_count
    
    async def increment_rate_limit(
        self, 
        telegram_id: int, 
        action: str = "otp",
        window_minutes: int = 60
    ) -> int:
        """
        Increment rate limit counter
        
        Args:
            telegram_id: User's Telegram ID
            action: Action type
            window_minutes: Time window in minutes
        
        Returns:
            int: Current count after increment
        """
        key = self._get_rate_limit_key(telegram_id, action)
        
        # Increment and set expiry if new key
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, timedelta(minutes=window_minutes))
        results = await pipe.execute()
        
        return results[0]
    
    async def get_rate_limit_ttl(self, telegram_id: int, action: str = "otp") -> int:
        """
        Get remaining time until rate limit resets
        
        Args:
            telegram_id: User's Telegram ID
            action: Action type
        
        Returns:
            int: Seconds until reset, -1 if no limit
        """
        key = self._get_rate_limit_key(telegram_id, action)
        ttl = await self.client.ttl(key)
        return max(ttl, 0)
    
    # ==========================================
    # Cooldown (minimum time between requests)
    # ==========================================
    
    def _get_cooldown_key(self, telegram_id: int) -> str:
        """Generate cooldown key"""
        return f"{self.PREFIX_RATE_LIMIT}cooldown:{telegram_id}"
    
    async def check_cooldown(self, telegram_id: int) -> tuple[bool, int]:
        """
        Check if user is in cooldown period
        
        Args:
            telegram_id: User's Telegram ID
        
        Returns:
            tuple: (can_request, seconds_remaining)
        """
        key = self._get_cooldown_key(telegram_id)
        ttl = await self.client.ttl(key)
        
        if ttl > 0:
            return False, ttl
        return True, 0
    
    async def set_cooldown(self, telegram_id: int, minutes: int = None) -> bool:
        """
        Set cooldown period for user
        
        Args:
            telegram_id: User's Telegram ID
            minutes: Cooldown duration in minutes
        
        Returns:
            bool: Success status
        """
        if minutes is None:
            minutes = settings.OTP_RATE_LIMIT_MINUTES
        
        key = self._get_cooldown_key(telegram_id)
        await self.client.setex(key, timedelta(minutes=minutes), "1")
        return True
    
    # ==========================================
    # Statistics
    # ==========================================
    
    async def increment_stat(self, stat_name: str, increment: int = 1) -> int:
        """
        Increment a statistics counter
        
        Args:
            stat_name: Name of the statistic
            increment: Amount to increment
        
        Returns:
            int: New value
        """
        key = f"{self.PREFIX_STATS}{stat_name}"
        return await self.client.incrby(key, increment)
    
    async def get_stat(self, stat_name: str) -> int:
        """
        Get a statistics value
        
        Args:
            stat_name: Name of the statistic
        
        Returns:
            int: Current value
        """
        key = f"{self.PREFIX_STATS}{stat_name}"
        value = await self.client.get(key)
        return int(value) if value else 0
    
    # ==========================================
    # Health Check
    # ==========================================
    
    async def ping(self) -> bool:
        """
        Check Redis connection health
        
        Returns:
            bool: True if connected
        """
        try:
            await self.client.ping()
            return True
        except Exception:
            return False


# Global Redis client instance
redis_client = RedisClient()


# Utility functions
async def get_redis() -> RedisClient:
    """
    Get Redis client (dependency injection for FastAPI)
    """
    return redis_client


def hash_otp(otp: str) -> str:
    """
    Hash OTP code using SHA-256
    
    Args:
        otp: Plain text OTP code
    
    Returns:
        str: Hashed OTP
    """
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp_hash(otp: str, otp_hash: str) -> bool:
    """
    Verify OTP against stored hash
    
    Args:
        otp: Plain text OTP to verify
        otp_hash: Stored hash
    
    Returns:
        bool: True if match
    """
    return hash_otp(otp) == otp_hash

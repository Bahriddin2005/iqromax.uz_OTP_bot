"""
Supabase Admin API - Create auth.users for Telegram signup
Telegram OTP users are created in auth.users so public.users gets synced via trigger.
"""

import logging
import secrets
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)

_supabase_client = None


def get_supabase_admin():
    """Lazy init Supabase admin client."""
    global _supabase_client
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required for Telegram user creation"
            )
        from supabase import create_client
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    return _supabase_client


async def create_telegram_user(
    telegram_id: int,
    telegram_username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone_number: Optional[str] = None
) -> Optional[str]:
    """
    Create auth.users entry for Telegram user. Trigger syncs to public.users.
    Returns user UUID or None on failure.
    """
    try:
        client = get_supabase_admin()
        email = f"tg_{telegram_id}@anon.iqromax.uz"
        password = secrets.token_urlsafe(32)
        user_metadata = {
            "telegram_id": telegram_id,
            "telegram_username": telegram_username or "",
            "full_name": f"{first_name or ''} {last_name or ''}".strip() or None,
        }
        resp = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": user_metadata,
            "app_metadata": {"provider": "telegram"},
        })
        user = getattr(resp, "user", None) or (resp if hasattr(resp, "id") else None)
        if user and hasattr(user, "id"):
            user_id = str(user.id)
            logger.info(f"Created auth user for telegram_id={telegram_id}, id={user_id}")
            return user_id
    except Exception as e:
        logger.exception(f"Failed to create Telegram user: {e}")
    return None

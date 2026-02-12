"""User helper utilities (language, etc.) - works with both SQLite and Supabase models."""


def get_user_language(user) -> str:
    """Get language code from user. Works with Language enum or string."""
    if not user or not user.language:
        return "uz"
    return getattr(user.language, "value", user.language) or "uz"

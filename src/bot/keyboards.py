"""
iqromax.uz OTP Bot - Telegram Keyboards
Inline and reply keyboards for bot interactions
"""

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

from src.bot.locales import get_text


def get_main_keyboard(lang: str = "uz", is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Get main menu reply keyboard
    
    Args:
        lang: Language code
        is_admin: Whether user is admin
    
    Returns:
        ReplyKeyboardMarkup: Main keyboard
    """
    buttons = [
        [KeyboardButton(text=get_text("btn_share_phone", lang), request_contact=True)],
        [KeyboardButton(text=get_text("btn_language", lang))]
    ]
    
    if is_admin:
        buttons.append([KeyboardButton(text=get_text("btn_admin", lang))])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_language_keyboard() -> InlineKeyboardMarkup:
    """
    Get language selection inline keyboard
    6 til: O'zbek, Ingliz, Rus, Qozoq, Qirg'iz, Tojik
    """
    buttons = [
        [InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="lang:uz")],
        [InlineKeyboardButton(text="🇬🇧 Ingliz tili", callback_data="lang:en")],
        [InlineKeyboardButton(text="🇷🇺 Rus tili", callback_data="lang:ru")],
        [InlineKeyboardButton(text="🇰🇿 Qozoq tili", callback_data="lang:kk")],
        [InlineKeyboardButton(text="🇰🇬 Qirg'iziston tili", callback_data="lang:ky")],
        [InlineKeyboardButton(text="🇹🇯 Tojik tili", callback_data="lang:tg")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """
    Get admin panel inline keyboard
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Admin panel keyboard
    """
    buttons = [
        [InlineKeyboardButton(
            text=get_text("btn_statistics", lang),
            callback_data="admin:stats"
        )],
        [InlineKeyboardButton(
            text=get_text("btn_users", lang),
            callback_data="admin:users"
        )],
        [InlineKeyboardButton(
            text=get_text("btn_broadcast", lang),
            callback_data="admin:broadcast"
        )],
        [InlineKeyboardButton(
            text=get_text("btn_settings", lang),
            callback_data="admin:settings"
        )]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """
    Get cancel action inline keyboard
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Cancel keyboard
    """
    buttons = [
        [InlineKeyboardButton(
            text=get_text("btn_cancel", lang),
            callback_data="cancel"
        )]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """
    Get back button inline keyboard
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Back keyboard
    """
    buttons = [
        [InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:back"
        )]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard(lang: str = "uz", action: str = "confirm") -> InlineKeyboardMarkup:
    """
    Get confirmation inline keyboard
    
    Args:
        lang: Language code
        action: Action identifier for callback
    
    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=get_text("btn_yes", lang),
                callback_data=f"{action}:yes"
            ),
            InlineKeyboardButton(
                text=get_text("btn_no", lang),
                callback_data=f"{action}:no"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
    lang: str = "uz"
) -> InlineKeyboardMarkup:
    """
    Get pagination inline keyboard
    
    Args:
        current_page: Current page number (1-indexed)
        total_pages: Total number of pages
        callback_prefix: Prefix for callback data
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Pagination keyboard
    """
    buttons = []
    nav_row = []
    
    # Previous button
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"{callback_prefix}:page:{current_page - 1}"
        ))
    
    # Page indicator
    nav_row.append(InlineKeyboardButton(
        text=f"{current_page}/{total_pages}",
        callback_data="noop"
    ))
    
    # Next button
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"{callback_prefix}:page:{current_page + 1}"
        ))
    
    if nav_row:
        buttons.append(nav_row)
    
    # Back button
    buttons.append([InlineKeyboardButton(
        text=get_text("btn_back", lang),
        callback_data="admin:back"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def remove_keyboard() -> ReplyKeyboardRemove:
    """
    Get keyboard remover
    
    Returns:
        ReplyKeyboardRemove: Keyboard remover
    """
    return ReplyKeyboardRemove()

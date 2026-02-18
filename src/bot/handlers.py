"""
iqromax.uz OTP Bot - Telegram Bot Handlers
Message and command handlers using aiogram
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from src.config import settings
from src.models import db_session, User, Language
from src.services import get_otp_service
from src.utils import is_admin, validate_otp_code, get_user_language
from src.bot.keyboards import (
    get_main_keyboard, get_language_keyboard,
    get_admin_keyboard, get_cancel_keyboard
)
from src.bot.locales import get_text, LANGUAGES



logger = logging.getLogger(__name__)

# Create router
router = Router()


# ==========================================
# User Commands
# ==========================================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Handle /start command
    Activates the bot for the user
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    logger.info(f"User started bot: {user_id} (@{username})")
    
    with db_session() as db:
        otp_service = get_otp_service(db)
        user = await otp_service.get_or_create_user(
            telegram_id=user_id,
            telegram_username=username,
            first_name=first_name,
            last_name=last_name
        )
        lang = get_user_language(user)
        welcome_text = get_text("welcome", lang)
        await message.answer(
            welcome_text,
            reply_markup=get_main_keyboard(lang, is_admin(user_id))
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Handle /help command
    """
    user_id = message.from_user.id
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        await message.answer(get_text("help", lang))


@router.message(F.contact)
async def handle_contact_share(message: Message):
    """
    Handle phone number share via Contact button
    """
    user_id = message.from_user.id
    contact = message.contact
    
    # Verify contact belongs to the sender (security)
    if contact.user_id != user_id:
        with db_session() as db:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            lang = get_user_language(user)
            await message.answer(get_text("error", lang))
        return
    
    phone = contact.phone_number or ""
    if not phone.startswith("+"):
        phone = "+" + phone
    
    with db_session() as db:
        otp_service = get_otp_service(db)
        user = await otp_service.get_or_create_user(
            telegram_id=user_id,
            telegram_username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            phone_number=phone
        )
        lang = get_user_language(user)
        await message.answer(get_text("phone_saved", lang))


@router.message(Command("language"))
async def cmd_language(message: Message):
    """
    Handle /language command yoki Til tugmasi
    Tillarni tanlash inline keyboard ko'rsatadi
    """
    user_id = message.from_user.id
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        await message.answer(get_text("select_language", lang), reply_markup=get_language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def callback_language(callback: CallbackQuery):
    """
    Handle language selection callback
    """
    user_id = callback.from_user.id
    selected_lang = callback.data.split(":")[1]
    
    if selected_lang not in LANGUAGES:
        await callback.answer("Invalid language")
        return
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            from src.models import USE_SUPABASE
            user.language = selected_lang if USE_SUPABASE else Language(selected_lang)
            db.commit()
            
            text = get_text("language_changed", selected_lang)
            # Inline keyboardni olib tashlash - qayta bosilganda xato bo'lmasligi uchun
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
            await callback.answer()
            
            # Send updated main menu
            await callback.message.answer(
                get_text("menu", selected_lang),
                reply_markup=get_main_keyboard(selected_lang, is_admin(user_id))
            )
        else:
            await callback.answer("User not found")


@router.message(Command("status"))
async def cmd_status(message: Message):
    """
    Handle /status command
    Check current OTP status
    """
    user_id = message.from_user.id
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        otp_service = get_otp_service(db)
        status = await otp_service.get_otp_status(user_id)
        text = (
            get_text("otp_status", lang).format(
                status=status["status"],
                attempts=status["attempts"],
                max_attempts=status["max_attempts"],
                expires_in=status["expires_in_seconds"],
            )
            if status
            else get_text("no_active_otp", lang)
        )
        await message.answer(text)


# ==========================================
# Admin Commands
# ==========================================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """
    Handle /admin command
    Show admin panel (admin only)
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Sizda admin huquqi yo'q.")
        logger.warning(f"Unauthorized admin access attempt: {user_id}")
        return
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        await message.answer(get_text("admin_panel", lang), reply_markup=get_admin_keyboard(lang))


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """
    Handle /stats command
    Show OTP statistics (admin only)
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Sizda admin huquqi yo'q.")
        return
    
    from src.bot.admin import get_statistics_text

    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        stats_text = await get_statistics_text(db, lang)
        await message.answer(stats_text, parse_mode="HTML")


@router.message(Command("users"))
async def cmd_users(message: Message):
    """
    Handle /users command
    Show user statistics (admin only)
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Sizda admin huquqi yo'q.")
        return
    
    from src.bot.admin import get_users_text

    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        users_text = await get_users_text(db, lang)
        await message.answer(users_text, parse_mode="HTML")


# ==========================================
# Admin Callbacks
# ==========================================

@router.callback_query(F.data == "admin:stats")
async def callback_admin_stats(callback: CallbackQuery):
    """
    Handle admin statistics callback
    """
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    
    from src.bot.admin import get_statistics_text

    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        stats_text = await get_statistics_text(db, lang)
        await callback.message.edit_text(stats_text, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "admin:users")
async def callback_admin_users(callback: CallbackQuery):
    """
    Handle admin users callback
    """
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    
    from src.bot.admin import get_users_text

    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        users_text = await get_users_text(db, lang)
        await callback.message.edit_text(users_text, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "admin:back")
async def callback_admin_back(callback: CallbackQuery):
    """
    Handle back to admin panel callback
    """
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        await callback.message.edit_text(
            get_text("admin_panel", lang),
            reply_markup=get_admin_keyboard(lang),
        )
        await callback.answer()


# ==========================================
# Message Handlers
# ==========================================

@router.message(F.text)
async def handle_text_message(message: Message):
    """
    Handle regular text messages
    """
    user_id = message.from_user.id
    text = (message.text or "").strip()

    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        lang = get_user_language(user)
        
        # Til tugmasi bosilganida - barcha tillardagi "Til" tugmasi matnini tekshirish
        if any(text == get_text("btn_language", l) for l in LANGUAGES):
            lang_text = get_text("select_language", lang)
            await message.answer(lang_text, reply_markup=get_language_keyboard())
            return
        
        # Admin tugmasi bosilganida
        if any(text == get_text("btn_admin", l) for l in LANGUAGES):
            if is_admin(user_id):
                text_admin = get_text("admin_panel", lang)
                await message.answer(text_admin, reply_markup=get_admin_keyboard(lang))
            else:
                await message.answer("⛔ Sizda admin huquqi yo'q.")
            return
        
        # Check if it looks like an OTP code
        if text.isdigit() and len(text) == settings.OTP_LENGTH:
            otp_service = get_otp_service(db)
            is_valid, status, otp_request = await otp_service.verify_otp(user_id, text)
            
            if is_valid:
                response = get_text("otp_verified", lang)
            elif status == "otp_not_found":
                response = get_text("no_active_otp", lang)
            elif status == "otp_expired":
                response = get_text("otp_expired", lang)
            elif status.startswith("invalid_otp:"):
                remaining = status.split(":")[1]
                response = get_text("otp_invalid", lang).format(remaining=remaining)
            elif status == "max_attempts_exceeded":
                response = get_text("max_attempts", lang)
            else:
                response = get_text("error", lang)
            
            await message.answer(response)
        else:
            response = get_text("unknown_message", lang)
            await message.answer(response)


@router.message()
async def handle_other_content(message: Message):
    """
    Handle non-text messages (photos, stickers, etc.) to avoid "Update is not handled"
    """
    with db_session() as db:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        lang = get_user_language(user)
        await message.answer(get_text("unknown_message", lang))


# ==========================================
# Error Handler
# ==========================================

@router.error()
async def error_handler(event, **kwargs):
    """
    Handle errors in handlers. Event is ErrorEvent with .exception attribute.
    """
    exc = getattr(event, "exception", event)
    logger.error(f"Error in handler: {exc}", exc_info=True)
    return True

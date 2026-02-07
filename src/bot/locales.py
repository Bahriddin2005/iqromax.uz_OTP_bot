"""
iqromax.uz OTP Bot - Localization
Multi-language support (Uzbek, Russian, English)
"""

from typing import Dict, Optional


# Supported languages: O'zbek, Ingliz, Rus, Qozoq, Qirg'iz, Tojik
LANGUAGES = ["uz", "en", "ru", "kk", "ky", "tg"]

# Fallback: kk, ky, tg -> ru (if translation missing)
FALLBACK_LANG = {"kk": "ru", "ky": "ru", "tg": "ru"}

# Default language
DEFAULT_LANGUAGE = "uz"


# ==========================================
# Translation Dictionary
# ==========================================

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ==========================================
    # Welcome & General Messages
    # ==========================================
    "welcome": {
        "uz": """🎉 Assalomu alaykum, {name}!

<b>iqromax.uz</b> OTP tasdiqlash botiga xush kelibsiz!

Bu bot orqali siz iqromax.uz saytida ro'yxatdan o'tishingizni tasdiqlashingiz mumkin.

📌 <b>Qanday ishlaydi:</b>
1. Saytda ro'yxatdan o'ting
2. Bot sizga 6 xonali kod yuboradi
3. Kodni saytga kiriting

❓ Yordam uchun /help buyrug'ini yuboring.""",
        
        "ru": """🎉 Здравствуйте, {name}!

Добро пожаловать в бот подтверждения OTP <b>iqromax.uz</b>!

С помощью этого бота вы можете подтвердить регистрацию на сайте iqromax.uz.

📌 <b>Как это работает:</b>
1. Зарегистрируйтесь на сайте
2. Бот отправит вам 6-значный код
3. Введите код на сайте

❓ Для помощи отправьте команду /help.""",
        
        "en": """🎉 Hello, {name}!

Welcome to the <b>iqromax.uz</b> OTP verification bot!

This bot helps you verify your registration on iqromax.uz website.

📌 <b>How it works:</b>
1. Register on the website
2. Bot will send you a 6-digit code
3. Enter the code on the website

❓ For help, send /help command.""",
        
        "kk": """🎉 Сәлем, {name}!

<b>iqromax.uz</b> OTP растау ботіне қош келдіңіз!

Осы бот арқылы iqromax.uz сайтында тіркелуіңізді растай аласыз.

📌 <b>Қалай жұмыс істейді:</b>
1. Сайтта тіркеліңіз
2. Бот сізге 6 таңбалы код жібереді
3. Кодты сайтқа енгізіңіз""",
        
        "ky": """🎉 Салам, {name}!

<b>iqromax.uz</b> OTP ырастоо ботине кош келиңиз!

Бул бот аркылуу iqromax.uz сайтында катталууңузду ырастай аласыз.

📌 <b>Кантип иштейт:</b>
1. Сайтта катталыңыз
2. Бот сизге 6 сандык код жөнөйт
3. Кодду сайтта киргизиңиз""",
        
        "tg": """🎉 Салом, {name}!

Ба боти тасдиқи OTP <b>iqromax.uz</b> хуш омадед!

Ин бот ба шумо имкон медиҳад ки дар сомонаи iqromax.uz ба сабт шудан тасдиқ кунед.

📌 <b>Чӣ гуна кор мекунад:</b>
1. Дар сомона сабт шавед
2. Бот ба шумо рамзи 6 рақамӣ мефиристад
3. Рамзро дар сомона ворид кунед"""
    },
    
    "help": {
        "uz": """📚 <b>Yordam</b>

<b>Mavjud buyruqlar:</b>
/start - Botni ishga tushirish
/help - Yordam ko'rsatish
/language - Tilni o'zgartirish
/status - OTP holatini tekshirish

<b>OTP haqida:</b>
• Kod 6 xonali raqamlardan iborat
• Kod 3 daqiqa amal qiladi
• Maksimal 3 ta urinish mavjud
• Kodni hech kimga bermang!

<b>Muammo bo'lsa:</b>
Sayt administratoriga murojaat qiling.""",
        
        "ru": """📚 <b>Помощь</b>

<b>Доступные команды:</b>
/start - Запустить бота
/help - Показать помощь
/language - Изменить язык
/status - Проверить статус OTP

<b>Об OTP:</b>
• Код состоит из 6 цифр
• Код действителен 3 минуты
• Максимум 3 попытки
• Никому не сообщайте код!

<b>При проблемах:</b>
Обратитесь к администратору сайта.""",
        
        "en": """📚 <b>Help</b>

<b>Available commands:</b>
/start - Start the bot
/help - Show help
/language - Change language
/status - Check OTP status

<b>About OTP:</b>
• Code consists of 6 digits
• Code is valid for 3 minutes
• Maximum 3 attempts
• Never share your code!

<b>If you have problems:</b>
Contact the site administrator."""
    },
    
    "menu": {
        "uz": "📋 Asosiy menyu",
        "ru": "📋 Главное меню",
        "en": "📋 Main menu",
        "kk": "📋 Басты мәзір",
        "ky": "📋 Негизги меню",
        "tg": "📋 Менюи асосӣ"
    },
    
    # ==========================================
    # OTP Messages
    # ==========================================
    "otp_message": {
        "uz": """🔐 <b>Iqromax.uz</b> ro'yxatdan o'tish kodi:

<code>{otp}</code>

⏳ Kod <b>{minutes} daqiqa</b> amal qiladi.
Agar bu siz bo'lmasangiz, e'tibor bermang.""",
        
        "ru": """🔐 Код подтверждения <b>iqromax.uz</b>

Ваш код: <code>{otp}</code>

⏰ Код действителен <b>{minutes} минут</b>.
⚠️ Никому не сообщайте код!

Если вы не запрашивали этот код, проигнорируйте это сообщение.""",
        
        "en": """🔐 <b>iqromax.uz</b> verification code

Your code: <code>{otp}</code>

⏰ Code is valid for <b>{minutes} minutes</b>.
⚠️ Never share this code with anyone!

If you didn't request this code, please ignore this message.""",
        
        "kk": """🔐 <b>iqromax.uz</b> растау коды

Сіздің кодыңыз: <code>{otp}</code>

⏰ Код <b>{minutes} минут</b> жарамды.
⚠️ Кодты ешкімге бермеңіз!""",
        
        "ky": """🔐 <b>iqromax.uz</b> ырастоо коду

Сиздин кодуңуз: <code>{otp}</code>

⏰ Код <b>{minutes} мүнөт</b> жарактуу.
⚠️ Кодду эчкимге бербеңиз!""",
        
        "tg": """🔐 Рамзи тасдиқи <b>iqromax.uz</b>

Рамзи шумо: <code>{otp}</code>

⏰ Рамз <b>{minutes} дақиқа</b> эътибор дорад.
⚠️ Рамзро ба ҳеҷ кас надод!"""
    },
    
    "otp_verified": {
        "uz": "✅ OTP muvaffaqiyatli tasdiqlandi! Endi saytda davom etishingiz mumkin.",
        "ru": "✅ OTP успешно подтверждён! Теперь вы можете продолжить на сайте.",
        "en": "✅ OTP verified successfully! You can now continue on the website.",
        "kk": "✅ OTP сәтті расталды! Енді сайтта жалғастыра аласыз.",
        "ky": "✅ OTP ийгиликтүү ырасталды! Эми сайтта уланта аласыз.",
        "tg": "✅ OTP бо муваффақият тасдиқ шуд! Ҳоло дар сомона идома диҳед."
    },
    
    "otp_invalid": {
        "uz": "❌ Noto'g'ri kod. Qolgan urinishlar: {remaining}",
        "ru": "❌ Неверный код. Осталось попыток: {remaining}",
        "en": "❌ Invalid code. Remaining attempts: {remaining}"
    },
    
    "otp_expired": {
        "uz": "⏰ Kod muddati tugagan. Iltimos, yangi kod so'rang.",
        "ru": "⏰ Срок действия кода истёк. Пожалуйста, запросите новый код.",
        "en": "⏰ Code has expired. Please request a new code."
    },
    
    "max_attempts": {
        "uz": "🚫 Maksimal urinishlar soni tugadi. Iltimos, yangi kod so'rang.",
        "ru": "🚫 Превышено максимальное количество попыток. Запросите новый код.",
        "en": "🚫 Maximum attempts exceeded. Please request a new code."
    },
    
    "no_active_otp": {
        "uz": "ℹ️ Sizda faol OTP kod mavjud emas.",
        "ru": "ℹ️ У вас нет активного OTP кода.",
        "en": "ℹ️ You don't have an active OTP code."
    },
    
    "otp_status": {
        "uz": """📊 <b>OTP holati</b>

Holat: {status}
Urinishlar: {attempts}/{max_attempts}
Qolgan vaqt: {expires_in} soniya""",
        
        "ru": """📊 <b>Статус OTP</b>

Статус: {status}
Попытки: {attempts}/{max_attempts}
Осталось времени: {expires_in} секунд""",
        
        "en": """📊 <b>OTP Status</b>

Status: {status}
Attempts: {attempts}/{max_attempts}
Time remaining: {expires_in} seconds"""
    },
    
    # ==========================================
    # Language
    # ==========================================
    "select_language": {
        "uz": "🌐 Tilni tanlang:",
        "ru": "🌐 Выберите язык:",
        "en": "🌐 Select language:",
        "kk": "🌐 Тілді таңдаңыз:",
        "ky": "🌐 Тилди тандаңыз:",
        "tg": "🌐 Забонро интихоб кунед:"
    },
    
    "language_changed": {
        "uz": "✅ Til o'zbekchaga o'zgartirildi.",
        "ru": "✅ Язык изменён на русский.",
        "en": "✅ Language changed to English.",
        "kk": "✅ Тіл қазақшаға өзгертілді.",
        "ky": "✅ Тил кыргызчага өзгөртүлдү.",
        "tg": "✅ Забон ба тоҷикӣ тағйир ёфт."
    },
    
    # ==========================================
    # Admin Panel
    # ==========================================
    "admin_panel": {
        "uz": """👨‍💼 <b>Admin Panel</b>

Quyidagi amallardan birini tanlang:""",
        
        "ru": """👨‍💼 <b>Панель администратора</b>

Выберите одно из действий:""",
        
        "en": """👨‍💼 <b>Admin Panel</b>

Select one of the actions:"""
    },
    
    "statistics_title": {
        "uz": "Statistika",
        "ru": "Статистика",
        "en": "Statistics"
    },
    
    # ==========================================
    # Buttons
    # ==========================================
    "btn_help": {
        "uz": "❓ Yordam",
        "ru": "❓ Помощь",
        "en": "❓ Help"
    },
    
    "btn_language": {
        "uz": "🌐 Til",
        "ru": "🌐 Язык",
        "en": "🌐 Language",
        "kk": "🌐 Тіл",
        "ky": "🌐 Тил",
        "tg": "🌐 Забон"
    },
    
    "btn_status": {
        "uz": "📊 OTP holati",
        "ru": "📊 Статус OTP",
        "en": "📊 OTP Status"
    },
    
    "btn_share_phone": {
        "uz": "📱 Telefon raqamni yuborish",
        "ru": "📱 Отправить номер телефона",
        "en": "📱 Share phone number",
        "kk": "📱 Телефон нөмірін жіберу",
        "ky": "📱 Телефон номерин жөнөтүү",
        "tg": "📱 Рақами телефонро фиристед"
    },
    
    "btn_admin": {
        "uz": "👨‍💼 Admin",
        "ru": "👨‍💼 Админ",
        "en": "👨‍💼 Admin",
        "kk": "👨‍💼 Админ",
        "ky": "👨‍💼 Админ",
        "tg": "👨‍💼 Админ"
    },
    
    "btn_statistics": {
        "uz": "📊 Statistika",
        "ru": "📊 Статистика",
        "en": "📊 Statistics"
    },
    
    "btn_users": {
        "uz": "👥 Foydalanuvchilar",
        "ru": "👥 Пользователи",
        "en": "👥 Users"
    },
    
    "btn_broadcast": {
        "uz": "📢 Xabar yuborish",
        "ru": "📢 Рассылка",
        "en": "📢 Broadcast"
    },
    
    "btn_settings": {
        "uz": "⚙️ Sozlamalar",
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings"
    },
    
    "btn_cancel": {
        "uz": "❌ Bekor qilish",
        "ru": "❌ Отмена",
        "en": "❌ Cancel"
    },
    
    "btn_back": {
        "uz": "⬅️ Orqaga",
        "ru": "⬅️ Назад",
        "en": "⬅️ Back"
    },
    
    "btn_yes": {
        "uz": "✅ Ha",
        "ru": "✅ Да",
        "en": "✅ Yes"
    },
    
    "btn_no": {
        "uz": "❌ Yo'q",
        "ru": "❌ Нет",
        "en": "❌ No"
    },
    
    # ==========================================
    # Statistics Labels
    # ==========================================
    "users": {
        "uz": "Foydalanuvchilar",
        "ru": "Пользователи",
        "en": "Users"
    },
    
    "total": {
        "uz": "Jami",
        "ru": "Всего",
        "en": "Total"
    },
    
    "active_today": {
        "uz": "Bugun faol",
        "ru": "Активных сегодня",
        "en": "Active today"
    },
    
    "new_today": {
        "uz": "Bugun yangi",
        "ru": "Новых сегодня",
        "en": "New today"
    },
    
    "otp_stats": {
        "uz": "OTP statistikasi",
        "ru": "Статистика OTP",
        "en": "OTP Statistics"
    },
    
    "total_sent": {
        "uz": "Jami yuborilgan",
        "ru": "Всего отправлено",
        "en": "Total sent"
    },
    
    "sent_today": {
        "uz": "Bugun yuborilgan",
        "ru": "Отправлено сегодня",
        "en": "Sent today"
    },
    
    "verified_today": {
        "uz": "Bugun tasdiqlangan",
        "ru": "Подтверждено сегодня",
        "en": "Verified today"
    },
    
    "expired_today": {
        "uz": "Bugun eskirgan",
        "ru": "Истекло сегодня",
        "en": "Expired today"
    },
    
    "failed_today": {
        "uz": "Bugun muvaffaqiyatsiz",
        "ru": "Неудачных сегодня",
        "en": "Failed today"
    },
    
    "success_rate": {
        "uz": "Muvaffaqiyat darajasi",
        "ru": "Процент успеха",
        "en": "Success rate"
    },
    
    "updated_at": {
        "uz": "Yangilangan vaqt",
        "ru": "Обновлено",
        "en": "Updated at"
    },
    
    # ==========================================
    # User Details Labels
    # ==========================================
    "users_list": {
        "uz": "Foydalanuvchilar ro'yxati",
        "ru": "Список пользователей",
        "en": "Users list"
    },
    
    "page": {
        "uz": "Sahifa",
        "ru": "Страница",
        "en": "Page"
    },
    
    "username": {
        "uz": "Username",
        "ru": "Имя пользователя",
        "en": "Username"
    },
    
    "name": {
        "uz": "Ism",
        "ru": "Имя",
        "en": "Name"
    },
    
    "registered": {
        "uz": "Ro'yxatdan o'tgan",
        "ru": "Зарегистрирован",
        "en": "Registered"
    },
    
    "no_users": {
        "uz": "Foydalanuvchilar topilmadi",
        "ru": "Пользователи не найдены",
        "en": "No users found"
    },
    
    "user_details": {
        "uz": "Foydalanuvchi ma'lumotlari",
        "ru": "Информация о пользователе",
        "en": "User details"
    },
    
    "phone": {
        "uz": "Telefon",
        "ru": "Телефон",
        "en": "Phone"
    },
    
    "language": {
        "uz": "Til",
        "ru": "Язык",
        "en": "Language"
    },
    
    "status": {
        "uz": "Holat",
        "ru": "Статус",
        "en": "Status"
    },
    
    "total_requests": {
        "uz": "Jami so'rovlar",
        "ru": "Всего запросов",
        "en": "Total requests"
    },
    
    "verified": {
        "uz": "Tasdiqlangan",
        "ru": "Подтверждено",
        "en": "Verified"
    },
    
    "dates": {
        "uz": "Sanalar",
        "ru": "Даты",
        "en": "Dates"
    },
    
    "last_activity": {
        "uz": "Oxirgi faollik",
        "ru": "Последняя активность",
        "en": "Last activity"
    },
    
    # ==========================================
    # Errors
    # ==========================================
    "error": {
        "uz": "❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.",
        "ru": "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
        "en": "❌ An error occurred. Please try again later."
    },
    
    "unknown_message": {
        "uz": "🤔 Tushunmadim. Yordam uchun /help buyrug'ini yuboring.",
        "ru": "🤔 Не понял. Для помощи отправьте команду /help.",
        "en": "🤔 I didn't understand. Send /help for assistance."
    },
    
    "phone_saved": {
        "uz": "✅ Telefon raqamingiz saqlandi: {phone}",
        "ru": "✅ Ваш номер телефона сохранён: {phone}",
        "en": "✅ Your phone number saved: {phone}",
        "kk": "✅ Телефон нөміріңіз сақталды: {phone}",
        "ky": "✅ Телефон номериңиз сакталды: {phone}",
        "tg": "✅ Рақами телефон шумо захира шуд: {phone}"
    },
    
    "error": {
        "uz": "❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.",
        "ru": "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
        "en": "❌ An error occurred. Please try again later.",
        "kk": "❌ Қате орын алды. Кейінірек қайта көріңіз.",
        "ky": "❌ Үчүрөөк кетти. Кийинчерээк кайра аракет кылыңыз.",
        "tg": "❌ Хато рух дод. Лутфан баъдтар кӯшиш кунед."
    },
    
    "unknown_message": {
        "uz": "🤔 Tushunmadim. Yordam uchun /help buyrug'ini yuboring.",
        "ru": "🤔 Не понял. Для помощи отправьте команду /help.",
        "en": "🤔 I didn't understand. Send /help for assistance.",
        "kk": "🤔 Түсінбедім. Көмек үшін /help жіберіңіз.",
        "ky": "🤔 Түшүнбөдүм. Жардам үчүн /help жөнөтүңүз.",
        "tg": "🤔 Фаҳмидам. Кӯмак барои /help фиристед."
    }
}


def get_text(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """
    Get translated text for a key
    
    Args:
        key: Translation key
        lang: Language code (uz, en, ru, kk, ky, tg)
    
    Returns:
        str: Translated text or key if not found
    """
    if lang not in LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    if key not in TRANSLATIONS:
        return key
    
    translations = TRANSLATIONS[key]
    
    if lang in translations:
        return translations[lang]
    
    # Fallback: kk, ky, tg -> ru
    fallback = FALLBACK_LANG.get(lang)
    if fallback and fallback in translations:
        return translations[fallback]
    
    if DEFAULT_LANGUAGE in translations:
        return translations[DEFAULT_LANGUAGE]
    
    return key


def get_all_translations(key: str) -> Dict[str, str]:
    """
    Get all translations for a key
    
    Args:
        key: Translation key
    
    Returns:
        Dict[str, str]: All translations for the key
    """
    return TRANSLATIONS.get(key, {})


def add_translation(key: str, translations: Dict[str, str]):
    """
    Add or update a translation
    
    Args:
        key: Translation key
        translations: Dict of language code to text
    """
    if key not in TRANSLATIONS:
        TRANSLATIONS[key] = {}
    
    TRANSLATIONS[key].update(translations)

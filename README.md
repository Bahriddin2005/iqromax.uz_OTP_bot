# iqromax.uz Telegram OTP Verification Bot

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

**Xavfsiz, tezkor va to'liq avtomatlashtirilgan Telegram OTP tasdiqlash tizimi**

</div>

---

## 📋 Mundarija

- [Loyiha haqida](#-loyiha-haqida)
- [Xususiyatlar](#-xususiyatlar)
- [Arxitektura](#-arxitektura)
- [O'rnatish](#-ornatish)
- [Konfiguratsiya](#-konfiguratsiya)
- [API dokumentatsiyasi](#-api-dokumentatsiyasi)
- [Database strukturasi](#-database-strukturasi)
- [Xavfsizlik](#-xavfsizlik)
- [Ishga tushirish](#-ishga-tushirish)
- [Monitoring](#-monitoring)

---

## 📖 Loyiha haqida

Bu loyiha **iqromax.uz** web saytida foydalanuvchilarni Telegram orqali tasdiqlash uchun yaratilgan. Foydalanuvchi saytda ro'yxatdan o'tayotganda, uning Telegram akkauntiga 6 xonali bir martalik parol (OTP) yuboriladi va shu kod orqali ro'yxatdan o'tish tasdiqlanadi.

### Ishlash jarayoni

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Web Sayt  │────▶│  Backend    │────▶│  Telegram   │────▶│ Foydalanuvchi│
│  (Frontend) │     │    API      │     │     Bot     │     │  (Telegram)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       │   1. Ro'yxatdan   │                   │                   │
       │      o'tish       │                   │                   │
       │──────────────────▶│                   │                   │
       │                   │   2. OTP yaratish │                   │
       │                   │      va yuborish  │                   │
       │                   │──────────────────▶│                   │
       │                   │                   │   3. OTP xabar    │
       │                   │                   │──────────────────▶│
       │                   │                   │                   │
       │   4. OTP kiritish │                   │                   │
       │──────────────────▶│                   │                   │
       │                   │   5. OTP tekshirish                   │
       │                   │──────────────────▶│                   │
       │   6. Natija       │                   │                   │
       │◀──────────────────│                   │                   │
       │                   │                   │                   │
```

---

## ✨ Xususiyatlar

### Asosiy funksiyalar
- ✅ 6 xonali xavfsiz OTP generatsiyasi
- ✅ OTP yuborish va tasdiqlash
- ✅ 3 daqiqalik amal qilish muddati
- ✅ Maksimal 3 ta urinish cheklovi
- ✅ Rate limiting (soatiga 5 ta so'rov)
- ✅ Cooldown (so'rovlar orasida 1 daqiqa)

### Xavfsizlik
- 🔒 OTP hashlab saqlanadi (SHA-256)
- 🔒 API kaliti orqali autentifikatsiya
- 🔒 Brute force himoyasi
- 🔒 SQL Injection himoyasi
- 🔒 HTTPS majburiy (production)
- 🔒 CORS sozlamalari

### Admin funksiyalari
- 📊 Real-time statistika
- 👥 Foydalanuvchilar boshqaruvi
- 🚫 Foydalanuvchilarni bloklash
- 📝 Admin harakatlar logi

### Multi-language
- 🇺🇿 O'zbekcha
- 🇷🇺 Русский
- 🇬🇧 English

---

## 🏗 Arxitektura

```
iqromax-otp-bot/
├── src/
│   ├── api/                 # FastAPI REST API
│   │   ├── app.py          # Asosiy FastAPI application
│   │   ├── routes.py       # OTP API endpointlar
│   │   ├── admin_routes.py # Admin API endpointlar
│   │   └── schemas.py      # Pydantic modellar
│   │
│   ├── bot/                 # Telegram Bot (aiogram)
│   │   ├── bot.py          # Bot initialization
│   │   ├── handlers.py     # Message handlers
│   │   ├── keyboards.py    # Inline/Reply keyboards
│   │   ├── admin.py        # Admin funksiyalari
│   │   └── locales.py      # Multi-language
│   │
│   ├── config/              # Konfiguratsiya
│   │   └── settings.py     # Environment variables
│   │
│   ├── models/              # Database modellar
│   │   ├── database.py     # SQLAlchemy modellar
│   │   └── redis_client.py # Redis client
│   │
│   ├── services/            # Business logic
│   │   └── otp_service.py  # OTP xizmati
│   │
│   ├── utils/               # Utility funksiyalar
│   │   ├── security.py     # Xavfsizlik
│   │   └── logging_config.py
│   │
│   └── locales/             # Tarjimalar (JSON)
│
├── tests/                   # Unit testlar
├── docs/                    # Dokumentatsiya
├── scripts/                 # Utility skriptlar
├── logs/                    # Log fayllar
├── .env.example            # Environment namunasi
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker compose
└── README.md
```

---

## 🚀 O'rnatish

### Talablar

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Telegram Bot Token (@BotFather dan)

### 1. Repozitoriyani klonlash

```bash
git clone https://github.com/your-username/iqromax-otp-bot.git
cd iqromax-otp-bot
```

### 2. Virtual environment yaratish

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate     # Windows
```

### 3. Dependencies o'rnatish

```bash
pip install -r requirements.txt
```

### 4. Environment sozlash

```bash
cp .env.example .env
# .env faylni tahrirlang
```

### 5. Database yaratish

```bash
# PostgreSQL
createdb iqromax_otp

# Yoki psql orqali
psql -U postgres -c "CREATE DATABASE iqromax_otp;"
```

### 6. Migratsiyalarni ishga tushirish

```bash
python -c "from src.models import init_db; init_db()"
```

---

## ⚙️ Konfiguratsiya

### Environment Variables

| O'zgaruvchi | Tavsif | Namuna |
|-------------|--------|--------|
| `TELEGRAM_BOT_TOKEN` | Bot token (@BotFather) | `123456:ABC-DEF...` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@localhost/db` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `API_SECRET_KEY` | API autentifikatsiya kaliti | `your-secret-key` |
| `OTP_EXPIRY_MINUTES` | OTP amal qilish muddati | `3` |
| `OTP_MAX_ATTEMPTS` | Maksimal urinishlar | `3` |
| `ADMIN_TELEGRAM_IDS` | Admin ID lar (vergul bilan) | `123456789,987654321` |

---

## 📚 API Dokumentatsiyasi

### Base URL
```
https://api.iqromax.uz/api/v1
```

### Autentifikatsiya
Barcha so'rovlarda `X-API-Key` header talab qilinadi.

```http
X-API-Key: your-api-secret-key
```

### Endpoints

#### 1. OTP Yuborish

```http
POST /send-otp
Content-Type: application/json
X-API-Key: your-api-key

{
    "telegram_id": 123456789,
    "telegram_username": "johndoe",
    "name": "John Doe",
    "phone": "+998901234567",
    "source": "web_registration"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "OTP yuborildi",
    "code": "otp_sent",
    "data": {
        "expires_in": 180,
        "max_attempts": 3
    }
}
```

#### 2. OTP Tasdiqlash

```http
POST /verify-otp
Content-Type: application/json
X-API-Key: your-api-key

{
    "telegram_id": 123456789,
    "otp": "482917"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "OTP tasdiqlandi",
    "code": "verified",
    "data": {
        "telegram_id": 123456789,
        "verified_at": "2024-01-15T10:30:00Z"
    }
}
```

#### 3. OTP Qayta Yuborish

```http
POST /resend-otp
Content-Type: application/json
X-API-Key: your-api-key

{
    "telegram_id": 123456789
}
```

#### 4. OTP Holatini Tekshirish

```http
GET /otp-status/123456789
X-API-Key: your-api-key
```

**Response:**
```json
{
    "success": true,
    "message": "OTP holati",
    "code": "status",
    "data": {
        "status": "pending",
        "attempts": 1,
        "max_attempts": 3,
        "remaining_attempts": 2,
        "expires_in_seconds": 120
    }
}
```

#### 5. Health Check

```http
GET /health
```

### Error Responses

| Status Code | Tavsif |
|-------------|--------|
| 400 | Noto'g'ri so'rov |
| 401 | Autentifikatsiya xatosi |
| 404 | Topilmadi |
| 429 | Rate limit |
| 500 | Server xatosi |

---

## 🗄 Database Strukturasi

### Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(20),
    language VARCHAR(2) DEFAULT 'uz',
    is_active BOOLEAN DEFAULT TRUE,
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW()
);
```

### OTP Requests Table

```sql
CREATE TABLE otp_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    otp_hash VARCHAR(255) NOT NULL,
    request_source VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP
);
```

### ER Diagram

```
┌──────────────┐       ┌──────────────────┐
│    users     │       │   otp_requests   │
├──────────────┤       ├──────────────────┤
│ id (PK)      │───┐   │ id (PK)          │
│ telegram_id  │   │   │ user_id (FK)     │──┘
│ username     │   └───│ otp_hash         │
│ first_name   │       │ status           │
│ language     │       │ attempts         │
│ is_blocked   │       │ expires_at       │
│ created_at   │       │ verified_at      │
└──────────────┘       └──────────────────┘
```

---

## 🔒 Xavfsizlik

### OTP Xavfsizligi
- OTP kodlar `secrets.randbelow()` yordamida generatsiya qilinadi
- Kodlar SHA-256 hash holatda saqlanadi
- Amal qilish muddati (TTL) Redis orqali boshqariladi

### API Xavfsizligi
- API kaliti orqali autentifikatsiya
- Rate limiting (soatiga 5 ta so'rov)
- Brute force himoyasi (5 ta muvaffaqiyatsiz urinishdan keyin 15 daqiqa bloklash)
- CORS sozlamalari

### Best Practices
1. Production da HTTPS ishlatish
2. API kalitini xavfsiz saqlash
3. Admin ID larni .env da saqlash
4. Loglarni muntazam tekshirish

---

## 🏃 Ishga Tushirish

### Development Mode

```bash
# Bot va API ni birga ishga tushirish
python main.py

# Yoki alohida
python -m src.bot.bot      # Faqat bot
uvicorn src.api.app:app    # Faqat API
```

### Production Mode (Docker)

```bash
docker-compose up -d
```

### Production Mode (Systemd)

```bash
# Service faylni yaratish
sudo cp scripts/iqromax-otp.service /etc/systemd/system/
sudo systemctl enable iqromax-otp
sudo systemctl start iqromax-otp
```

---

## 📊 Monitoring

### Loglar

```bash
# Application logs
tail -f logs/app.log

# Error logs
tail -f logs/error.log
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Admin Statistika

Bot orqali `/stats` buyrug'i yoki API orqali:

```bash
curl -H "X-API-Key: your-key" \
     -H "X-Admin-ID: 123456789" \
     http://localhost:8000/api/v1/admin/statistics
```

---

## 📝 License

MIT License - Batafsil ma'lumot uchun [LICENSE](LICENSE) faylini ko'ring.

---

## 👥 Muallif

**iqromax.uz** jamoasi

---

<div align="center">

**iqromax.uz** © 2024

</div>

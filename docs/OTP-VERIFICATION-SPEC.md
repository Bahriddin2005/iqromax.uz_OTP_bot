# Telegram Bot → OTP → Website Verification

## Objective

Secure, real-time registration where:
- OTP is sent **only** to Telegram Bot
- User enters OTP **only** on the website
- Telegram identity is verified from Telegram (never from frontend)
- **One Telegram = One account** (no duplicate registrations)

---

## Security Rules

| Rule | Implementation |
|------|----------------|
| ❌ Never accept Telegram username from frontend for identity | Identity from OTP record only |
| ❌ Never trust website input for identity | Backend fetches from DB (populated by /start) |
| ❌ Never reuse OTP | Marked `used` after verification |
| ❌ Never allow one Telegram → multiple accounts | `website_registered_at` check |
| ✅ OTP expires automatically | 3 min TTL in Redis + DB |
| ✅ Backend validates everything | All checks server-side |

---

## Registration Flow

### 1. User on Website
- Opens iqromax.uz/register
- Clicks "Register via Telegram"
- Enters Telegram username (optional, for **routing only** – to know where to send OTP)

### 2. Backend: Send OTP
- **POST /api/v1/send-otp** with `telegram_username` (for routing)
- Backend looks up `telegram_id` from users who have /start'ed the bot
- Generates 6-digit OTP, saves with `telegram_id`, expiration, `used=false`
- Sends OTP to user via Telegram Bot

### 3. User Receives OTP in Telegram
- Must have pressed /start on bot before
- Message format: `🔐 Iqromax.uz ro'yxatdan o'tish kodi: {otp}`

### 4. User Enters OTP on Website
- Inputs OTP into form, clicks Verify

### 5. Backend: Verify OTP
- **POST /api/v1/verify-otp** with **only** `{ "otp": "492817" }`
- Backend looks up `telegram_id` from OTP record (not from request)
- Verifies: OTP exists, not expired, not used
- Duplicate check: if `telegram_id` already has `website_registered_at` → block
- Creates account: sets `website_registered_at`, returns `telegram_id`, `telegram_username`, `first_name`

---

## API Endpoints

### POST /api/v1/send-otp
**Request:** `{ "telegram_username": "johndoe" }` (username for routing only)
**Response:** `{ "success": true, "data": { "expires_in": 180 } }`

### POST /api/v1/verify-otp
**Request:** `{ "otp": "492817" }` (only field – no telegram_id/username)
**Response:** `{ "success": true, "data": { "telegram_id": 123, "telegram_username": "johndoe", "first_name": "John" } }`

**Errors:**
- `already_registered` – This Telegram account is already registered
- `otp_not_found` – Wrong or expired OTP
- `otp_expired` – OTP has expired
- `max_attempts` – Too many wrong attempts

---

## Database

- **users**: Bot users + website accounts. `website_registered_at` = completed registration (One Telegram = One Account).
- **otp_requests**: OTP linked to `user_id` (→ telegram_id). Hash stored, not plain code.
- **Redis**: `otp:code:{code}` → `{telegram_id}` for verify-by-code-only lookup.

### Migration (existing DB)
Run `scripts/migrate-website-registered.sql` to add `website_registered_at` column.

---

## Test Cases

| Scenario | Expected |
|----------|----------|
| Wrong OTP | ❌ Blocked |
| Expired OTP | ❌ Blocked |
| Same Telegram tries again | ❌ Blocked (`already_registered`) |
| Correct OTP + new Telegram | ✅ Success |
| Username from frontend used for identity | ❌ Never – only for routing |

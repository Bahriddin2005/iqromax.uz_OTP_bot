# iqromax.uz OTP Bot - API Documentation

## Overview

Bu API iqromax.uz web saytida foydalanuvchilarni Telegram orqali tasdiqlash uchun ishlatiladi.

**Base URL:** `https://api.iqromax.uz/api/v1`

**Content-Type:** `application/json`

---

## Authentication

Barcha API so'rovlarida `X-API-Key` header talab qilinadi.

```http
X-API-Key: your-api-secret-key
```

Admin endpointlar uchun qo'shimcha `X-Admin-ID` header ham kerak:

```http
X-Admin-ID: 123456789
```

---

## Rate Limiting

| Limit Type | Value | Description |
|------------|-------|-------------|
| Per Hour | 5 requests | Bitta foydalanuvchi uchun soatiga maksimal OTP so'rovlar |
| Cooldown | 60 seconds | OTP so'rovlar orasidagi minimal vaqt |
| Brute Force | 5 attempts | Muvaffaqiyatsiz urinishlardan keyin 15 daqiqa bloklash |

Rate limit xatolari `429 Too Many Requests` status code bilan qaytariladi.

---

## Endpoints

### 1. Send OTP

Foydalanuvchiga OTP kod yuborish.

**Endpoint:** `POST /send-otp`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `telegram_id` | integer | No* | Foydalanuvchining Telegram ID si |
| `telegram_username` | string | No* | Telegram username (@ siz) |
| `name` | string | No | Foydalanuvchi ismi |
| `phone` | string | No | Telefon raqami |
| `source` | string | No | So'rov manbasi (default: "web_registration") |

*`telegram_id` yoki `telegram_username` dan biri majburiy.

**Example Request:**

```bash
curl -X POST https://api.iqromax.uz/api/v1/send-otp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "telegram_id": 123456789,
    "name": "John Doe",
    "source": "web_registration"
  }'
```

**Success Response (200):**

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

**Error Responses:**

| Status | Code | Description |
|--------|------|-------------|
| 400 | `missing_identifier` | telegram_id yoki telegram_username kerak |
| 400 | `invalid_username` | Noto'g'ri username formati |
| 403 | `user_blocked` | Foydalanuvchi bloklangan |
| 404 | `user_not_found` | Foydalanuvchi topilmadi (bot ishga tushirilmagan) |
| 429 | `cooldown` | Cooldown davri (retry_after ko'rsatiladi) |
| 429 | `rate_limit` | Rate limit oshib ketdi |
| 500 | `message_send_failed` | Telegram xabar yuborilmadi |

---

### 2. Verify OTP

OTP kodni tasdiqlash.

**Endpoint:** `POST /verify-otp`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `telegram_id` | integer | No* | Foydalanuvchining Telegram ID si |
| `telegram_username` | string | No* | Telegram username |
| `otp` | string | Yes | 6 xonali OTP kod |

**Example Request:**

```bash
curl -X POST https://api.iqromax.uz/api/v1/verify-otp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "telegram_id": 123456789,
    "otp": "482917"
  }'
```

**Success Response (200):**

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

**Error Responses:**

| Status | Code | Description |
|--------|------|-------------|
| 400 | `invalid_otp_format` | OTP formati noto'g'ri |
| 400 | `invalid_otp` | OTP kod noto'g'ri (remaining_attempts ko'rsatiladi) |
| 400 | `otp_expired` | OTP muddati tugagan |
| 404 | `otp_not_found` | Faol OTP topilmadi |
| 429 | `max_attempts` | Maksimal urinishlar tugadi |
| 429 | `locked_out` | Brute force himoyasi |

---

### 3. Resend OTP

OTP kodni qayta yuborish (avvalgi kod bekor qilinadi).

**Endpoint:** `POST /resend-otp`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `telegram_id` | integer | No* | Telegram ID |
| `telegram_username` | string | No* | Telegram username |
| `source` | string | No | So'rov manbasi |

**Example Request:**

```bash
curl -X POST https://api.iqromax.uz/api/v1/resend-otp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "telegram_id": 123456789
  }'
```

Response `/send-otp` bilan bir xil.

---

### 4. Get OTP Status

Joriy OTP holatini tekshirish.

**Endpoint:** `GET /otp-status/{telegram_id}`

**Example Request:**

```bash
curl https://api.iqromax.uz/api/v1/otp-status/123456789 \
  -H "X-API-Key: your-api-key"
```

**Success Response (200):**

```json
{
  "success": true,
  "message": "OTP holati",
  "code": "status",
  "data": {
    "request_id": 42,
    "status": "pending",
    "attempts": 1,
    "max_attempts": 3,
    "remaining_attempts": 2,
    "expires_in_seconds": 120,
    "created_at": "2024-01-15T10:27:00Z"
  }
}
```

---

### 5. Health Check

Tizim holatini tekshirish.

**Endpoint:** `GET /health`

**Example Request:**

```bash
curl https://api.iqromax.uz/api/v1/health
```

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "telegram_bot": "running"
  }
}
```

---

## Admin Endpoints

Admin endpointlar uchun `X-Admin-ID` header majburiy.

### Get Statistics

**Endpoint:** `GET /admin/statistics`

```bash
curl https://api.iqromax.uz/api/v1/admin/statistics \
  -H "X-API-Key: your-api-key" \
  -H "X-Admin-ID: 123456789"
```

### List Users

**Endpoint:** `GET /admin/users`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Sahifa raqami |
| `per_page` | integer | 20 | Har sahifada |
| `search` | string | - | Qidiruv |
| `status_filter` | string | all | active/blocked/all |

### Block User

**Endpoint:** `POST /admin/users/{telegram_id}/block`

### Unblock User

**Endpoint:** `POST /admin/users/{telegram_id}/unblock`

---

## Error Response Format

Barcha xatolar quyidagi formatda qaytariladi:

```json
{
  "success": false,
  "message": "Human-readable error message",
  "code": "error_code",
  "details": {
    "additional": "info"
  }
}
```

---

## Code Examples

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_URL = 'https://api.iqromax.uz/api/v1';
const API_KEY = 'your-api-key';

// Send OTP
async function sendOTP(telegramId, name) {
  try {
    const response = await axios.post(`${API_URL}/send-otp`, {
      telegram_id: telegramId,
      name: name,
      source: 'web_registration'
    }, {
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Error:', error.response?.data);
    throw error;
  }
}

// Verify OTP
async function verifyOTP(telegramId, otp) {
  try {
    const response = await axios.post(`${API_URL}/verify-otp`, {
      telegram_id: telegramId,
      otp: otp
    }, {
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Error:', error.response?.data);
    throw error;
  }
}
```

### Python

```python
import requests

API_URL = 'https://api.iqromax.uz/api/v1'
API_KEY = 'your-api-key'

headers = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
}

# Send OTP
def send_otp(telegram_id: int, name: str = None):
    response = requests.post(
        f'{API_URL}/send-otp',
        json={
            'telegram_id': telegram_id,
            'name': name,
            'source': 'web_registration'
        },
        headers=headers
    )
    return response.json()

# Verify OTP
def verify_otp(telegram_id: int, otp: str):
    response = requests.post(
        f'{API_URL}/verify-otp',
        json={
            'telegram_id': telegram_id,
            'otp': otp
        },
        headers=headers
    )
    return response.json()
```

### PHP

```php
<?php
$apiUrl = 'https://api.iqromax.uz/api/v1';
$apiKey = 'your-api-key';

function sendOTP($telegramId, $name = null) {
    global $apiUrl, $apiKey;
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, "$apiUrl/send-otp");
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'X-API-Key: ' . $apiKey,
        'Content-Type: application/json'
    ]);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
        'telegram_id' => $telegramId,
        'name' => $name,
        'source' => 'web_registration'
    ]));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    
    $response = curl_exec($ch);
    curl_close($ch);
    
    return json_decode($response, true);
}

function verifyOTP($telegramId, $otp) {
    global $apiUrl, $apiKey;
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, "$apiUrl/verify-otp");
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'X-API-Key: ' . $apiKey,
        'Content-Type: application/json'
    ]);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
        'telegram_id' => $telegramId,
        'otp' => $otp
    ]));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    
    $response = curl_exec($ch);
    curl_close($ch);
    
    return json_decode($response, true);
}
?>
```

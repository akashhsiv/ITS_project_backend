
# Business Registration & Authentication Flow – Rista Apps

This document outlines the full authentication flow for businesses registering and accessing the Rista Apps platform.

---

## 📌 1. Business Registration

**Endpoint:**  
`POST /businesses/`

**Process:**
- Business fills out registration form.
- System generates:
  - `account_number` (8-digit)
  - `device_key` (e.g. `DCXXXXXX`)
  - `user_id` (e.g. `UZ1234`)
  - `pin` (4-digit)
- `is_active` is set to `False`.
- An **activation email** is sent with:
  - Activate Account Link
  - Device Key & Expiry
  - User ID & PIN

---

## ✅ 2. Account Activation

**Link inside email:**  
`GET /api/activate/<activation_token>/`

**Process:**
- Token expires after 24 hours (`activation_token_expires`).
- If valid:
  - Sets `is_active = True`
  - Clears `activation_token` and `activation_token_expires`
  - Sends welcome email again with credentials

---

## 🔐 3. Device Registration

**Endpoint:**  
`POST /businesses/register_device/`

**Payload:**
```json
{
  "device_registration_key": "DCXXXXXX",
  "pin": "1234"
}
```

**Response:**
- Validates against `device_key` and `pin`
- Returns:
  - Email, User ID, PIN, and Device Key

> ⚠️ `device_key` is valid only for 7 days (`device_key_expires`)

---

## 🔁 4. Reset Device Key

**Endpoint:**  
`POST /businesses/reset_device/`

**Payload:**
```json
{
  "account_number": 12345678,
  "email": "example@domain.com"
}
```

**Process:**
- Verifies the business by `account_number` and `email`
- Regenerates `device_key` and `device_key_expires`
- Sends new credentials to email

---

## 🔑 5. Forgot PIN Flow

**Endpoint 1:**  
`POST /businesses/forgot_pin/`

**Payload:**
```json
{
  "email": "example@domain.com"
}
```

**Process:**
- Generates `forgot_pin_token` and `forgot_pin_token_expires`
- Sends email with reset link:  
  `GET /api/forgot_pin/confirm/<token>/`

**Endpoint 2 (confirmation):**  
`GET /api/forgot_pin/confirm/<token>/`

**Process:**
- If token is valid (within 24 hours):
  - Generates new `pin`
  - Clears forgot PIN token fields
  - Sends new PIN via email

---

## 🔓 6. Login with PIN

**Endpoint:**  
`POST /businesses/login_with_pin/`

**Payload:**
```json
{
  "user_id": "UZXXXX",
  "pin": "1234"
}
```

**Response:**
- Verifies credentials and returns business info

---

## 🧠 Security Notes

- All tokens have expirations
- PINs are only sent via secure email
- `device_key` is valid for 7 days and then must be reset
- Separate tokens are used for:
  - Account activation
  - Forgot PIN

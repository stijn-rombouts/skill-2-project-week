# 2FA Testing Guide

## Overview
Your application now has a complete 2FA (Two-Factor Authentication) management system using TOTP (Time-based One-Time Password).

## How to Access 2FA Settings

1. **Login** to your application with any user account
2. **Open the navigation drawer** (hamburger menu)
3. Scroll to the **"Account"** section
4. Click **"Two-Factor Auth"**

## Testing the 2FA Setup

### Step 1: Generate Secret
- On the 2FA page, click **"Generate 2FA Secret"**
- The app will generate a unique TOTP secret and display a QR code

### Step 2: Download an Authenticator App
Choose one of these free apps:
- **Google Authenticator** (iOS/Android)
- **Microsoft Authenticator** (iOS/Android)
- **Authy** (iOS/Android/Desktop)
- **FreeOTP** (iOS/Android)

### Step 3: Scan the QR Code
- Open your authenticator app
- Scan the QR code displayed on the 2FA page
- Or manually enter the secret shown below the QR code

### Step 4: Verify with Code
- Your authenticator app will show a 6-digit code that refreshes every 30 seconds
- Enter this code in the **"Verify Code"** input
- Click **"Verify & Enable 2FA"**

### Step 5: Test Login with 2FA
1. **Logout** from the application
2. **Login again** with your username and password
3. You'll be redirected to the **2FA verification page**
4. Enter the 6-digit code from your authenticator app
5. If correct, you'll be fully logged in

## Disabling 2FA

Once 2FA is enabled, you can disable it by:
1. Going to the 2FA settings page
2. Clicking the **"Disable 2FA"** expansion section
3. Entering your 6-digit code
4. Clicking **"Disable 2FA"**

## Testing via API (cURL)

### Login without 2FA
```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=patient1&password=password123"
```

### Generate 2FA Secret
```bash
curl -X GET http://localhost:8000/api/2fa/enable \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Verify 2FA Setup
```bash
curl -X POST http://localhost:8000/api/2fa/verify-setup \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456", "secret": "YOUR_SECRET"}'
```

### Login with 2FA Enabled
```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=patient1&password=password123"
# Returns: {"requires_2fa": true, "token_2fa": "..."}
```

### Complete 2FA Login
```bash
curl -X POST http://localhost:8000/api/2fa/verify-login \
  -H "Content-Type: application/json" \
  -d '{"code": "123456", "token_2fa": "TOKEN_FROM_LOGIN"}'
```

### Disable 2FA
```bash
curl -X POST http://localhost:8000/api/2fa/disable \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'
```

## Troubleshooting

### "Invalid code" Error
- Make sure you're using the current 6-digit code
- Codes refresh every 30 seconds
- Check that your device clock is synchronized

### "2FA token expired"
- The 2FA token is only valid for 5 minutes
- You'll need to login again if it expires

### QR Code Not Scanning
- Use the manual entry option (secret is shown below the QR code)
- Copy the secret and manually enter it in your authenticator app

## Files Modified

### Frontend
- **Created**: `src/pages/TwoFactorAuthPage.vue` - 2FA management UI
- **Updated**: `src/router/routes.js` - Added 2FA route
- **Updated**: `src/layouts/MainLayout.vue` - Added 2FA navigation link
- **Updated**: `src/stores/auth-store.js` - Added setToken() and setUser() methods

### Backend
- **Updated**: `main.py`
  - Changed `/api/2fa/enable` from POST to GET
  - Updated `/api/me` to include `is_2fa_enabled` field

## Features

✅ Generate TOTP secrets with QR code
✅ Scan QR code or manual entry
✅ Verify setup with 6-digit code
✅ Enable/disable 2FA
✅ Login with 2FA protection
✅ Time-based code generation (TOTP)
✅ 5-minute token expiration for added security
✅ Works with any standard TOTP app

# Multi-Factor Authentication (MFA) Implementation Guide

This document details the Multi-Factor Authentication (MFA) mechanism currently implemented in the `mini_bank_system`. It covers the chosen approach, the technical flow, the design decisions made, and alternative approaches.

## Chosen Approach: Time-Based One-Time Password (TOTP)

The current implementation utilizes **TOTP (Time-Based One-Time Password)**, defined in RFC 6238. This is the standard used by authenticator apps like Google Authenticator, Authy, and Microsoft Authenticator.

### Why TOTP?
- **Security:** Tokens are generated offline on the user's device, making it immune to SIM swapping (unlike SMS).
- **Cost-Effective:** No recurring costs for sending SMS or emails.
- **Reliability:** Works without an internet connection or cellular signal on the client side.

### Technical Stack
- **Library:** `pyotp` is used to generate the base32 secrets, build provisioning URIs (for QR codes), and verify the 6-digit tokens.
- **Storage:** The `User` model in SQLAlchemy stores the `mfa_secret` (the base32 string) and an `mfa_enabled` boolean flag.

---

## Technical Flow

### 1. Setup Phase
When a user wishes to enable MFA, they call `POST /api/v1/auth/mfa/setup`.
- **Backend Action:** Generates a random base32 secret using `pyotp.random_base32()`.
- **Response:** Returns the secret and a `totp_uri`. The frontend uses this URI to generate a QR Code (e.g., using `qrcode.react`) that the user scans with their authenticator app.
- **State:** At this point, the secret is stored in the DB, but `mfa_enabled` remains `False`.

### 2. Verification / Activation Phase
The user must prove they successfully scanned the code by providing a valid 6-digit token to `POST /api/v1/auth/mfa/verify`.
- **Backend Action:** Uses `pyotp.TOTP(secret).verify(token)` to check the token.
- **State Change:** If valid, `mfa_enabled` is flipped to `True`. The setup is complete.

### 3. Login Flow with MFA
Once MFA is enabled, the login flow changes slightly to become a **two-step process**:
1. **First Step (`POST /login`)**: The user provides their email and password. Instead of returning a full access token, the backend returns a **temporary JWT** (valid for 5 minutes) with a special claim (`"mfa": "pending"`). The response includes `"mfa_required": True`.
2. **Second Step (`POST /mfa/verify`)**: The client prompts the user for their 6-digit code. It sends this code along with the temporary JWT as a Bearer token. The backend verifies the token and the TOTP code, and finally issues the full `access_token` and `refresh_token`.

> [!NOTE]
> **Design Decision: The Temporary JWT**
> We use a temporary JWT between the first and second login steps to keep the API entirely stateless. Instead of using server-side sessions (e.g., Redis) to remember that the user successfully completed step 1, the temporary token cryptographically proves that the password was verified.

---

## Alternative MFA Approaches

While TOTP is a robust choice, several other approaches exist. Below is a comparison to help understand the trade-offs.

### 1. WebAuthn / FIDO2 (Passkeys or Hardware Keys)
Uses public key cryptography to authenticate users via hardware tokens (YubiKey) or device biometrics (Apple FaceID, Windows Hello).
- **Pros:** The most secure option available. Phishing-resistant. Passkeys offer an incredible user experience.
- **Cons:** Complex to implement (requires handling challenging cryptographic challenges on both client and server).
- **When to choose:** For highly sensitive applications (like banking core infrastructure) or when prioritizing a frictionless, passwordless user experience.

### 2. SMS / Voice Call OTP
Sends a 6-digit code to the user's registered phone number.
- **Pros:** Very familiar to users; requires no additional app installation.
- **Cons:** Vulnerable to SIM swapping and SS7 attacks. Costs money per message. Delivery can be delayed by carrier issues.
- **When to choose:** When targeting a user base that is non-technical and may struggle with authenticator apps. *(Note: NIST recently deprecated SMS as an out-of-band authenticator).*

### 3. Email OTP
Sends a one-time link or code to the user's email address (Magic Links).
- **Pros:** Easy to implement, users are familiar with it, no extra apps needed.
- **Cons:** If the user's email is compromised (which is often the case in credential stuffing), the MFA is useless.
- **When to choose:** As a low-friction fallback method, or for less sensitive systems where convenience overrides strict security.

### 4. Push Notifications
A mobile app receives a push notification asking the user to tap "Approve" or "Deny".
- **Pros:** Excellent user experience, very low friction.
- **Cons:** Requires the bank to have its own dedicated mobile application installed on the user's phone with push services (APNs/FCM) configured. Vulnerable to "MFA Fatigue" attacks where attackers spam prompts until the user accidentally clicks approve.
- **When to choose:** When you have a dedicated mobile app and want to offer a premium, seamless security experience.

> [!TIP]
> **Future Recommendation**
> For a banking system, upgrading to **WebAuthn (Passkeys)** alongside TOTP is highly recommended. It significantly mitigates phishing risks, which are the primary vector for banking compromises today.

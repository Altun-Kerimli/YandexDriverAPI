# Driver Profile API (Yandex Driver Portal)

This repo provides a starter API and local testing page for letting taxi drivers update their profile data
(for example, a car number). The intended flow mirrors a Yandex-hosted service: a driver authenticates with
their phone number, receives a short verification code, then receives a session token used to read/update
their profile.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/> to use the local testing page.

## API flow

1. **Request OTP**: `POST /auth/request` with `{ "phone_number": "+79990001122" }`.
2. **Verify OTP**: `POST /auth/verify` with `{ "verification_id": "...", "code": "0000" }`.
3. **Update profile**: `PATCH /drivers/me` with `Authorization: Bearer <session_token>`.

The current implementation is intentionally minimal and uses in-memory storage so you can wire it
to your real Yandex driver API later.

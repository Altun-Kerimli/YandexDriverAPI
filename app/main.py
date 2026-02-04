from datetime import datetime, timedelta
from typing import Dict, Optional
import secrets

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Driver Profile API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DriverProfile(BaseModel):
    driver_id: str
    full_name: str
    phone_number: str
    car_number: str
    car_model: Optional[str] = None
    updated_at: datetime


class AuthRequest(BaseModel):
    phone_number: str = Field(..., example="+79990001122")


class AuthVerify(BaseModel):
    verification_id: str
    code: str = Field(..., example="0000")


class AuthResponse(BaseModel):
    session_token: str
    expires_at: datetime


class DriverUpdate(BaseModel):
    car_number: Optional[str] = None
    car_model: Optional[str] = None
    full_name: Optional[str] = None


class DriverResponse(BaseModel):
    driver: DriverProfile


class VerificationRecord(BaseModel):
    verification_id: str
    phone_number: str
    created_at: datetime


class SessionRecord(BaseModel):
    session_token: str
    driver_id: str
    expires_at: datetime


DRIVERS: Dict[str, DriverProfile] = {
    "driver-001": DriverProfile(
        driver_id="driver-001",
        full_name="Aleksei Petrov",
        phone_number="+79990001122",
        car_number="A001AA77",
        car_model="Hyundai Solaris",
        updated_at=datetime.utcnow(),
    )
}
PHONE_TO_DRIVER = {"+79990001122": "driver-001"}
VERIFICATIONS: Dict[str, VerificationRecord] = {}
SESSIONS: Dict[str, SessionRecord] = {}


def get_session(authorization: Optional[str]) -> SessionRecord:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    session = SESSIONS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if session.expires_at < datetime.utcnow():
        del SESSIONS[token]
        raise HTTPException(status_code=401, detail="Session token expired")
    return session


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Driver Profile Test Console</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      body { font-family: sans-serif; margin: 2rem; max-width: 760px; }
      section { border: 1px solid #ddd; padding: 1rem; margin-bottom: 1rem; }
      label { display: block; margin-top: 0.5rem; }
      input { padding: 0.4rem; width: 100%; max-width: 360px; }
      button { margin-top: 0.8rem; padding: 0.5rem 1rem; }
      pre { background: #f6f6f6; padding: 1rem; }
    </style>
  </head>
  <body>
    <h1>Driver Profile Test Console</h1>
    <p>Use this local page to test the API flow before deploying to a Yandex-hosted domain.</p>
    <section>
      <h2>1. Request OTP</h2>
      <label>Phone number</label>
      <input id="phone" value="+79990001122" />
      <button onclick="requestOtp()">Request OTP</button>
      <pre id="requestResult"></pre>
    </section>
    <section>
      <h2>2. Verify OTP</h2>
      <label>Verification ID</label>
      <input id="verificationId" />
      <label>Code</label>
      <input id="code" value="0000" />
      <button onclick="verifyOtp()">Verify</button>
      <pre id="verifyResult"></pre>
    </section>
    <section>
      <h2>3. Update profile</h2>
      <label>Session token</label>
      <input id="sessionToken" />
      <label>Car number</label>
      <input id="carNumber" value="A777AA77" />
      <label>Car model</label>
      <input id="carModel" value="Toyota Camry" />
      <button onclick="updateProfile()">Update</button>
      <pre id="updateResult"></pre>
    </section>
    <script>
      async function requestOtp() {
        const phone = document.getElementById('phone').value;
        const res = await fetch('/auth/request', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone_number: phone })
        });
        document.getElementById('requestResult').textContent = await res.text();
      }
      async function verifyOtp() {
        const verificationId = document.getElementById('verificationId').value;
        const code = document.getElementById('code').value;
        const res = await fetch('/auth/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ verification_id: verificationId, code })
        });
        const text = await res.text();
        document.getElementById('verifyResult').textContent = text;
        try {
          const data = JSON.parse(text);
          document.getElementById('sessionToken').value = data.session_token;
        } catch (err) {
          console.warn('Unable to parse response', err);
        }
      }
      async function updateProfile() {
        const token = document.getElementById('sessionToken').value;
        const carNumber = document.getElementById('carNumber').value;
        const carModel = document.getElementById('carModel').value;
        const res = await fetch('/drivers/me', {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ car_number: carNumber, car_model: carModel })
        });
        document.getElementById('updateResult').textContent = await res.text();
      }
    </script>
  </body>
</html>
"""


@app.post("/auth/request")
def request_auth(body: AuthRequest) -> VerificationRecord:
    verification_id = secrets.token_urlsafe(8)
    record = VerificationRecord(
        verification_id=verification_id,
        phone_number=body.phone_number,
        created_at=datetime.utcnow(),
    )
    VERIFICATIONS[verification_id] = record
    return record


@app.post("/auth/verify", response_model=AuthResponse)
def verify_auth(body: AuthVerify) -> AuthResponse:
    record = VERIFICATIONS.get(body.verification_id)
    if not record:
        raise HTTPException(status_code=400, detail="Unknown verification id")
    if body.code != "0000":
        raise HTTPException(status_code=400, detail="Invalid code")
    driver_id = PHONE_TO_DRIVER.get(record.phone_number)
    if not driver_id:
        raise HTTPException(status_code=404, detail="Driver not found")
    session_token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    SESSIONS[session_token] = SessionRecord(
        session_token=session_token,
        driver_id=driver_id,
        expires_at=expires_at,
    )
    return AuthResponse(session_token=session_token, expires_at=expires_at)


@app.get("/drivers/me", response_model=DriverResponse)
def get_profile(authorization: Optional[str] = Header(default=None)) -> DriverResponse:
    session = get_session(authorization)
    driver = DRIVERS.get(session.driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return DriverResponse(driver=driver)


@app.patch("/drivers/me", response_model=DriverResponse)
def update_profile(
    update: DriverUpdate, authorization: Optional[str] = Header(default=None)
) -> DriverResponse:
    session = get_session(authorization)
    driver = DRIVERS.get(session.driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    updates = update.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    new_driver = driver.model_copy(update=updates)
    new_driver.updated_at = datetime.utcnow()
    DRIVERS[session.driver_id] = new_driver
    return DriverResponse(driver=new_driver)

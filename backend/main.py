from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, time
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from email.mime.text import MIMEText
import smtplib
import os
from dotenv import load_dotenv
from jose import JWTError

load_dotenv()

from database import init_db, get_db, User, Role, Medication, MedicationIntake
from auth import (authenticate_user,
    create_access_token,
    create_2fa_token,      
    verify_2fa_token,     
    generate_totp_secret,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
    get_totp_provisioning_uri,
    verify_totp_code,
)

app = FastAPI()

# --------------------
# Pydantic Models
# --------------------
class Verify2FASetupRequest(BaseModel):
    code: str
    secret: str

class Verify2FALoginRequest(BaseModel):
    code: str
    token_2fa: str

class Disable2FARequest(BaseModel):
    code: str

class RemoveOldAccount2FARequest(BaseModel):
    code: str

# Add CORS middleware BEFORE other middleware and routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------
# Scheduler + Missed-med notifications
# --------------------
scheduler = BackgroundScheduler()
notified_missed_medications = set()  # Track which missed meds we've already notified about

check_missed_medications_interval = 20  # seconds
check_missed_medications_grace_period = 5  # minutes


def send_alert_email(to_email: str, patient_name: str, medication_name: str) -> bool:
    """Send an alert email to the caregiver about a missed medication."""
    subject = f"LET OP: {patient_name} heeft medicatie nog niet ingenomen"

    body = (
        f"Dag,\n\n"
        f"Dit is een herinnering voor {patient_name}.\n\n"
        f"De medicatie '{medication_name}' is nog niet als 'ingenomen' gemeld.\n"
        f"Controleer of de medicatie alsnog ingenomen kan worden.\n\n"
        f"Tijdstip melding: {datetime.now().strftime('%H:%M')}"
    )

    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")

    if not sender or not password:
        print("❌ EMAIL_ADDRESS / EMAIL_PASSWORD missing in environment.")
        return False

    try:
        msg = MIMEText(body)
        msg["Subject"], msg["From"], msg["To"] = subject, sender, to_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        print(f"✅ Email successfully sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email failed to {to_email}: {e}")
        return False


def check_missed_medications():
    """Check for medications that should have been taken but weren't."""
    db = next(get_db())

    try:
        now = datetime.now()
        today = now.date()
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_name = day_names[now.weekday()]

        medications = db.query(Medication).filter(Medication.is_active == True).all()

        for medication in medications:
            if not medication.schedule:
                continue

            if today_name not in medication.schedule:
                continue

            day_schedule = medication.schedule[today_name]
            if not day_schedule.get("enabled"):
                continue

            times = day_schedule.get("times") or []
            for time_str in times:
                try:
                    hours, minutes = map(int, time_str.split(":"))
                    scheduled_dt = datetime.combine(today, time(hours, minutes))

                    time_diff = now - scheduled_dt
                    if not (timedelta(minutes=check_missed_medications_grace_period) <= time_diff <= timedelta(minutes=10)):
                        continue

                    intake = (
                        db.query(MedicationIntake)
                        .filter(
                            MedicationIntake.medication_id == medication.id,
                            MedicationIntake.patient_id == medication.patient_id,
                            MedicationIntake.scheduled_time == time_str,
                            MedicationIntake.taken_at >= datetime.combine(today, time(0, 0)),
                        )
                        .first()
                    )

                    notification_key = f"{medication.id}_{medication.patient_id}_{today.isoformat()}_{time_str}"

                    if intake:
                        continue

                    if notification_key in notified_missed_medications:
                        continue

                    patient = db.query(User).filter(User.id == medication.patient_id).first()
                    caregiver = patient.caregiver if patient else None

                    if patient:
                        print(
                            f"[MISSED MEDICATION ALERT] Patient: {patient.username}, "
                            f"Medication: {medication.name} ({medication.dosage}), "
                            f"Scheduled time: {time_str}, Current time: {now.strftime('%H:%M')}"
                        )

                    if caregiver and caregiver.email and patient:
                        print(f"📧 Sending alert email to {caregiver.email}")
                        send_alert_email(caregiver.email, patient.username, medication.name)
                    else:
                        if patient:
                            print(f"⚠️ No caregiver email found for patient {patient.username}")

                    notified_missed_medications.add(notification_key)

                except ValueError:
                    # skip invalid time formats
                    continue

        # Cleanup old notification keys (older than ~24h)
        yesterday = (now - timedelta(days=1)).date()
        for key in list(notified_missed_medications):
            try:
                parts = key.split("_")
                # expected: medicationId_patientId_YYYY-MM-DD_HH:MM
                if len(parts) < 4:
                    continue
                key_date = datetime.fromisoformat(parts[2]).date()
                if key_date < yesterday:
                    notified_missed_medications.discard(key)
            except Exception:
                continue

    finally:
        db.close()


# --------------------
# App lifecycle
# --------------------
@app.on_event("startup")
async def startup_event():
    """Initialize database + start scheduler + seed roles/users."""
    init_db()

    scheduler.add_job(check_missed_medications, "interval", seconds=check_missed_medications_interval)
    scheduler.start()
    print("Missed medication checker started")

    db = next(get_db())
    try:
        # Roles
        mantelzorger_role = db.query(Role).filter(Role.name == "mantelzorger").first()
        if not mantelzorger_role:
            mantelzorger_role = Role(name="mantelzorger")
            db.add(mantelzorger_role)
            db.commit()
            db.refresh(mantelzorger_role)

        patient_role = db.query(Role).filter(Role.name == "patient").first()
        if not patient_role:
            patient_role = Role(name="patient")
            db.add(patient_role)
            db.commit()
            db.refresh(patient_role)

        zorgverlener_role = db.query(Role).filter(Role.name == "zorgverlener").first()
        if not zorgverlener_role:
            zorgverlener_role = Role(name="zorgverlener")
            db.add(zorgverlener_role)
            db.commit()
            db.refresh(zorgverlener_role)

        # Default users
        mantelzorger1 = db.query(User).filter(User.username == "mantelzorger1").first()
        if not mantelzorger1:
            mantelzorger1 = User(
                username="mantelzorger1",
                email="jarne.bouamoud@hotmail.com",
                hashed_password=get_password_hash("password123"),
                role_id=mantelzorger_role.id,
            )
            db.add(mantelzorger1)
            db.commit()
            db.refresh(mantelzorger1)

        patient1 = db.query(User).filter(User.username == "patient1").first()
        if not patient1:
            patient1 = User(
                username="patient1",
                hashed_password=get_password_hash("password123"),
                role_id=patient_role.id,
                caregiver_id=mantelzorger1.id,
            )
            db.add(patient1)
            db.commit()

        zorgverlener1 = db.query(User).filter(User.username == "zorgverlener1").first()
        if not zorgverlener1:
            zorgverlener1 = User(
                username="zorgverlener1",
                hashed_password=get_password_hash("password123"),
                role_id=zorgverlener_role.id,
            )
            db.add(zorgverlener1)
            db.commit()

        print("Database initialized with default roles and users")
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("Scheduler stopped")


# --------------------
# Basic
# --------------------
@app.get("/")
async def root():
    return {"message": "Hello World"}


# --------------------
# Auth endpoints
# --------------------
@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint - returns 2FA token if 2FA is enabled"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if 2FA is enabled
    if user.is_2fa_enabled:
        # Return 2FA token instead of full access token
        token_2fa_expires = timedelta(minutes=5)
        token_2fa = create_2fa_token(
            data={"sub": user.username}, expires_delta=token_2fa_expires
        )
        return {
            "requires_2fa": True,
            "token_2fa": token_2fa,
            "username": user.username
        }
    
    # Normal login if 2FA not enabled
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role.name
    }


@app.get("/api/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.name,
        "is_2fa_enabled": current_user.is_2fa_enabled
    }


# --------------------
# Patient schedule
# --------------------
@app.get("/api/patient_schedule")
async def get_patient_schedule(current_user: User = Depends(get_current_user)):
    if current_user.role.name != "patient":
        raise HTTPException(status_code=403, detail="Only patients can access their medication schedule")

    medications = current_user.medications
    schedule = []
    for med in medications:
        if med.is_active:
            schedule.append(
                {
                    "name": med.name,
                    "dosage": med.dosage,
                    "schedule": med.schedule,
                    "notes": med.notes,
                }
            )

    return {"medication_schedule": schedule}


# --------------------
# Caregiver: patients
# --------------------
@app.get("/api/patients")
async def get_patients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can view patients")

    patients = db.query(User).filter(User.role.has(Role.name == "patient")).all()
    return [{"id": p.id, "username": p.username} for p in patients]


# --------------------
# Pydantic models
# --------------------
class MedicationCreate(BaseModel):
    name: str
    dosage: str
    schedule: dict
    notes: Optional[str] = None


class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    dosage: Optional[str] = None
    schedule: Optional[dict] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class MedicationResponse(BaseModel):
    id: int
    name: str
    dosage: str
    schedule: dict
    start_date: datetime
    end_date: Optional[datetime] = None
    notes: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# --------------------
# Medication endpoints
# --------------------
@app.post("/api/patients/{patient_id}/medications", response_model=MedicationResponse)
async def create_medication(
    patient_id: int,
    medication: MedicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can add medications")

    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    db_medication = Medication(
        patient_id=patient_id,
        name=medication.name,
        dosage=medication.dosage,
        schedule=medication.schedule,
        notes=medication.notes,
    )
    db.add(db_medication)
    db.commit()
    db.refresh(db_medication)
    return db_medication


@app.get("/api/patients/{patient_id}/medications", response_model=List[MedicationResponse])
async def get_patient_medications(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    return medications


@app.get("/api/medications/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    return medication


@app.put("/api/medications/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: int,
    medication_update: MedicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can update medications")

    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")

    if medication_update.name is not None:
        medication.name = medication_update.name
    if medication_update.dosage is not None:
        medication.dosage = medication_update.dosage
    if medication_update.schedule is not None:
        medication.schedule = medication_update.schedule
    if medication_update.notes is not None:
        medication.notes = medication_update.notes
    if medication_update.is_active is not None:
        medication.is_active = medication_update.is_active

    db.commit()
    db.refresh(medication)
    return medication


@app.delete("/api/medications/{medication_id}")
async def delete_medication(
    medication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can delete medications")

    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")

    db.delete(medication)
    db.commit()
    return {"message": "Medication deleted successfully"}


# --------------------
# Medication intake endpoints
# --------------------
class MedicationIntakeCreate(BaseModel):
    medication_name: str
    scheduled_time: str
    status: Optional[str] = "taken"
    notes: Optional[str] = None


class MedicationIntakeResponse(BaseModel):
    id: int
    medication_id: int
    patient_id: int
    scheduled_time: str
    taken_at: datetime
    status: str
    notes: Optional[str] = None
    medication_name: str

    class Config:
        from_attributes = True


@app.post("/api/medication_intakes", response_model=MedicationIntakeResponse)
async def record_medication_intake(
    intake: MedicationIntakeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "patient":
        raise HTTPException(status_code=403, detail="Only patients can record medication intake")

    medication = (
        db.query(Medication)
        .filter(
            Medication.patient_id == current_user.id,
            Medication.name == intake.medication_name,
            Medication.is_active == True,
        )
        .first()
    )
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")

    db_intake = MedicationIntake(
        medication_id=medication.id,
        patient_id=current_user.id,
        scheduled_time=intake.scheduled_time,
        status=intake.status,
        notes=intake.notes,
    )
    db.add(db_intake)
    db.commit()
    db.refresh(db_intake)

    return MedicationIntakeResponse(
        id=db_intake.id,
        medication_id=db_intake.medication_id,
        patient_id=db_intake.patient_id,
        scheduled_time=db_intake.scheduled_time,
        taken_at=db_intake.taken_at,
        status=db_intake.status,
        notes=db_intake.notes,
        medication_name=medication.name,
    )


@app.get("/api/medication_intakes", response_model=List[MedicationIntakeResponse])
async def get_medication_intakes(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "patient":
        raise HTTPException(status_code=403, detail="Only patients can view their intake history")

    query = db.query(MedicationIntake).filter(MedicationIntake.patient_id == current_user.id)

    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.filter(MedicationIntake.taken_at >= start_dt)

    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.filter(MedicationIntake.taken_at <= end_dt)

    intakes = query.order_by(MedicationIntake.taken_at.desc()).all()

    response: List[MedicationIntakeResponse] = []
    for intake in intakes:
        medication = db.query(Medication).filter(Medication.id == intake.medication_id).first()
        response.append(
            MedicationIntakeResponse(
                id=intake.id,
                medication_id=intake.medication_id,
                patient_id=intake.patient_id,
                scheduled_time=intake.scheduled_time,
                taken_at=intake.taken_at,
                status=intake.status,
                notes=intake.notes,
                medication_name=medication.name if medication else "Unknown",
            )
        )

    return response


@app.get("/api/patients/{patient_id}/medication_intakes", response_model=List[MedicationIntakeResponse])
async def get_patient_medication_intakes(
    patient_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can view patient intake history")

    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    query = db.query(MedicationIntake).filter(MedicationIntake.patient_id == patient_id)

    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.filter(MedicationIntake.taken_at >= start_dt)

    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.filter(MedicationIntake.taken_at <= end_dt)

    intakes = query.order_by(MedicationIntake.taken_at.desc()).all()

    response: List[MedicationIntakeResponse] = []
    for intake in intakes:
        medication = db.query(Medication).filter(Medication.id == intake.medication_id).first()
        response.append(
            MedicationIntakeResponse(
                id=intake.id,
                medication_id=intake.medication_id,
                patient_id=intake.patient_id,
                scheduled_time=intake.scheduled_time,
                taken_at=intake.taken_at,
                status=intake.status,
                notes=intake.notes,
                medication_name=medication.name if medication else "Unknown",
            )
        )

    return response


# --------------------
# 2FA endpoints (FIXED)
# --------------------
@app.get("/api/2fa/enable")
async def enable_2fa(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generate TOTP secret for 2FA setup"""
    if current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    secret = generate_totp_secret()
    provisioning_uri = get_totp_provisioning_uri(secret, current_user.username)

    # NOTE: For best security, store secret in a 'pending' field server-side and only accept code in verify.
    return {"secret": secret, "provisioning_uri": provisioning_uri, "qr_code": provisioning_uri}


@app.post("/api/2fa/verify-setup")
async def verify_2fa_setup(
    request: Verify2FASetupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify TOTP code and enable 2FA"""
    if current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    if not verify_totp_code(request.secret, request.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    current_user.totp_secret = request.secret
    current_user.is_2fa_enabled = True
    db.commit()

    return {"message": "2FA enabled successfully"}


@app.post("/api/2fa/disable")
async def disable_2fa(
    request: Disable2FARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disable 2FA with verification"""
    if not current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA secret missing")

    if not verify_totp_code(current_user.totp_secret, request.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    db.commit()

    return {"message": "2FA disabled successfully"}


@app.post("/api/2fa/verify-login")
async def verify_2fa_login(
    request: Verify2FALoginRequest,
    db: Session = Depends(get_db)
):
    """Complete 2FA login with TOTP code"""
    try:
        payload = verify_2fa_token(request.token_2fa)
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid 2FA token")

    if not username:
        raise HTTPException(status_code=401, detail="Invalid 2FA token payload")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_2fa_enabled or not user.totp_secret:
        raise HTTPException(status_code=401, detail="2FA not enabled for user")

    if not verify_totp_code(user.totp_secret, request.code):
        raise HTTPException(status_code=401, detail="Invalid code")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role.name
    }


@app.post("/api/2fa/remove-old-account")
async def remove_old_2fa_account(
    request: RemoveOldAccount2FARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove old linked account from authenticator app - requires current TOTP code verification"""
    if not current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled. No old account to remove.")

    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA secret not found")

    if not verify_totp_code(current_user.totp_secret, request.code):
        raise HTTPException(status_code=400, detail="Invalid code. Could not verify current 2FA account.")

    # Clear the old secret and disable 2FA temporarily to allow re-setup
    # This allows the user to remove the old account from their authenticator app
    # and set up a fresh one for better structure
    current_user.totp_secret = None
    current_user.is_2fa_enabled = False
    db.commit()

    return {
        "message": "Old 2FA account has been removed. You can now set up a fresh account.",
        "status": "removed"
    }

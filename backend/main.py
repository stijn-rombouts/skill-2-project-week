from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from pydantic import BaseModel
from typing import Optional
from email.mime.text import MIMEText
import smtplib
import os
from dotenv import load_dotenv
from database import init_db, get_db, User, Role, Medication
from auth import (
    authenticate_user, 
    create_access_token, 
    get_password_hash, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)

load_dotenv()

app = FastAPI()

# Add CORS middleware BEFORE other middleware and routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()
    db = next(get_db())
    try:
        # 1. Rollen aanmaken
        m_role = db.query(Role).filter(Role.name == "mantelzorger").first()
        if not m_role:
            m_role = Role(name="mantelzorger")
            db.add(m_role); db.commit(); db.refresh(m_role)

        p_role = db.query(Role).filter(Role.name == "patient").first()
        if not p_role:
            p_role = Role(name="patient")
            db.add(p_role); db.commit(); db.refresh(p_role)

        # 2. Mantelzorger aanmaken MET e-mail
        m1 = db.query(User).filter(User.username == "mantelzorger1").first()
        if not m1:
            m1 = User(
                username="mantelzorger1",
                email="jarne.bouamoud@hotmail.com",
                hashed_password=get_password_hash("password123"),
                role_id=m_role.id
            )
            db.add(m1); db.commit(); db.refresh(m1)

        # 3. Patiënt aanmaken EN KOPPELEN aan mantelzorger
        p1 = db.query(User).filter(User.username == "patient1").first()
        if not p1:
            p1 = User(
                username="patient1",
                hashed_password=get_password_hash("password123"),
                role_id=p_role.id,
                caregiver_id=m1.id  # <--- DIT IS DE CRUCIALE KOPPELING
            )
            db.add(p1); db.commit(); db.refresh(p1)

        # 4. Test medicatie aanmaken (zodat ID 1 altijd bestaat)
        med1 = db.query(Medication).filter(Medication.id == 1).first()
        if not med1:
            med1 = Medication(
                patient_id=p1.id,
                name="test medicatie",
                dosage="1 pil",
                schedule={"monday": {"enabled": True, "times": ["08:00"]}}
            )
            db.add(med1); db.commit()

        print("✅ Database succesvol gereset, gekoppeld en gevuld!")
    finally:
        db.close()

notification_schedule = []

def generate_notification_schedule():
    global notification_schedule
    # Generate the notification schedule, scheduled every 20 seconds for 1 hour
    from datetime import datetime, timedelta
    now = datetime.now()
    notification_schedule = []
    for i in range(180):
        notification_time = now + timedelta(seconds=20 * (i + 1))
        notification_schedule.append({
            "time": notification_time.strftime("%H:%M:%S"),
            "timestamp": notification_time.isoformat(),
            "message": f"Notification {i + 1} at {notification_time.strftime('%H:%M:%S')}"
        })

# Email Send Function
def send_alert_email(to_email: str, patient_name: str, medication_name: str):
    subject = f"ALERT: {patient_name} missed their medication"
    body = f"Hello,\n\nThis is an automated alert. {patient_name} has not confirmed taking their '{medication_name}' as scheduled.\n\nSent: {datetime.now().strftime('%H:%M:%S')}"
    
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")

    try:
        msg = MIMEText(body)
        msg['Subject'], msg['From'], msg['To'] = subject, sender, to_email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/api/check")
async def check():
    return True

# Schedule for notifications
@app.get("/api/schedule_notification")
async def schedule_notification():    
    return {"schedule": notification_schedule}

# Endpoint to clear the schedule (for testing purposes)
@app.post("/api/clear_schedule")
async def clear_schedule():
    global notification_schedule
    notification_schedule = []
    return {"message": "Schedule cleared"}

@app.post("/api/generate_schedule")
async def regenerate_schedule():
    generate_notification_schedule()
    return {"message": "Schedule regenerated"}


# Authentication endpoints
@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint that returns a JWT token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
    """Get current user information (protected route example)"""
    return {
        "username": current_user.username,
        "role": current_user.role.name
    }


@app.get("/api/patients")
async def get_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all patients (mantelzorger only)"""
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can view patients")
    
    patients = db.query(User).filter(
        User.role.has(Role.name == "patient")
    ).all()
    
    return [{"id": p.id, "username": p.username} for p in patients]


# Medication Pydantic Models
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


# Medication Endpoints
@app.post("/api/patients/{patient_id}/medications", response_model=MedicationResponse)
async def create_medication(
    patient_id: int,
    medication: MedicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new medication for a patient (mantelzorger only)"""
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can add medications")
    
    # Verify patient exists
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db_medication = Medication(
        patient_id=patient_id,
        name=medication.name,
        dosage=medication.dosage,
        schedule=medication.schedule,
        notes=medication.notes
    )
    db.add(db_medication)
    db.commit()
    db.refresh(db_medication)
    return db_medication


@app.get("/api/patients/{patient_id}/medications", response_model=list[MedicationResponse])
async def get_patient_medications(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all medications for a patient"""
    # Verify patient exists
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    return medications


@app.get("/api/medications/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific medication"""
    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    return medication


@app.put("/api/medications/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: int,
    medication_update: MedicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a medication (mantelzorger only)"""
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can update medications")
    
    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    if medication_update.name:
        medication.name = medication_update.name
    if medication_update.dosage:
        medication.dosage = medication_update.dosage
    if medication_update.schedule:
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
    current_user: User = Depends(get_current_user)
):
    """Delete a medication (mantelzorger only)"""
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can delete medications")
    
    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    db.delete(medication)
    db.commit()
    return {"message": "Medication deleted successfully"}

@app.post("/api/medications/{medication_id}/missed")
async def report_missed_medication(medication_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    print(f"🔔 API ONTVANGEN: Missed call voor ID {medication_id}")
    
    med = db.query(Medication).filter(Medication.id == medication_id).first()
    if not med:
        print(f"❌ FOUT: Medicijn {medication_id} niet gevonden in DB")
        raise HTTPException(status_code=404, detail="Medication not found")

    patient = med.patient
    caregiver = patient.caregiver 

    if caregiver and caregiver.email:
        print(f"📧 EMAIL TRIGGER: Sturen naar {caregiver.email}")
        background_tasks.add_task(send_alert_email, caregiver.email, patient.username, med.name)
        return {"status": "Alert sent"}
    
    print("⚠️ WAARSCHUWING: Geen caregiver of e-mail gevonden in DB voor deze patient")
    return {"status": "No caregiver email found"}
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from pydantic import BaseModel
from typing import Optional

from database import init_db, get_db, User, Role, Medication
from auth import (
    authenticate_user, 
    create_access_token, 
    get_password_hash, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)

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
    """Initialize database and create default data on startup"""
    init_db()
    
    # Create a database session
    db = next(get_db())
    
    try:
        # Check if roles exist, if not create them
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
        
        # Check if default users exist, if not create them
        mantelzorger1 = db.query(User).filter(User.username == "mantelzorger1").first()
        if not mantelzorger1:
            mantelzorger1 = User(
                username="mantelzorger1",
                hashed_password=get_password_hash("password123"),  # Default password
                role_id=mantelzorger_role.id
            )
            db.add(mantelzorger1)
            db.commit()
        
        patient1 = db.query(User).filter(User.username == "patient1").first()
        if not patient1:
            patient1 = User(
                username="patient1",
                hashed_password=get_password_hash("password123"),  # Default password
                role_id=patient_role.id
            )
            db.add(patient1)
            db.commit()
        
        zorgverlener1 = db.query(User).filter(User.username == "zorgverlener1").first()
        if not zorgverlener1:
            zorgverlener1 = User(
                username="zorgverlener1",
                hashed_password=get_password_hash("password123"),  # Default password
                role_id=zorgverlener_role.id
            )
            db.add(zorgverlener1)
            db.commit()
        
        print("Database initialized with default roles and users")
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
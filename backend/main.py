from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from pydantic import BaseModel

from database import init_db, get_db, User, Role, Medication
from auth import (
    authenticate_user, 
    create_access_token, 
    get_password_hash, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)
from medication_checker import check_missed_medications, mark_medication_taken, get_patient_medications

app = FastAPI()

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


# Pydantic models for medication endpoints
class MedicationCreate(BaseModel):
    name: str
    scheduled_time: str  # Format: "HH:MM"


class MedicationResponse(BaseModel):
    id: int
    name: str
    scheduled_time: str
    taken: bool
    date: datetime
    
    class Config:
        from_attributes = True


# Medication endpoints
@app.post("/api/medications/create")
async def create_medication(
    med: MedicationCreate,
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a medication reminder (mantelzorger only)
    """
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only mantelzorgers can create medications")
    
    # Check if user is the mantelzorger for this patient
    patient = db.query(User).filter(User.id == patient_id).first()
    if not patient or patient.mantelzorger_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this patient")
    
    medication = Medication(
        user_id=patient_id,
        name=med.name,
        scheduled_time=med.scheduled_time,
        date=datetime.utcnow()
    )
    db.add(medication)
    db.commit()
    db.refresh(medication)
    
    return MedicationResponse.from_orm(medication)


@app.get("/api/medications/{patient_id}")
async def get_medications(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get medications for a patient
    """
    meds = get_patient_medications(db, patient_id)
    return [MedicationResponse.from_orm(m) for m in meds]


@app.post("/api/medications/{medication_id}/taken")
async def medication_taken(
    medication_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a medication as taken (patient only)
    """
    if current_user.role.name != "patient":
        raise HTTPException(status_code=403, detail="Only patients can mark medications as taken")
    
    med = db.query(Medication).filter(Medication.id == medication_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    if med.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    mark_medication_taken(db, medication_id)
    
    return {"message": "Medication marked as taken"}


@app.post("/api/check-missed-medications")
async def check_missed(db: Session = Depends(get_db)):
    """
    Check for missed medications and send emails to mantelzorgers
    This should be called by a scheduler
    """
    check_missed_medications(db)
    return {"message": "Medication check completed"}
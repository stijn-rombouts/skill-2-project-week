from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, time
from pydantic import BaseModel
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, get_db, User, Role, Medication, MedicationIntake
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

# Initialize scheduler for checking missed medications
scheduler = BackgroundScheduler()
notified_missed_medications = set()  # Track which missed medications we've already notified about
check_missed_medications_interval = 20  # seconds
check_missed_medications_grace_period = 1  # minutes


def check_missed_medications():
    """Check for medications that should have been taken but weren't"""
    db = next(get_db())
    
    try:
        now = datetime.now()
        today = now.date()
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        today_name = day_names[now.weekday()]
        
        # Get all active medications
        medications = db.query(Medication).filter(Medication.is_active == True).all()
        
        for medication in medications:
            # Check if medication has a schedule for today
            if medication.schedule and today_name in medication.schedule:
                day_schedule = medication.schedule[today_name]
                
                if day_schedule.get('enabled') and day_schedule.get('times'):
                    for time_str in day_schedule['times']:
                        # Parse scheduled time
                        try:
                            hours, minutes = map(int, time_str.split(':'))
                            scheduled_datetime = datetime.combine(today, time(hours, minutes))
                            
                            # Check if 5 minutes have passed since scheduled time
                            time_diff = now - scheduled_datetime
                            if timedelta(minutes=check_missed_medications_grace_period) <= time_diff <= timedelta(minutes=10):
                                # Check if medication was taken
                                intake = db.query(MedicationIntake).filter(
                                    MedicationIntake.medication_id == medication.id,
                                    MedicationIntake.patient_id == medication.patient_id,
                                    MedicationIntake.scheduled_time == time_str,
                                    MedicationIntake.taken_at >= datetime.combine(today, time(0, 0))
                                ).first()
                                
                                # Create unique key for this missed medication
                                notification_key = f"{medication.id}_{medication.patient_id}_{today}_{time_str}"
                                
                                if not intake and notification_key not in notified_missed_medications:
                                    # Medication was missed!
                                    patient = db.query(User).filter(User.id == medication.patient_id).first()
                                    
                                    print(f"[MISSED MEDICATION ALERT] Patient: {patient.username}, "
                                          f"Medication: {medication.name} ({medication.dosage}), "
                                          f"Scheduled time: {time_str}, Current time: {now.strftime('%H:%M')}")
                                    
                                    # TODO: Send email notification here
                                    # send_email(
                                    #     to=patient.email,
                                    #     subject=f"Missed Medication: {medication.name}",
                                    #     body=f"You missed your {medication.name} scheduled at {time_str}"
                                    # )
                                    
                                    # Mark as notified
                                    notified_missed_medications.add(notification_key)
                        
                        except ValueError:
                            continue  # Skip invalid time formats
        
        # Clean up old notification keys (older than 24 hours)
        yesterday = (now - timedelta(days=1)).date()
        notified_missed_medications_copy = notified_missed_medications.copy()
        for key in notified_missed_medications_copy:
            try:
                # Key format: medication_id_patient_id_date_time
                parts = key.split('_')
                if len(parts) >= 3:
                    key_date_str = '_'.join(parts[2:-1])  # Get date part
                    key_date = datetime.strptime(key_date_str, '%Y-%m-%d').date()
                    if key_date < yesterday:
                        notified_missed_medications.discard(key)
            except:
                continue
    
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    """Initialize database and create default data on startup"""
    init_db()
    
    # Start the scheduler for checking missed medications
    scheduler.add_job(check_missed_medications, 'interval', seconds=check_missed_medications_interval)
    scheduler.start()
    print("Missed medication checker started")
    
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


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    scheduler.shutdown()
    print("Scheduler stopped")


@app.get("/")
async def root():
    return {"message": "Hello World"}


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
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.name
    }


@app.get("/api/patient_schedule")
async def get_patient_schedule(current_user: User = Depends(get_current_user)):
    """Get the medication schedule for the current patient"""
    if current_user.role.name != "patient":
        raise HTTPException(status_code=403, detail="Only patients can access their medication schedule")
    
    medications = current_user.medications
    schedule = []
    for med in medications:
        if med.is_active:
            schedule.append({
                "name": med.name,
                "dosage": med.dosage,
                "schedule": med.schedule,
                "notes": med.notes
            })
    
    return {"medication_schedule": schedule}


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


# Medication Intake Endpoints
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
    current_user: User = Depends(get_current_user)
):
    """Record that a patient has taken (or skipped) a medication"""
    if current_user.role.name != "patient":
        raise HTTPException(status_code=403, detail="Only patients can record medication intake")
    
    # Find the medication by name for this patient
    medication = db.query(Medication).filter(
        Medication.patient_id == current_user.id,
        Medication.name == intake.medication_name,
        Medication.is_active == True
    ).first()
    
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    # Create intake record
    db_intake = MedicationIntake(
        medication_id=medication.id,
        patient_id=current_user.id,
        scheduled_time=intake.scheduled_time,
        status=intake.status,
        notes=intake.notes
    )
    db.add(db_intake)
    db.commit()
    db.refresh(db_intake)
    
    # Add medication name to response
    response_data = MedicationIntakeResponse(
        id=db_intake.id,
        medication_id=db_intake.medication_id,
        patient_id=db_intake.patient_id,
        scheduled_time=db_intake.scheduled_time,
        taken_at=db_intake.taken_at,
        status=db_intake.status,
        notes=db_intake.notes,
        medication_name=medication.name
    )
    
    return response_data


@app.get("/api/medication_intakes", response_model=list[MedicationIntakeResponse])
async def get_medication_intakes(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get medication intake history for the current patient"""
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
    
    # Build response with medication names
    response = []
    for intake in intakes:
        medication = db.query(Medication).filter(Medication.id == intake.medication_id).first()
        response.append(MedicationIntakeResponse(
            id=intake.id,
            medication_id=intake.medication_id,
            patient_id=intake.patient_id,
            scheduled_time=intake.scheduled_time,
            taken_at=intake.taken_at,
            status=intake.status,
            notes=intake.notes,
            medication_name=medication.name if medication else "Unknown"
        ))
    
    return response


@app.get("/api/patients/{patient_id}/medication_intakes", response_model=list[MedicationIntakeResponse])
async def get_patient_medication_intakes(
    patient_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get medication intake history for a specific patient (mantelzorger only)"""
    if current_user.role.name != "mantelzorger":
        raise HTTPException(status_code=403, detail="Only caregivers can view patient intake history")
    
    # Verify patient exists
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
    
    # Build response with medication names
    response = []
    for intake in intakes:
        medication = db.query(Medication).filter(Medication.id == intake.medication_id).first()
        response.append(MedicationIntakeResponse(
            id=intake.id,
            medication_id=intake.medication_id,
            patient_id=intake.patient_id,
            scheduled_time=intake.scheduled_time,
            taken_at=intake.taken_at,
            status=intake.status,
            notes=intake.notes,
            medication_name=medication.name if medication else "Unknown"
        ))
    
    return response
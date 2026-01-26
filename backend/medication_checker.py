"""
Medication Checker Service
Checks if elderly people have taken their medication and sends email reminders to mantelzorgers
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import Medication, User
from email_service import send_email


def check_missed_medications(db: Session):
    """
    Check for medications that were scheduled but not taken
    Send email reminders to corresponding mantelzorgers
    """
    
    # Get today's date
    today = datetime.utcnow().date()
    
    # Find all medications scheduled for today that haven't been taken
    missed_meds = db.query(Medication).filter(
        Medication.date >= datetime.combine(today, datetime.min.time()),
        Medication.date < datetime.combine(today + timedelta(days=1), datetime.min.time()),
        Medication.taken == False
    ).all()
    
    print(f"📋 Checking medications for {today}... Found {len(missed_meds)} missed medications")
    
    for med in missed_meds:
        patient = med.user
        mantelzorger = patient.mantelzorger
        
        if mantelzorger and mantelzorger.email:
            # Send email to mantelzorger
            subject = f"⚠️ Medicijn Herinnering - {patient.username}"
            body = f"""
Hallo,

{patient.username} heeft hun medicijn '{med.name}' nog niet ingeslikt vandaag.

Geplande tijd: {med.scheduled_time}
Datum: {today}

Graag nawees of het medicijn is ingeslikt.

Met vriendelijke groeten,
Medicijn Herinneringssysteem
            """
            
            send_email(mantelzorger.email, subject, body)
            print(f"✅ Email sent to {mantelzorger.email} for patient {patient.username}")
        else:
            print(f"⚠️ No mantelzorger email found for {patient.username}")


def mark_medication_taken(db: Session, medication_id: int):
    """
    Mark a medication as taken
    """
    med = db.query(Medication).filter(Medication.id == medication_id).first()
    if med:
        med.taken = True
        med.taken_at = datetime.utcnow()
        db.commit()
        print(f"✅ Medication {med.name} marked as taken for {med.user.username}")
        return True
    return False


def get_patient_medications(db: Session, patient_id: int, date=None):
    """
    Get all medications for a patient on a specific date
    """
    if date is None:
        date = datetime.utcnow().date()
    
    medications = db.query(Medication).filter(
        Medication.user_id == patient_id,
        Medication.date >= datetime.combine(date, datetime.min.time()),
        Medication.date < datetime.combine(date + timedelta(days=1), datetime.min.time())
    ).all()
    
    return medications

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.sqlite import JSON

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"))
    caregiver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 2FA columns
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)
    totp_secret = Column(String, nullable=True)
    
    role = relationship("Role", back_populates="users")
    medications = relationship("Medication", back_populates="patient")
    caregiver = relationship("User", remote_side="User.id", foreign_keys="User.caregiver_id", viewonly=True)


class Medication(Base):
    __tablename__ = "medications"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    schedule = Column(JSON, nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    patient = relationship("User", back_populates="medications")
    intakes = relationship("MedicationIntake", back_populates="medication")


class MedicationIntake(Base):
    __tablename__ = "medication_intakes"
    
    id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scheduled_time = Column(String, nullable=False)
    taken_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, default="taken", nullable=False)
    notes = Column(Text, nullable=True)
    
    medication = relationship("Medication", back_populates="intakes")
    patient = relationship("User")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
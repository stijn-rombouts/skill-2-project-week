from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

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
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    
    role = relationship("Role", back_populates="users")
    medications = relationship("Medication", back_populates="patient")


class Medication(Base):
    __tablename__ = "medications"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)  # e.g., "500mg", "2 tablets"
    schedule = Column(JSON, nullable=False)  # Weekly schedule: {day: {enabled: bool, times: [HH:MM, ...]}, ...}
    start_date = Column(DateTime, default=datetime.now, nullable=False)
    end_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    patient = relationship("User", back_populates="medications")
    intakes = relationship("MedicationIntake", back_populates="medication", cascade="all, delete-orphan")


class MedicationIntake(Base):
    __tablename__ = "medication_intakes"
    
    id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scheduled_time = Column(String, nullable=False)  # HH:MM format
    taken_at = Column(DateTime, default=datetime.now, nullable=False)
    status = Column(String, default="taken", nullable=False)  # "taken", "skipped", "missed"
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
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

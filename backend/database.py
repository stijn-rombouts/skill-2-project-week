from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime
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
    email = Column(String, unique=True, index=True, nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    
    role = relationship("Role", back_populates="users")
    # Patient can have one mantelzorger
    mantelzorger_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Mantelzorger can have multiple patients
    patients = relationship("User", remote_side=[id], backref="mantelzorger")
    medications = relationship("Medication", back_populates="user")


class Medication(Base):
    __tablename__ = "medications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    scheduled_time = Column(String, nullable=False)
    taken = Column(Boolean, default=False)
    taken_at = Column(DateTime, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="medications")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

from sqlalchemy import Integer, String, create_engine, Column, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from datetime import datetime, UTC
import os

DATABASE = os.getenv("DATABASE_URL" , "sqlite:///Expense.db")

engine = create_engine(DATABASE, echo=False)

sessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class Admin(Base):
    __tablename__ = "Admin_Details"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String(100), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
        }

class Employee(Base):
    __tablename__ = "Employee_Details"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    tasks = relationship("Task", back_populates="owner_rel") 
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email
        }

class Task(Base):
    __tablename__ = "Tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    priority = Column(String(20), default="medium")
    due_date = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.now(UTC).strftime("%Y-%m-%d"))
    owner_id = Column(Integer, ForeignKey("Employee_Details.id"), nullable=False)  
    owner_rel = relationship("Employee", back_populates="tasks")  
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "owner_id": self.owner_id
        }

class TokenBlacklist(Base):
    __tablename__ = "BlacklistedTokens"
    id = Column(Integer, primary_key=True)
    jti = Column(String, nullable=False, index=True, unique=True)
    created_at = Column(String)

Base.metadata.create_all(engine)

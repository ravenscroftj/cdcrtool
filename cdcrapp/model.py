from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import relationship

from sqlalchemy import Column, Integer, String, Text, Boolean, Table, ForeignKey, Float, DateTime

from datetime import datetime

Base = declarative_base()

    

class User(Base):
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password = Column(String(255))
    email = Column(String(255))
    tasks = relationship("Task", secondary="user_tasks")
    salt = Column(String(64))
    view_gsheets = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
class Task(Base):
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    hash = Column(String(64), unique=True)
    news_text = Column(Text)
    sci_text = Column(Text)
    news_url = Column(String(255))
    sci_url = Column(String(150))
    news_ent = Column(String(255))
    sci_ent = Column(String(255))
    similarity = Column(Float)
    is_iaa = Column(Boolean, default=False)
    is_bad = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class UserTask(Base):
    
    __tablename__ = "user_tasks"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), primary_key=True)
    
    answer = Column(String(150))
    
    task = relationship("Task", backref="usertasks")
    user = relationship("User", backref="usertasks")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
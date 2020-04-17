from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import relationship

from sqlalchemy import Column, Integer, String, Text, Boolean, Table, ForeignKey

Base = declarative_base()

user_tasks = Table("user_tasks", Base.metadata,
                   Column("user_id", Integer, ForeignKey("users.id")),
                   Column("task_id", Integer, ForeignKey("tasks.id"))
                   )
    

class User(Base):
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    password = Column(String(64))
    email = Column(String(255))
    tasks = relationship("Task", secondary=user_tasks)
    
    
class Task(Base):
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    hash = Column(String(64), unique=True)
    news_text = Column(Text)
    sci_text = Column(Text)
    news_url = Column(String(150))
    sci_url = Column(String(150))
    news_ent = Column(String(150))
    sci_ent = Column(String(150))
    is_iaa = Column(Boolean, default=False)
    is_bad = Column(Boolean, default=False)
    

class UserTask(Base):
    
    __tablename__ = "user_Tasks"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), primary_key=True)
    
    answer = Column(String(150))
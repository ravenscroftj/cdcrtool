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
    #news_text = Column(Text)
    #sci_text = Column(Text)
    #news_url = Column(String(255))
    #sci_url = Column(String(150))
    news_ent = Column(String(255))
    sci_ent = Column(String(255))
    similarity = Column(Float)
    # If set can be used in IAA calculations 
    is_iaa = Column(Boolean, default=False)
    # If set will be prioritised above "new" tasks by editor
    is_iaa_priority = Column(Boolean, default=False)
    is_bad = Column(Boolean, default=False)

    sci_paper_id = Column(ForeignKey("scipapers.id"))
    scipaper = relationship("SciPaper", lazy="joined")

    news_article_id = Column(ForeignKey("newsarticles.id"))
    newsarticle = relationship("NewsArticle", lazy="joined")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    @property
    def news_text(self):
        return self.newsarticle.summary
    
    @property
    def news_url(self):
        return self.newsarticle.url

    @property
    def sci_text(self):
        return self.scipaper.abstract

    @property
    def sci_url(self):
        return self.scipaper.url


class NewsArticle(Base):

    __tablename__ = "newsarticles"
    id = Column(Integer, primary_key=True)
    url = Column(String(255))
    summary = Column(Text)

class SciPaper(Base):

    __tablename__ = "scipapers"
    id = Column(Integer, primary_key=True)
    url = Column(String(150))
    abstract = Column(Text)


class UserTask(Base):
    
    __tablename__ = "user_tasks"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), primary_key=True)
    
    answer = Column(String(150))
    
    task = relationship("Task", backref="usertasks")
    user = relationship("User", backref="usertasks")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import relationship, backref

from sqlalchemy import Column, Integer, String, Text, Boolean, Table, ForeignKey, Float, DateTime

from datetime import datetime

from flask_security import RoleMixin, UserMixin, current_user

from collections import Counter

Base = declarative_base()


roles_users = Table('roles_users', Base.metadata,
        Column('user_id', Integer(), ForeignKey('users.id')),
        Column('role_id', Integer(), ForeignKey('roles.id')))



class Role(Base, RoleMixin):

    __tablename__ = "roles"

    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))


class User(Base, UserMixin):
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password = Column(String(255))
    email = Column(String(255))
    tasks = relationship("Task", secondary="user_tasks")
    salt = Column(String(64))
    view_gsheets = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

    roles = relationship('Role', secondary=roles_users,
                            backref=backref('users', lazy='dynamic'))

    active = Column(Boolean())
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    @property
    def total_annotations(self):
        return UserTask.query.filter(UserTask.user_id==self.id).count()
    
class Task(Base):
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    hash = Column(String(64), unique=True)
    news_ent = Column(String(255))
    sci_ent = Column(String(255))
    similarity = Column(Float)
    # If set can be used in IAA calculations 
    is_iaa = Column(Boolean, default=False)
    # If set will be prioritised above "new" tasks by editor
    is_iaa_priority = Column(Boolean, default=False)
    is_bad = Column(Boolean, default=False)
    is_bad_user_id = Column(ForeignKey("users.id"))
    is_bad_reason = Column(String(255))
    is_bad_reported_at = Column(DateTime, nullable=True)

    is_difficult = Column(Boolean, default=False)
    is_difficult_user_id = Column(ForeignKey("users.id"))
    is_difficult_reported_at = Column(DateTime, nullable=True)

    sci_paper_id = Column(ForeignKey("scipapers.id"))
    scipaper = relationship("SciPaper", lazy="joined")

    news_article_id = Column(ForeignKey("newsarticles.id"))
    newsarticle = relationship("NewsArticle", lazy="joined")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    priority = Column(Integer, default=0)

    _current_user_answer = None

    is_difficult_user = relationship("User", backref="difficult_tasks", foreign_keys=is_difficult_user_id)

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

    @property
    def current_user_answer(self):
        if self._current_user_answer is None:
            self._current_user_answer = UserTask.query.filter(UserTask.task_id==self.id, UserTask.user_id == current_user.id).one_or_none()
        
        return self._current_user_answer

    @property
    def news_ents(self):
        base_query = Task.query.filter(Task.news_article_id==self.news_article_id)
        return list(set([t.news_ent for t in base_query.all()]))

    @property
    def sci_ents(self):
        base_query = Task.query.filter(Task.sci_paper_id==self.sci_paper_id)
        return list(set([t.sci_ent for t in base_query.all()]))

    def get_best_answer(self):
        """Use votes to work out which answer is most appropriate"""
        
        votes = Counter([ut.answer for ut in self.usertasks])

        if len(votes) < 1:
            return None

        if votes['yes'] > votes['no']:
            return 'yes'
        else:
            return 'no'

        

    @property
    def related_answers(self):
        """Get all yes/no pairs for current user and news/sci doc"""
        q = UserTask.query.join(Task.usertasks).filter(Task.sci_paper_id==self.sci_paper_id,
            Task.news_article_id==self.news_article_id,
            UserTask.user_id==current_user.id, ~Task.is_bad)

        return [{"news_ent":ut.task.news_ent, "sci_ent":ut.task.sci_ent, "answer": ut.answer} for ut in q.all()]

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
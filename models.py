from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    notifications = relationship("Notification", back_populates="client")


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    message = Column(String)
    send_date = Column(DateTime)
    is_sent = Column(Boolean, default=False)
    client_id = Column(Integer, ForeignKey('users.id'))  # Связь с таблицей пользователей
    client = relationship("User", back_populates="notifications")  # Отношение с пользователем

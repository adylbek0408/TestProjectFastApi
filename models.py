# models.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    email = Column(String, nullable=True)
    telegram_id = Column(BigInteger, nullable=True)

    notifications = relationship("Notification", back_populates="client")

    def __str__(self):
        return f"{self.username} (ID: {self.id})"

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    message = Column(String)
    send_date = Column(DateTime(timezone=True), nullable=False)
    is_sent = Column(Boolean, default=False)
    client_id = Column(Integer, ForeignKey('users.id'))

    client = relationship("User", back_populates="notifications")

    def __str__(self):
        return f"{self.title} (ID: {self.id})"

import os
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from models import User, Notification, Base
from database import AsyncSessionLocal, engine
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from datetime import datetime

# Схемы для валидации данных
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    telegram_id: int

class NotificationCreate(BaseModel):
    title: str
    message: str
    send_date: datetime
    client_id: int

app = FastAPI(title="Selection Project")

# Инициализация базы данных
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Зависимость для получения сессии БД
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

# Аутентификация для админ-панели
class BasicAuthBackend(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if form["username"] == "admin" and form["password"] == "password":
            request.session.update({"token": "admin"})
            return True
        return False

    async def logout(self, request: Request) -> None:
        request.session.clear()

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("token") == "admin"

# Модели для админ-панели
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email, User.telegram_id]
    column_labels = {"username": "Username", "email": "Email", "telegram_id": "Telegram ID"}

class NotificationAdmin(ModelView, model=Notification):
    column_list = [Notification.id, Notification.title, Notification.send_date, Notification.is_sent, Notification.client]
    column_labels = {
        "title": "Title",
        "message": "Message",
        "send_date": "Send Date",
        "is_sent": "Is Sent",
        "client": "Client"
    }
    form_columns = [Notification.title, Notification.message, Notification.send_date, Notification.client]

# Инициализация админ-панели
secret_key = "supersecretkey"
admin = Admin(app, engine, authentication_backend=BasicAuthBackend(secret_key=secret_key))
admin.add_view(UserAdmin)
admin.add_view(NotificationAdmin)

# Маршрут для проверки работы
@app.get("/")
async def read_root():
    return {"message": "Hello, Admin Panel"}

if __name__ == "__main__":
    import asyncio
    import uvicorn
    asyncio.run(init_db())
    uvicorn.run(app, host="0.0.0.0", port=8000)

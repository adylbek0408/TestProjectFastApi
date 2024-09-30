import os
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from models import User, Notification, Base
from database import AsyncSessionLocal, engine
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from datetime import datetime

# Схема для создания пользователя
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    telegram_id: int

# Схема для создания уведомления
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

# Создаем зависимость для получения асинхронной сессии базы данных
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

# Обработчик для создания нового пользователя
@app.post("/users/")
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == user.email))
    db_user = result.scalar_one_or_none()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(username=user.username, email=user.email, password=user.password, telegram_id=user.telegram_id)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

# Обработчик для получения всех пользователей
@app.get("/users/")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users

# Обработчик для создания нового уведомления
@app.post("/notifications/")
async def create_notification(notification: NotificationCreate, db: AsyncSession = Depends(get_db)):
    new_notification = Notification(**notification.dict())
    db.add(new_notification)
    await db.commit()
    await db.refresh(new_notification)
    return new_notification

# Настройка аутентификации для админки
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

# Настройка модели User для админки
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email, User.telegram_id]
    column_labels = {"username": "Username", "email": "Email", "telegram_id": "Telegram ID"}

class NotificationAdmin(ModelView, model=Notification):
    column_list = [Notification.title, Notification.message, Notification.send_date, Notification.is_sent, Notification.client]
    column_labels = {
        "title": "Title",
        "message": "Message",
        "send_date": "Send Date",
        "is_sent": "Is Sent",
        "client": "Client"
    }
    form_columns = [Notification.title, Notification.message, Notification.send_date, Notification.client]

# Добавляем секретный ключ для аутентификации
secret_key = "supersecretkeythatshouldbesecret"

# Инициализация админки с секретным ключом
admin = Admin(app, engine, authentication_backend=BasicAuthBackend(secret_key=secret_key))

# Добавляем модель пользователя и уведомления в админку
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
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from models import User
from database import AsyncSessionLocal, engine
from sqladmin import Admin, ModelView
from models import User, Notification
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request


# Схема для создания пользователя
class UserCreate(BaseModel):
    username: str
    email: str
    password: str


app = FastAPI(title="Selection Project")


# Создаем зависимость для получения сессии базы данных
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


# Обработчик для создания нового пользователя
@app.post("/users/")
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == user.email))
    db_user = result.scalars().first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(username=user.username, email=user.email, password=user.password)
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


# Настройка аутентификации для админки
class BasicAuthBackend(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.foarm()
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
    column_list = [User.id, User.username, User.email]
    column_labels = {"username": "Username", "email": "Email"}


class NotificationAdmin(ModelView, model=Notification):
    column_list = [Notification.title, Notification.message, Notification.send_date, Notification.client]
    column_labels = {
        "title": "Title",
        "message": "Message",
        "send_date": "Send Date",
        "is_sent": "Is Sent",
        "client": "Client"  # Исправлено на "client"
    }
    form_columns = [Notification.title, Notification.message, Notification.send_date, Notification.client]


# Добавляем секретный ключ для аутентификации
secret_key = "supersecretkeythatshouldbesecret"

# Инициализация админки с секретным ключом
admin = Admin(app, engine=engine, authentication_backend=BasicAuthBackend(secret_key=secret_key))

# Добавляем модель пользователя и уведомления в админку
admin.add_view(UserAdmin)
admin.add_view(NotificationAdmin)


# Маршрут для проверки работы
@app.get("/")
async def read_root():
    return {"message": "Hello, Admin Panel"}

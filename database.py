import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка подключения к базе данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Если используем асинхронный движок, меняем URL на асинхронный протокол
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Создаем асинхронный движок
engine = create_async_engine(ASYNC_DATABASE_URL)

# Настройка сессии
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Базовый класс для всех моделей
Base = declarative_base()

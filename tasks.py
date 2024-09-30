# tasks.py
import os
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models import Notification, User
from datetime import datetime, timezone
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получение Telegram Bot Token из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Настройка Celery
celery_app = Celery('tasks')
celery_app.conf.broker_url = 'redis://redis:6379/0'
celery_app.conf.result_backend = 'redis://redis:6379/0'

# Настройка подключения к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL.replace('+asyncpg', ''))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Инициализация бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def send_telegram_message(chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except TelegramError as e:
        logger.error(f"Не удалось отправить сообщение в Telegram: {e}")
        return False

@celery_app.task
def check_and_send_notifications():
    logger.info("Начало проверки и отправки уведомлений")

    with SessionLocal() as session:
        current_time = datetime.now(timezone.utc)

        try:
            notifications = session.execute(
                select(Notification).filter(
                    Notification.send_date <= current_time,
                    Notification.is_sent == False
                )
            ).scalars().all()

            for notif in notifications:
                user = session.execute(select(User).filter(User.id == notif.client_id)).scalar_one_or_none()
                if user and user.telegram_id:
                    success = asyncio.run(send_telegram_message(
                        user.telegram_id,
                        f"{notif.title}\n\n{notif.message}"
                    ))
                    if success:
                        notif.is_sent = True
                        session.add(notif)
                        logger.info(f"Уведомление {notif.id} успешно отправлено пользователю {user.username}")
                    else:
                        logger.error(f"Не удалось отправить уведомление {notif.id} пользователю {user.username}")
                else:
                    logger.warning(f"Пользователь с ID {notif.client_id} не найден или не имеет Telegram ID")

            session.commit()
            logger.info("Все уведомления обработаны и база данных обновлена")
        except Exception as e:
            logger.error(f"Ошибка в задаче check_and_send_notifications: {str(e)}", exc_info=True)
            session.rollback()
            raise

    logger.info("Завершение проверки и отправки уведомлений")

# main.py (FastAPI приложение)
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from models import User, Notification
from sqladmin import Admin, ModelView
from datetime import datetime

app = FastAPI()

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email, User.telegram_id]

class NotificationAdmin(ModelView, model=Notification):
    column_list = [Notification.title, Notification.message, Notification.send_date, Notification.is_sent, Notification.client]
    form_columns = [Notification.title, Notification.message, Notification.send_date, Notification.client]

admin = Admin(app, engine)
admin.add_view(UserAdmin)
admin.add_view(NotificationAdmin)

# Здесь можно добавить дополнительные эндпоинты, если необходимо

# bot.py (Telegram бот)
from telegram.ext import Application, CommandHandler

async def start(update, context):
    await update.message.reply_text('Привет! Я бот для отправки уведомлений.')

async def check_notifications(update, context):
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Notification).join(User).filter(
                User.telegram_id == user_id,
                Notification.is_sent == False
            )
        )
        notifications = result.scalars().all()

        if notifications:
            for notification in notifications:
                await update.message.reply_text(f"Уведомление: {notification.title}\n\n{notification.message}")
                notification.is_sent = True
                session.add(notification)
            await session.commit()
            await update.message.reply_text("Все актуальные уведомления отправлены.")
        else:
            await update.message.reply_text("У вас нет новых уведомлений.")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('check_notifications', check_notifications))
    application.run_polling()

if __name__ == '__main__':
    main()
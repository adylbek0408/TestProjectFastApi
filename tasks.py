from celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Notification, User
from datetime import datetime
from telegram import Bot
import logging
import os
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка SQLAlchemy
engine = create_engine('postgresql://postgres:adminadmin@db/selection_project')
SessionLocal = sessionmaker(bind=engine)

# Получение Telegram Bot Token из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@celery_app.task
def check_and_send_notifications():
    asyncio.run(async_check_and_send_notifications())

async def async_check_and_send_notifications():
    logger.info("Starting check_and_send_notifications task")
    session = SessionLocal()
    current_time = datetime.utcnow()

    try:
        notifications = session.query(Notification).filter(
            Notification.send_date <= current_time,
            Notification.is_sent == False
        ).all()

        logger.info(f"Found {len(notifications)} notifications to send")

        for notification in notifications:
            # Получаем пользователя
            user = session.query(User).filter(User.id == notification.client_id).first()
            if user:
                try:
                    await bot.send_message(chat_id=user.telegram_id, text=f"{notification.title}\n\n{notification.message}")
                    notification.is_sent = True
                    session.add(notification)
                    logger.info(f"Notification {notification.id} sent successfully to {user.username}")
                except Exception as e:
                    logger.error(f"Error sending notification {notification.id} to {user.username}: {str(e)}")
            else:
                logger.warning(f"User with ID {notification.client_id} not found for notification {notification.id}")

        session.commit()
    except Exception as e:
        logger.error(f"Error in check_and_send_notifications task: {str(e)}")
        session.rollback()
    finally:
        session.close()

    logger.info("Finished check_and_send_notifications task")

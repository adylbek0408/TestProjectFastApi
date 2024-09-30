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
logger.info(f"Telegram Bot Token: {TELEGRAM_BOT_TOKEN[:5]}...{TELEGRAM_BOT_TOKEN[-5:]}")

# Настройка Celery
celery_app = Celery('tasks')
celery_app.conf.broker_url = 'redis://redis:6379/0'
celery_app.conf.result_backend = 'redis://redis:6379/0'

# Настройка синхронного подключения к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL.replace('+asyncpg', ''))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Инициализация бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def send_telegram_message(chat_id, text):
    try:
        logger.info(f"Attempting to send message to Telegram chat ID: {chat_id}")
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"Message sent successfully to chat ID: {chat_id}")
        return True
    except TelegramError as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


@celery_app.task
def check_and_send_notifications():
    logger.info("Starting check_and_send_notifications task")

    with SessionLocal() as session:
        current_time = datetime.now(timezone.utc)
        logger.info(f"Current time (UTC): {current_time}")

        try:
            all_notifications = session.execute(select(Notification)).scalars().all()
            logger.info(f"Total notifications in database: {len(all_notifications)}")

            for notif in all_notifications:
                logger.info(
                    f"Notification {notif.id}: title='{notif.title}', send_date={notif.send_date}, is_sent={notif.is_sent}")

                if notif.send_date <= current_time and not notif.is_sent:
                    logger.info(f"Notification {notif.id} is eligible for sending")
                    user = session.execute(select(User).filter(User.id == notif.client_id)).scalar_one_or_none()
                    if user and user.telegram_id:
                        success = asyncio.run(send_telegram_message(
                            user.telegram_id,
                            f"{notif.title}\n\n{notif.message}"
                        ))
                        if success:
                            notif.is_sent = True
                            session.add(notif)
                            logger.info(
                                f"Notification {notif.id} sent successfully to user {user.username} (Telegram ID: {user.telegram_id})")
                        else:
                            logger.error(
                                f"Failed to send notification {notif.id} to user {user.username} (Telegram ID: {user.telegram_id})")
                    else:
                        logger.warning(
                            f"User with ID {notif.client_id} not found or has no Telegram ID for notification {notif.id}")
                else:
                    if notif.is_sent:
                        logger.info(f"Notification {notif.id} is already sent")
                    else:
                        logger.info(f"Notification {notif.id} is scheduled for future: {notif.send_date}")

            session.commit()
            logger.info("All notifications processed and database updated")
        except Exception as e:
            logger.error(f"Error in check_and_send_notifications task: {str(e)}", exc_info=True)
            session.rollback()
            raise

    logger.info("Finished check_and_send_notifications task")


if __name__ == '__main__':
    celery_app.start()
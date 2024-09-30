# tasks.py

import os
import logging
from celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from models import Notification, User
from datetime import datetime, timezone
from telegram import Bot
from telegram.error import TelegramError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получение переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC")  # Синхронный URL базы данных

# Настройка синхронного двигателя и сессии SQLAlchemy
engine = create_engine(DATABASE_URL_SYNC, future=True)
Session = sessionmaker(bind=engine)

def send_telegram_message(chat_id, text):
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        bot.send_message(chat_id=chat_id, text=text)
        return True
    except TelegramError as e:
        logger.error(f"Ошибка отправки сообщения в Telegram: {e}")
        return False

@celery_app.task(name='check_and_send_notifications')
def check_and_send_notifications():
    logger.info("Запуск задачи check_and_send_notifications")
    with Session() as session:
        current_time = datetime.now(timezone.utc)
        logger.info(f"Текущее время (UTC): {current_time}")

        try:
            result = session.execute(select(Notification).filter(Notification.is_sent == False))
            notifications = result.scalars().all()
            logger.info(f"Всего ожидающих уведомлений: {len(notifications)}")

            for notif in notifications:
                logger.info(f"Обработка уведомления {notif.id}: {notif.title}")

                # Приводим notif.send_date к осведомлённому datetime
                if notif.send_date.tzinfo is None:
                    notif_send_date = notif.send_date.replace(tzinfo=timezone.utc)
                else:
                    notif_send_date = notif.send_date

                if notif_send_date <= current_time:
                    if notif.client_id is None:
                        logger.error(f"Уведомление {notif.id} не связано с пользователем (client_id is None)")
                        continue

                    user = session.get(User, notif.client_id)
                    if user and user.telegram_id:
                        success = send_telegram_message(
                            user.telegram_id,
                            f"{notif.title}\n\n{notif.message}"
                        )
                        if success:
                            notif.is_sent = True
                            session.commit()
                            logger.info(f"Уведомление {notif.id} отправлено пользователю {user.username}")
                        else:
                            logger.error(f"Не удалось отправить уведомление {notif.id} пользователю {user.username}")
                    else:
                        logger.warning(f"Пользователь {notif.client_id} не найден или не имеет telegram_id")
                else:
                    logger.info(f"Уведомление {notif.id} запланировано на будущее время: {notif.send_date}")
        except Exception as e:
            logger.error(f"Ошибка в check_and_send_notifications: {e}", exc_info=True)
    logger.info("Задача check_and_send_notifications завершена")

from celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Notification
from datetime import datetime
from bot import send_notification
import logging

engine = create_engine('postgresql://postgres:adminadmin@db/selection_project')
SessionLocal = sessionmaker(bind=engine)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@celery_app.task
def check_and_send_notifications():
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
            logger.info(f"Sending notification {notification.id} to client {notification.client_id}")
            try:
                send_notification(notification.client_id, notification.title, notification.message)
                notification.is_sent = True
                session.add(notification)
                logger.info(f"Notification {notification.id} sent successfully")
            except Exception as e:
                logger.error(f"Error sending notification {notification.id}: {str(e)}")

        session.commit()
    except Exception as e:
        logger.error(f"Error in check_and_send_notifications task: {str(e)}")
        session.rollback()
    finally:
        session.close()

    logger.info("Finished check_and_send_notifications task")

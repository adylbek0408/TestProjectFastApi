# bot.py

import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from models import User, Notification
from datetime import datetime, timezone

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # Асинхронный URL базы данных

# Настройка асинхронного двигателя и сессии SQLAlchemy
engine = create_async_engine(DATABASE_URL, future=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для уведомлений. Используйте команду /register для регистрации."
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with async_session() as session:
        user_id = update.effective_user.id
        username = update.effective_user.username
        if not username:
            await update.message.reply_text(
                "У вас не установлен username в Telegram. Пожалуйста, установите его и попробуйте снова."
            )
            return
        try:
            # Проверяем, зарегистрирован ли пользователь
            result = await session.execute(
                select(User).filter(User.telegram_id == user_id)
            )
            user = result.scalars().first()
            if user:
                await update.message.reply_text(
                    "Вы уже зарегистрированы. Если вы хотите обновить свою информацию, используйте команду /update_info."
                )
            else:
                # Создаём нового пользователя
                new_user = User(
                    username=username,
                    telegram_id=user_id
                )
                session.add(new_user)
                await session.commit()
                await update.message.reply_text("Регистрация успешна!")
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя: {e}", exc_info=True)
            await update.message.reply_text("Произошла ошибка при регистрации. Попробуйте позже.")

async def update_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with async_session() as session:
        user_id = update.effective_user.id
        new_username = update.effective_user.username
        if not new_username:
            await update.message.reply_text(
                "У вас не установлен username в Telegram. Пожалуйста, установите его и попробуйте снова."
            )
            return
        try:
            # Проверяем, зарегистрирован ли пользователь
            result = await session.execute(
                select(User).filter(User.telegram_id == user_id)
            )
            user = result.scalars().first()
            if user:
                old_username = user.username
                user.username = new_username
                await session.commit()
                await update.message.reply_text(f"Информация обновлена! Ваше имя пользователя изменено с '{old_username}' на '{new_username}'.")
            else:
                await update.message.reply_text(
                    "Вы не зарегистрированы. Используйте команду /register для регистрации."
                )
        except Exception as e:
            logger.error(f"Ошибка при обновлении информации пользователя: {e}", exc_info=True)
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

async def check_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with async_session() as session:
        current_time = datetime.now(timezone.utc)

        try:
            result = await session.execute(
                select(Notification)
                .join(User)
                .filter(
                    User.telegram_id == update.effective_user.id,
                    Notification.is_sent == False
                )
            )
            notifications = result.scalars().all()

            if not notifications:
                await update.message.reply_text("У вас нет новых уведомлений.")
                return

            notifications_sent = False
            future_notifications = []

            for notif in notifications:
                # Приводим notif.send_date к осведомлённому datetime
                if notif.send_date.tzinfo is None:
                    notif_send_date = notif.send_date.replace(tzinfo=timezone.utc)
                else:
                    notif_send_date = notif.send_date

                if notif_send_date <= current_time:
                    # Отправка уведомления пользователю
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"{notif.title}\n\n{notif.message}"
                    )
                    notif.is_sent = True
                    notifications_sent = True
                    await session.commit()
                else:
                    future_notifications.append(notif)

            if notifications_sent:
                await update.message.reply_text("Все новые уведомления отправлены.")
            elif future_notifications:
                await update.message.reply_text("У вас есть уведомления, запланированные на будущее время.")
            else:
                await update.message.reply_text("У вас нет новых уведомлений.")

        except Exception as e:
            logger.error(f"Ошибка при проверке уведомлений: {e}", exc_info=True)
            await update.message.reply_text("Произошла ошибка при проверке уведомлений.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('register', register))
    application.add_handler(CommandHandler('update_info', update_info))
    application.add_handler(CommandHandler('check_notifications', check_notifications))

    # Запуск бота
    application.run_polling()

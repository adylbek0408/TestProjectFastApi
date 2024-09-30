import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from dotenv import load_dotenv
from models import User, Notification, Base
from datetime import datetime, timezone

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение настроек из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаем асинхронную сессию
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Состояния разговора
USERNAME, EMAIL, PASSWORD = range(3)

async def get_async_session():
    async with AsyncSessionLocal() as session:
        yield session

async def check_existing_user(session: AsyncSession, telegram_id: int):
    result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def create_user(session: AsyncSession, username: str, email: str, password: str, telegram_id: int):
    result = await session.execute(select(User).filter(User.email == email))
    existing_email = result.scalar_one_or_none()

    if existing_email:
        raise ValueError("Пользователь с этим email уже существует")

    user = User(username=username, email=email, password=password, telegram_id=telegram_id)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Добро пожаловать! Используйте /register для регистрации или /check_notifications для проверки уведомлений.')

async def register(update: Update, context: CallbackContext) -> int:
    async with AsyncSessionLocal() as session:
        existing_user = await check_existing_user(session, update.effective_user.id)
        if existing_user:
            await update.message.reply_text(
                'Вы уже зарегистрированы. Если вы хотите обновить свою информацию, используйте команду /update_info.')
            return ConversationHandler.END
        else:
            await update.message.reply_text('Привет! Как тебя зовут?')
            return USERNAME

async def username(update: Update, context: CallbackContext) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text('Отлично! Теперь отправь мне свой email.')
    return EMAIL

async def email(update: Update, context: CallbackContext) -> int:
    context.user_data['email'] = update.message.text
    await update.message.reply_text('Теперь отправь мне свой пароль.')
    return PASSWORD

async def password(update: Update, context: CallbackContext) -> int:
    user_password = update.message.text
    async with AsyncSessionLocal() as session:
        try:
            await create_user(
                session,
                context.user_data['username'],
                context.user_data['email'],
                user_password,
                update.effective_user.id
            )
            await update.message.reply_text('Регистрация завершена. Спасибо!')
        except ValueError as e:
            await update.message.reply_text(f'Ошибка регистрации: {str(e)}')
        except Exception as e:
            await update.message.reply_text('Произошла ошибка при регистрации. Пожалуйста, попробуйте еще раз.')
            print(f"Полная ошибка: {e}")  # Для отладки
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Регистрация отменена.')
    return ConversationHandler.END

async def update_info(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Функция обновления информации пока не реализована.')

async def check_notifications(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        current_time = datetime.now(timezone.utc)
        result = await session.execute(
            select(Notification).join(User).filter(
                User.telegram_id == user_id,
                Notification.send_date <= current_time,
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

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('update_info', update_info))
    application.add_handler(CommandHandler('check_notifications', check_notifications))

    # Инициализация базы данных
    asyncio.get_event_loop().run_until_complete(init_db())

    application.run_polling()

if __name__ == '__main__':
    main()
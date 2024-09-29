import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from models import User
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from sqlalchemy.future import select

USERNAME, EMAIL, PASSWORD = range(3)


async def get_async_session():
    async with AsyncSessionLocal() as session:
        yield session


# Предполагаемая функция для создания пользователя
async def create_user(session: AsyncSession, username: str, email: str, password: str, telegram_id: int):
    user = User(username=username, email=email, password=password, telegram_id=telegram_id)
    session.add(user)
    await session.commit()


# Начало регистрации
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Добро пожаловать!')


# Регистрация
async def register(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Привет! Как тебя зовут?')
    return USERNAME


# Получение имени пользователя
async def username(update: Update, context: CallbackContext) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text('Отлично! Теперь отправь мне свой email.')
    return EMAIL


# Получение email
async def email(update: Update, context: CallbackContext) -> int:
    context.user_data['email'] = update.message.text
    await update.message.reply_text('Теперь отправь мне свой пароль.')
    return PASSWORD


# Получение пароля и завершение регистрации
async def password(update: Update, context: CallbackContext) -> int:
    user_password = update.message.text
    async for session in context.bot_data['session_factory']():
        try:
            await create_user(
                session,
                context.user_data['username'],
                context.user_data['email'],
                user_password,
                update.effective_user.id
            )
            await update.message.reply_text('Регистрация завершена. Спасибо!')
        except Exception as e:
            await update.message.reply_text(f'Ошибка регистрации: {str(e)}')
    return ConversationHandler.END


# Отмена регистрации
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Регистрация отменена.')
    return ConversationHandler.END


async def send_notification(client_id: int, title: str, message: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).filter(User.id == client_id))
        user = result.scalar_one_or_none()
        if user:
            try:
                await application.bot.send_message(chat_id=user.telegram_id, text=f"{title}\n\n{message}")
            except Exception as e:
                print(f"Ошибка отправки уведомления для пользователя {client_id}: {str(e)}")
                # Дополнительно можно записывать ошибку в логи
        else:
            print(f"Пользователь с ID {client_id} не найден.")


def main():
    global application
    token = '7897880750:AAEVpCvlPFu2qDTodl2nKX7dWmZ0IPFe5EQ'
    application = Application.builder().token(token).build()

    application.bot_data['session_factory'] = get_async_session

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
    application.run_polling()


if __name__ == '__main__':
    main()

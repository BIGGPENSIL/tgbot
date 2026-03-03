import logging
import os
import re

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)

# ====================== НАСТРОЙКИ ======================
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния (фамилии больше нет)
CHOICE, NAME, PHONE, TRANSPORT, MODEL, YEAR, MILEAGE = range(7)

# ====================== ОБЩАЯ ОТМЕНА ======================
async def cancel(update: Update, context) -> int:
    await update.message.reply_text(
        '❌ Операция отменена.',
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

# ====================== ШАГИ БОТА ======================
async def start(update: Update, context) -> int:
    await update.message.reply_text(
        'Привет! Добро пожаловать в бота **SHUNSOKU**. Выберите опцию:',
        reply_markup=ReplyKeyboardMarkup(
            [['Консультация', 'Заказ'], ['Отмена']],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return CHOICE


async def choice(update: Update, context) -> int:
    if update.message.text.strip() == 'Отмена':
        return await cancel(update, context)
    
    context.user_data['choice'] = update.message.text
    await update.message.reply_text(
        'Пожалуйста, введите ваше имя:',
        reply_markup=ReplyKeyboardMarkup([['Отмена']], resize_keyboard=True)
    )
    return NAME


async def name(update: Update, context) -> int:
    if update.message.text.strip() == 'Отмена':
        return await cancel(update, context)
    
    context.user_data['name'] = update.message.text
    # Сразу переходим к телефону (фамилии больше нет)
    await update.message.reply_text(
        'Введите ваш номер телефона (в формате +7XXXXXXXXXX или 8XXXXXXXXXX):',
        reply_markup=ReplyKeyboardMarkup([['Отмена']], resize_keyboard=True)
    )
    return PHONE


async def phone(update: Update, context) -> int:
    text = update.message.text.strip()
    if text == 'Отмена':
        return await cancel(update, context)

    # Валидация телефона
    if not re.match(r'^\+?7\d{10}$|^8\d{10}$', text):
        await update.message.reply_text(
            '❌ Неверный формат телефона!\n\n'
            'Примеры:\n'
            '• +79161234567\n'
            '• 89161234567\n\n'
            'Попробуйте ещё раз:'
        )
        return PHONE

    if text.startswith('8'):
        text = '+7' + text[1:]
    context.user_data['phone'] = text

    await update.message.reply_text(
        'Выберите тип транспорта:',
        reply_markup=ReplyKeyboardMarkup(
            [['Мотоцикл', 'Машина'], ['Отмена']],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return TRANSPORT


async def transport(update: Update, context) -> int:
    if update.message.text.strip() == 'Отмена':
        return await cancel(update, context)
    
    context.user_data['transport'] = update.message.text
    await update.message.reply_text(
        'Введите модель транспорта:',
        reply_markup=ReplyKeyboardMarkup([['Отмена']], resize_keyboard=True)
    )
    return MODEL


async def model(update: Update, context) -> int:
    if update.message.text.strip() == 'Отмена':
        return await cancel(update, context)
    
    context.user_data['model'] = update.message.text
    await update.message.reply_text(
        'Введите год выпуска (1950–2030):',
        reply_markup=ReplyKeyboardMarkup([['Отмена']], resize_keyboard=True)
    )
    return YEAR


async def year(update: Update, context) -> int:
    if update.message.text.strip() == 'Отмена':
        return await cancel(update, context)
    
    try:
        y = int(update.message.text.strip())
        if not (1950 <= y <= 2030):
            raise ValueError
        context.user_data['year'] = str(y)
    except:
        await update.message.reply_text(
            '❌ Неверный год!\n\n'
            'Введите число от 1950 до 2030:'
        )
        return YEAR
    
    await update.message.reply_text(
        'Введите желаемый пробег (в км):',
        reply_markup=ReplyKeyboardMarkup([['Отмена']], resize_keyboard=True)
    )
    return MILEAGE


async def mileage(update: Update, context) -> int:
    if update.message.text.strip() == 'Отмена':
        return await cancel(update, context)
    
    try:
        m = int(update.message.text.strip().replace(' ', '').replace(',', ''))
        if m < 0 or m > 1000000:
            raise ValueError
        context.user_data['mileage'] = str(m)
    except:
        await update.message.reply_text(
            '❌ Неверный пробег!\n\n'
            'Введите число от 0 до 1 000 000:'
        )
        return MILEAGE

    # ====================== ОТПРАВКА АДМИНУ ======================
    data = context.user_data
    message = (
        f"Новый запрос:\n"
        f"Опция: {data['choice']}\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Транспорт: {data['transport']}\n"
        f"Модель: {data['model']}\n"
        f"Год: {data['year']}\n"
        f"Желаемый пробег: {data['mileage']} км\n"
        f"Пользователь: @{update.message.from_user.username} (ID: {update.message.from_user.id})"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=message)
        await update.message.reply_text('Спасибо! Ваши данные отправлены. Мы свяжемся с вами скоро.')
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")
        await update.message.reply_text('Произошла ошибка. Попробуйте позже.')

    context.user_data.clear()
    return ConversationHandler.END


# ====================== ЗАПУСК ======================
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOICE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, choice)],
            NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            PHONE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            TRANSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transport)],
            MODEL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, model)],
            YEAR:      [MessageHandler(filters.TEXT & ~filters.COMMAND, year)],
            MILEAGE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, mileage)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

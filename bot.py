import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler

# Токен твоего бота
TOKEN = '7391894514:AAGIHR4g83Ifyu-ZExbMUC4-SXnIP7Z0ElA'

# Создание приложения Telegram
app = ApplicationBuilder().token(TOKEN).build()


# Функция для команды /start
async def start(update, context):
    # Создаем Inline кнопку с WebApp
    keyboard = [
        [InlineKeyboardButton("Open App", web_app=telegram.WebAppInfo("https://www.favbet.ua/uk/short-register/?clickid=1090568018&advertiser_id=8&b_tag=a_513b_89c_1090568018AffiliateId=160&publisher_id=160&track_id=1090568018&param1="))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение с кнопкой
    await update.message.reply_text("Нажми кнопку, чтобы открыть Mini App", reply_markup=reply_markup)


# Привязываем команду /start к функции
app.add_handler(CommandHandler("start", start))

# Запуск бота
app.run_polling()

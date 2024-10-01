import telegram
import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler


TOKEN = '7391894514:AAGIHR4g83Ifyu-ZExbMUC4-SXnIP7Z0ElA'

app = ApplicationBuilder().token(TOKEN).build()

# Инициализируем планировщик задач
scheduler = BackgroundScheduler()
scheduler.start()

async def start(update, context):
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo="https://www.dropbox.com/scl/fi/z8mizfnt40l2hrfig0j58/photo_2024-08-20_16-58-28.jpg?rlkey=aduxk31rerw4ru5928rhhfpaa&st=9m45qjur&dl=0",
    )

    keyboard = [
        [InlineKeyboardButton("1", callback_data="option_1")],
        [InlineKeyboardButton("2", callback_data="option_2")],
        [InlineKeyboardButton("3", callback_data="option_3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Вітаю, дорогий клієнте🙌 "
        "Цієї весни ми даємо можливість першим 100 гравцям отримати будь-який бонус на свій рахунок🎁💰 "
        "👇Обирай будь-яку коробку за номером та забирай свій приз👇",
        reply_markup=reply_markup
    )

# Функция для обработки нажатий на кнопки 1, 2, 3
async def button_handler(update, context):
    query = update.callback_query
    await query.answer()

    # Подготовка кнопок для регистрации
    registration_keyboard = [
        [InlineKeyboardButton("Реєстрація", url="https://tds.favbet.partners/331/127?l=111&utm_medium=NewBot&utm_source=NewBot&utm_campaign=NewBot&creative_type=link&creative_id=111")],
        [InlineKeyboardButton("Реєстрація через Telegram", web_app=telegram.WebAppInfo("https://tds.favbet.partners/331/127?l=111&utm_medium=NewBotMini&utm_source=NewBotMini&utm_campaign=NewBotMini&creative_type=link&creative_id=111"))]
    ]
    reply_markup = InlineKeyboardMarkup(registration_keyboard)

    if query.data == "option_1":
        photo_url = "https://www.dropbox.com/scl/fi/qmt9g2pur5zgzex5ilcfv/photo_2024-08-20_16-58-36.jpg?rlkey=9ui7kivcg1jji6q4c007ozu9e&st=4uw7k61b&dl=0"
        text = ("😍️ОТАКОЇ😍️\n"
                "🎁️Ти виграв 300 БЕЗКОШТОВНИХ обертів без відіграшу🎁️\n"
                "А оскільки фріспіни БЕЗ ВІДІГРАШУ, "
                "виграш одразу можна вивести на карту 💸 "
                "+ 100FS в грі Starlight Princess \n\n"
                "Щоб забрати подарунок👇️ :\n"
                "1. Натисніть Реєстрація ✅ і перейдіть на сайт\n"
                "2. Пройдіть швидку реєстрацію\n"
                "3. Станьте гравцем Favbet та внесіть депозит від 100 грн\n"
                "4. Отримаєте бонус на Ваш рахунок\n\n"
                "👇 Скоріше приєднуйся до прибуткової гри 👇")

    elif query.data == "option_2":
        photo_url = "https://www.dropbox.com/scl/fi/qmt9g2pur5zgzex5ilcfv/photo_2024-08-20_16-58-36.jpg?rlkey=9ui7kivcg1jji6q4c007ozu9e&st=4uw7k61b&dl=0"
        text = ("😍️ОТАКОЇ😍️\n"
                "🎁️Ти виграв 300 БЕЗКОШТОВНИХ обертів без відіграшу🎁️\n"
                "А оскільки фріспіни БЕЗ ВІДІГРАШУ, "
                "виграш одразу можна вивести на карту 💸 "
                "+ 100FS в грі Starlight Princess \n\n"
                "Щоб забрати подарунок👇️ :\n"
                "1. Натисніть Реєстрація ✅ і перейдіть на сайт\n"
                "2. Пройдіть швидку реєстрацію\n"
                "3. Станьте гравцем Favbet та внесіть депозит від 100 грн\n"
                "4. Отримаєте бонус на Ваш рахунок\n\n"
                "👇 Скоріше приєднуйся до прибуткової гри 👇")

    elif query.data == "option_3":
        photo_url = "https://www.dropbox.com/scl/fi/qmt9g2pur5zgzex5ilcfv/photo_2024-08-20_16-58-36.jpg?rlkey=9ui7kivcg1jji6q4c007ozu9e&st=4uw7k61b&dl=0"
        text = ("😍️ОТАКОЇ😍️\n"
                "🎁️Ти виграв 300 БЕЗКОШТОВНИХ обертів без відіграшу🎁️\n"
                "А оскільки фріспіни БЕЗ ВІДІГРАШУ, "
                "виграш одразу можна вивести на карту 💸 "
                "+ 100FS в грі Starlight Princess \n\n"
                "Щоб забрати подарунок👇️ :\n"
                "1. Натисніть Реєстрація ✅ і перейдіть на сайт\n"
                "2. Пройдіть швидку реєстрацію\n"
                "3. Станьте гравцем Favbet та внесіть депозит від 100 грн\n"
                "4. Отримаєте бонус на Ваш рахунок\n\n"
                "👇 Скоріше приєднуйся до прибуткової гри 👇")

    await context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=photo_url,
        caption=text,
        reply_markup=reply_markup
    )

# Функция для планирования сообщений с картинкой и текстом
async def schedule_message(update, context):
    chat_id = update.message.chat_id
    if len(context.args) < 3:
        await update.message.reply_text("Неправильный формат. Используйте: /schedule <время> <ссылка_на_картинку> <текст>")
        return

    try:
        # Получаем время в формате ГГГГ-ММ-ДД ЧЧ:ММ
        run_time = datetime.datetime.strptime(context.args[0], '%Y-%m-%d %H:%M')
    except ValueError:
        await update.message.reply_text("Неправильный формат времени. Используйте формат: ГГГГ-ММ-ДД ЧЧ:ММ")
        return

    # Получаем ссылку на картинку и текст
    photo_url = context.args[1]
    text = ' '.join(context.args[2:])  # Соединяем текст сообщения

    # Функция для отправки запланированного сообщения
    def send_scheduled_message(context):
        context.bot.send_photo(chat_id=chat_id, photo=photo_url, caption=text)

    # Планируем отправку сообщения
    scheduler.add_job(send_scheduled_message, 'date', run_date=run_time, args=[context])
    await update.message.reply_text(f"Запланировано сообщение на {run_time} с текстом: {text} и картинкой: {photo_url}")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("schedule", schedule_message))
app.add_handler(CallbackQueryHandler(button_handler))

app.run_polling()

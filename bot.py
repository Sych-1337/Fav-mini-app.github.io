import telegram
import httpx
import io
import datetime
import os
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read the token from environment for security
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set. Please set it before running the bot.")

WEBAPP_BASE_URL = os.getenv('WEBAPP_BASE_URL', 'http://localhost:8000')
ALLOWED_REDIRECT_DOMAIN = os.getenv('ALLOWED_REDIRECT_DOMAIN', 'go.favbet.ua')

app = ApplicationBuilder().token(TOKEN).build()

# Инициализируем планировщик задач
scheduler = BackgroundScheduler()
scheduler.start()


def _decode_payload(payload: str):
    """Поддерживает два формата: "id_p2_l" и base64url("id:p2:l"). Возвращает (id, p2, l)."""
    import base64
    if not payload:
        raise ValueError("Пустой payload")
    if len(payload.encode('utf-8')) > 64:
        raise ValueError("Payload превышает 64 байта")
    if '_' in payload:
        parts = payload.split('_')
        if len(parts) != 3:
            raise ValueError("Некорректный формат payload: ожидается id_p2_l")
        id_str, p2_str, l_str = parts
    else:
        pad = '=' * (-len(payload) % 4)
        try:
            decoded = base64.urlsafe_b64decode(payload + pad).decode('utf-8')
        except Exception as e:
            raise ValueError("Некорректная base64url строка") from e
        parts = decoded.split(':')
        if len(parts) != 3:
            raise ValueError("Некорректный формат расшифровки: ожидается 'id:p2:l'")
        id_str, p2_str, l_str = parts
    if not (id_str.isdigit() and p2_str.isdigit() and l_str.isdigit()):
        raise ValueError("Параметры должны быть числами: id, p2 и l")
    return id_str, p2_str, l_str


def _build_target_url(id_str: str, p2_str: str, l_str: str) -> str:
    # Безопасность: используем только разрешённый домен
    domain = 'go.favbet.ua' if ALLOWED_REDIRECT_DOMAIN != 'go.favbet.ua' else ALLOWED_REDIRECT_DOMAIN
    return f"https://{domain}/{id_str}/{p2_str}?l={l_str}"

async def start(update, context):
    # Попробуем взять payload из аргументов /start
    payload = None
    if context.args:
        # Для дип‑ссылок Telegram весь payload идёт единым аргументом
        payload = context.args[0]

    # Если payload корректный — добавим кнопки Mini App и обычную URL-ссылку
    dynamic_buttons = []
    if payload:
        try:
            i, p2, l = _decode_payload(payload)
            target = _build_target_url(i, p2, l)
            dynamic_buttons = [
                [InlineKeyboardButton("Открыть в Mini App", web_app=telegram.WebAppInfo(f"{WEBAPP_BASE_URL}?tgWebAppStartParam={payload}"))],
                [InlineKeyboardButton("Открыть в браузере", url=target)],
            ]
        except Exception as e:
            logger.warning("Некорректный payload: %s", e)

    keyboard = (
        dynamic_buttons
        + [
            [InlineKeyboardButton("1", callback_data="option_1")],
            [InlineKeyboardButton("2", callback_data="option_2")],
            [InlineKeyboardButton("3", callback_data="option_3")],
        ]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 1) Отправляем приветственное сообщение с HTML и emoji-id
    chat_id = update.effective_chat.id
    welcome_text = (
        'Ласкаво просимо у Favbet! <emoji id="503026726308172796"></emoji>\n'
        'Раді, що ти тепер з нами 🤝\n\n'
        'Тут круті акції, ексклюзивні промокоди та безліч бонусів <emoji id="5301170991198654880"></emoji>\n'
        'Словом, тільки твій всесвіт гри '
        '<emoji id="5303136638861242426"></emoji>'
        '<emoji id="5301286457099441206"></emoji>'
        '<emoji id="503026726308172796"></emoji>'
    )
    await context.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode='HTML')

    # 2) Отправляем картинку с хостинга с кнопками (загружаем байты, т.к. ссылка не прямой файл)
    photo_url = "https://prnt.sc/YT4wmRnnBUPU"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(photo_url)
            resp.raise_for_status()
            data = resp.content
        bio = io.BytesIO(data)
        bio.name = "111.jpg"  # имя файла для Telegram
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=bio,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.warning("Не удалось скачать изображение по URL %s: %s", photo_url, e)

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

logger.info("Starting bot polling...")  
app.run_polling() 

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

    # Кнопка под главным сообщением: "Забрати бонус" (открывает Mini App)
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(
            text="Забрати бонус",
            web_app=telegram.WebAppInfo(
                url="https://go.favbet.ua/311/134?l=591&utm_source=tgbot&utm_content=tg&creative_type=link&creative_id=591"
            )
        )]]
    )

    # 1) Отправляем приветственное сообщение с обычными эмодзи
    chat_id = update.effective_chat.id
    welcome_text = (
        'Ласкаво просимо у Favbet! 💅\n'
        'Раді, що ти тепер з нами 🤝\n\n'
        'Тут круті акції, ексклюзивні промокоди та безліч бонусів 💅\n'
        'Словом, тільки твій всесвіт гри 🎰🎰🎰'
    )
    await context.bot.send_message(chat_id=chat_id, text=welcome_text, reply_markup=reply_markup)

    # 2) Отправляем картинку по прямой ссылке (без кнопок)
    photo_url = "https://raw.githubusercontent.com/Sych-1337/Fav-mini-app.github.io/refs/heads/main/111.jpg"
    await context.bot.send_photo(chat_id=chat_id, photo=photo_url)

# Функция для обработки нажатий (сейчас callback-кнопок нет)
async def button_handler(update, context):
    query = update.callback_query
    if not query:
        return
    # Просто закрываем индикатор нажатия и подсказываем перейти по кнопке под сообщением
    await query.answer(text="Скористайтесь кнопкою \"Забрати бонус\" під повідомленням", show_alert=False)

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

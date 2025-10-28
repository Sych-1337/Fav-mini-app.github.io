import telegram
import httpx
import io
import datetime
import os
import logging
import json
import asyncio
import re
import time

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read the token from environment for security
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set. Please set it before running the bot.")

WEBAPP_BASE_URL = os.getenv('WEBAPP_BASE_URL', 'http://localhost:8000')
ALLOWED_REDIRECT_DOMAIN = os.getenv('ALLOWED_REDIRECT_DOMAIN', 'go.favbet.ua')
CONTROL_CHAT_ID_ENV = os.getenv('CONTROL_CHAT_ID')
BOT_ADMIN_IDS_ENV = os.getenv('BOT_ADMIN_IDS', '')

# Parse control chat id and admin ids
CONTROL_CHAT_ID = None
try:
    if CONTROL_CHAT_ID_ENV:
        CONTROL_CHAT_ID = int(CONTROL_CHAT_ID_ENV)
except ValueError:
    logger.warning("CONTROL_CHAT_ID is not a valid integer: %s", CONTROL_CHAT_ID_ENV)

BOT_ADMIN_IDS: set[int] = set()
for part in BOT_ADMIN_IDS_ENV.replace(';', ',').split(','):
    part = part.strip()
    if not part:
        continue
    try:
        BOT_ADMIN_IDS.add(int(part))
    except ValueError:
        logger.warning("Invalid admin id in BOT_ADMIN_IDS: %s", part)

app = ApplicationBuilder().token(TOKEN).build()

# Инициализируем планировщик задач
scheduler = BackgroundScheduler()
scheduler.start()

# -------------------- JSONL subscribers storage --------------------
# Используем JSON Lines для безопасной дописи и быстрой загрузки при старте.
# DATA_DIR можно указывать на Render Disk, например /data
DATA_DIR = os.getenv('DATA_DIR', os.path.join(os.path.dirname(__file__), 'data'))
USERS_JSONL = os.path.join(DATA_DIR, 'users.jsonl')
USERS_SNAPSHOT = os.path.join(DATA_DIR, 'users.snapshot.json')

# В памяти держим множество подписчиков для быстрой рассылки
SUBSCRIBERS: set[int] = set()

def _ensure_files() -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(USERS_JSONL):
            with open(USERS_JSONL, 'w', encoding='utf-8'):
                pass
        if not os.path.exists(USERS_SNAPSHOT):
            with open(USERS_SNAPSHOT, 'w', encoding='utf-8') as f:
                json.dump({'subscribers': []}, f)
    except Exception as e:
        logger.error('Failed to ensure data files: %s', e)

def load_subscribers_from_disk() -> set[int]:
    _ensure_files()
    subs: set[int] = set()
    # 1) Быстрый снапшот
    try:
        with open(USERS_SNAPSHOT, 'r', encoding='utf-8') as s:
            data = json.load(s)
            for cid in data.get('subscribers', []):
                try:
                    subs.add(int(cid))
                except Exception:
                    continue
    except Exception:
        pass
    # 2) Догружаем хвост из JSONL
    try:
        with open(USERS_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                op = rec.get('op')
                cid = rec.get('chat_id')
                if cid is None:
                    continue
                try:
                    cid = int(cid)
                except Exception:
                    continue
                if op == 'seen':
                    subs.add(cid)
                elif op == 'unsubscribe':
                    subs.discard(cid)
    except FileNotFoundError:
        pass
    return subs

def _append_event(record: dict) -> None:
    record = dict(record)
    record['ts'] = int(time.time())
    payload = json.dumps(record, ensure_ascii=False)
    try:
        _ensure_files()
        # Атомарная допись строки
        with open(USERS_JSONL, 'a', encoding='utf-8') as f:
            f.write(payload + '\n')
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        logger.error('Failed to append JSONL event: %s', e)

def mark_seen(chat_id: int) -> None:
    try:
        cid = int(chat_id)
    except Exception:
        return
    SUBSCRIBERS.add(cid)
    _append_event({'op': 'seen', 'chat_id': cid})

def mark_unsubscribe(chat_id: int) -> None:
    try:
        cid = int(chat_id)
    except Exception:
        return
    SUBSCRIBERS.discard(cid)
    _append_event({'op': 'unsubscribe', 'chat_id': cid})

def compact_users() -> None:
    try:
        _ensure_files()
        snap = {'subscribers': sorted(int(x) for x in SUBSCRIBERS)}
        tmp = USERS_SNAPSHOT + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(snap, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, USERS_SNAPSHOT)
    except Exception as e:
        logger.error('Failed to compact users snapshot: %s', e)

# Инициализация подписчиков при старте и планирование компакта
try:
    SUBSCRIBERS = load_subscribers_from_disk()
    logger.info("Loaded %d subscribers from JSONL store", len(SUBSCRIBERS))
    # ежедневная компакция в 03:30
    scheduler.add_job(compact_users, 'cron', hour=3, minute=30)
except Exception as e:
    logger.warning("Failed to initialize subscribers: %s", e)


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

    # Кнопка под сообщением: "Забрати бонус" (Mini App с base64url payload)
    import base64
    raw_payload = "311:134:591"  # id:p2:l
    encoded = base64.urlsafe_b64encode(raw_payload.encode("utf-8")).decode("utf-8").rstrip("=")
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(
            text="Забрати бонус",
            web_app=telegram.WebAppInfo(url=f"{WEBAPP_BASE_URL}?tgWebAppStartParam={encoded}")
        )]]
    )

    # Отправляем одно сообщение: фото + подпись + кнопка
    chat_id = update.effective_chat.id
    welcome_text = (
        'Ласкаво просимо у Favbet! 💅\n'
        'Раді, що ти тепер з нами 🤝\n\n'
        'Тут круті акції, ексклюзивні промокоди та безліч бонусів 💅\n'
        'Словом, тільки твій всесвіт гри 🎰🎰🎰'
    )
    photo_url = "https://raw.githubusercontent.com/Sych-1337/Fav-mini-app.github.io/refs/heads/main/111.jpg"
    await context.bot.send_photo(chat_id=chat_id, photo=photo_url, caption=welcome_text, reply_markup=reply_markup)
    # Subscribe user who pressed /start (JSONL append-only)
    try:
        if update.effective_chat and update.effective_chat.type == 'private':
            mark_seen(update.effective_chat.id)
    except Exception as e:
        logger.warning("Failed to add subscriber: %s", e)

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


# -------------------- Control chat posting --------------------
def _is_from_control_chat(update) -> bool:
    try:
        return CONTROL_CHAT_ID is not None and update.effective_chat and update.effective_chat.id == CONTROL_CHAT_ID
    except Exception:
        return False

def _is_admin(update) -> bool:
    try:
        return update.effective_user and (update.effective_user.id in BOT_ADMIN_IDS)
    except Exception:
        return False

async def _broadcast_to_all(bot, send_callable) -> tuple[int, int]:
    """send_callable(chat_id) -> awaitable that sends message to chat_id"""
    subscribers = list(SUBSCRIBERS)
    ok = 0
    fail = 0
    for uid in subscribers:
        try:
            await send_callable(uid)
            ok += 1
        except Exception as e:
            logger.warning("Failed to send to %s: %s", uid, e)
            fail += 1
        await asyncio.sleep(0.05)
    return ok, fail

def _strip_post_prefix(text: str) -> str:
    # Remove leading /post or /post@BotName and following spaces
    return re.sub(r"^/post(?:@\w+)?\s*", "", text or "", flags=re.IGNORECASE)

def _extract_text_and_url(body: str) -> tuple[str, str | None]:
    """Parses body like: TEXT **https://example.com**
    Returns (text_without_markup, url_or_None).
    If multiple **...** present, use the last occurrence.
    """
    if not body:
        return "", None
    candidates = list(re.finditer(r"\*\*(.+?)\*\*", body))
    url = None
    if candidates:
        last = candidates[-1]
        candidate = last.group(1).strip()
        if re.match(r"^(?:https?://)\S+", candidate, flags=re.IGNORECASE):
            url = candidate
            # remove that occurrence from text
            body = body[: last.start()] + body[last.end() :]
    # cleanup extra spaces
    text = re.sub(r"\s+", " ", body).strip()
    return text, url

async def post_text(update, context: ContextTypes.DEFAULT_TYPE):
    # Accept only from control chat and admin
    if not _is_from_control_chat(update) or not _is_admin(update):
        return
    # Extract text after command
    body = _strip_post_prefix(update.effective_message.text or "")
    if not body.strip():
        await update.effective_message.reply_text("Порожній текст для розсилки")
        return

    text_body, url = _extract_text_and_url(body)
    reply_markup = (
        InlineKeyboardMarkup([[InlineKeyboardButton("Забрати бонус", web_app=telegram.WebAppInfo(url=url))]])
        if url
        else None
    )

    async def send_callable(uid: int):
        await context.bot.send_message(chat_id=uid, text=text_body, parse_mode="HTML", reply_markup=reply_markup)

    ok, fail = await _broadcast_to_all(context.bot, send_callable)
    await context.bot.send_message(chat_id=CONTROL_CHAT_ID, text=f"Розсилка завершена. Успішно: {ok}, помилок: {fail}")

async def post_photo(update, context: ContextTypes.DEFAULT_TYPE):
    # Accept only from control chat and admin
    if not _is_from_control_chat(update) or not _is_admin(update):
        return

    msg = update.effective_message
    if not msg or not msg.photo:
        return
    # Get best quality photo
    photo = msg.photo[-1]
    caption_body = _strip_post_prefix(msg.caption or "")
    text_body, url = _extract_text_and_url(caption_body)
    reply_markup = (
        InlineKeyboardMarkup([[InlineKeyboardButton("Забрати бонус", web_app=telegram.WebAppInfo(url=url))]])
        if url
        else None
    )

    async def send_callable(uid: int):
        await context.bot.send_photo(chat_id=uid, photo=photo.file_id, caption=text_body or None, parse_mode="HTML", reply_markup=reply_markup)

    ok, fail = await _broadcast_to_all(context.bot, send_callable)
    await context.bot.send_message(chat_id=CONTROL_CHAT_ID, text=f"Розсилка завершена (фото). Успішно: {ok}, помилок: {fail}")

# Пользовательская отписка от рассылки
async def unsubscribe_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat and update.effective_chat.type == 'private':
            mark_unsubscribe(update.effective_chat.id)
            await update.effective_message.reply_text("🔕 Ви відписані від розсилки.")
    except Exception as e:
        logger.warning("Failed to unsubscribe: %s", e)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("schedule", schedule_message))
app.add_handler(CommandHandler("unsubscribe", unsubscribe_cmd))
app.add_handler(CallbackQueryHandler(button_handler))
if CONTROL_CHAT_ID is not None:
    # /post text in control chat
    app.add_handler(CommandHandler("post", post_text, filters=filters.Chat(chat_id=CONTROL_CHAT_ID)))
    # photo with caption starting with /post
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=CONTROL_CHAT_ID) & filters.PHOTO & filters.CaptionRegex(r"^/post(\s|@|$)"),
            post_photo,
        )
    )

logger.info("Starting bot polling...")  
app.run_polling() 

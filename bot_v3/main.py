from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery

from .utils import decode_payload as decode_payload_util, build_target_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "http://localhost:8000")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandStart.CommandObject):
    args: Optional[str] = command.args
    if not args:
        await message.answer("Пришлите /start <payload> или используйте дип-ссылку")
        return
    try:
        id_str, p2_str, l_str = decode_payload_util(args)
        target = build_target_url(id_str, p2_str, l_str)
    except ValueError as e:
        await message.answer(f"Ошибка payload: {e}")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть в Mini App", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}?tgWebAppStartParam={args}"))],
        [InlineKeyboardButton(text="Открыть в браузере", url=target)],
    ])

    await message.answer(
        text=f"Целевая ссылка: {target}\nМожете открыть в Mini App или в браузере.",
        reply_markup=kb,
    )


# Обработчик для deep-link кнопки app?startapp=...
@dp.message()
async def fallback(message: Message):
    # Подсказка по использованию
    await message.answer("Используйте /start <payload> или дип-ссылку")


async def main():
    logger.info("Starting aiogram v3 bot_v3...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

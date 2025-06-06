import asyncio
import re
import sqlite3
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart

from config import BOT_TOKEN, MAX_DOWNLOADS_PER_USER
from utils import detect_platform, download_video, get_user_locale, cleanup_message_later

# --- Логика базы данных (без изменений) ---
DB_NAME = 'bot_users.db'

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            download_count INTEGER DEFAULT 0,
            last_reset TEXT
        )
    ''')
    conn.commit()
    conn.close()

def check_and_update_limit(user_id: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    now = datetime.utcnow()
    
    if user:
        last_reset = datetime.fromisoformat(user["last_reset"])
        if now - last_reset > timedelta(days=1):
            cursor.execute("UPDATE users SET download_count = 1, last_reset = ? WHERE user_id = ?", (now.isoformat(), user_id))
        elif user["download_count"] >= MAX_DOWNLOADS_PER_USER:
            conn.close()
            return False
        else:
            cursor.execute("UPDATE users SET download_count = download_count + 1 WHERE user_id = ?", (user_id,))
    else:
        cursor.execute("INSERT INTO users (user_id, download_count, last_reset) VALUES (?, 1, ?)", (user_id, now.isoformat()))

    conn.commit()
    conn.close()
    return True

# --- Логика бота ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁 Скачати ще", callback_data="download_more")]])
warning_texts = {
    "uk": "⚠️ <b>Увага:</b> відео буде автоматично видалено через 5 хвилин.\nЗбережіть його заздалегідь.",
    "pl": "⚠️ <b>Uwaga:</b> film zostanie automatycznie usunięty za 5 minut.\nPobierz go wcześniej."
}

@dp.message(CommandStart())
async def start(message: Message):
    locale = get_user_locale(message)
    text = {"uk": "👋 Вітаю! Надішліть посилання на відео з TikTok, Instagram або YouTube.", "pl": "👋 Cześć! Wyślij link do filmu z TikToka, Instagrama lub YouTube."}.get(locale, "👋 Send me a video link.")
    await message.answer(text)

@dp.message(F.text.regexp(r'(https?://\S+)'))
async def handle_video_request(message: Message):
    user_id = message.from_user.id
    locale = get_user_locale(message)

    if not check_and_update_limit(user_id):
        text = {"uk": f"🚫 Ви досягли денного ліміту завантажень ({MAX_DOWNLOADS_PER_USER}).", "pl": f"🚫 Osiągnięto dzienny limit pobierania ({MAX_DOWNLOADS_PER_USER})."}.get(locale, f"🚫 Daily download limit reached ({MAX_DOWNLOADS_PER_USER}).")
        await message.reply(text)
        return

    url_match = re.search(r'(https?://\S+)', message.text)
    if not url_match: return

    url = url_match.group(1)
    platform = detect_platform(url)

    if platform:
        status_message = await message.answer("⏬ Завантажую відео...")
        video_path = await download_video(url, platform)
        
        if video_path:
            try:
                sent_video = await message.answer_video(video=FSInputFile(path=video_path), reply_markup=keyboard)
                await message.answer(warning_texts.get(locale))
                # ИСПРАВЛЕНИЕ: Убедитесь, что вызов содержит все 4 аргумента
                asyncio.create_task(cleanup_message_later(bot, sent_video.chat.id, sent_video.message_id, 300))
            except Exception as e:
                print(f"Ошибка при отправке видео: {e}")
                await message.answer("❌ Помилка під час відправки відео.")
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)
                await status_message.delete()
        else:
            await status_message.delete()
            await message.answer("❌ Помилка під час завантаження відео. Можливо, посилання недійсне або сервіс недоступний.")
    else:
        await message.reply("❌ Невідома або непідтримувана платформа.")

@dp.callback_query(F.data == "download_more")
async def handle_repeat(callback_query: CallbackQuery):
    locale = get_user_locale(callback_query)
    text = {"uk": "🔁 Надішліть нове посилання для завантаження.", "pl": "🔁 Wyślij nowy link do pobrania."}.get(locale)
    await callback_query.message.answer(text)
    await callback_query.answer()
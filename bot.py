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

# --- Логика базы данных (добавляем поле language_code) ---
DB_NAME = 'bot_users.db'

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # ИЗМЕНЕНИЕ: Добавляем столбец для языка пользователя
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN language_code TEXT")
    except sqlite3.OperationalError:
        # Такая колонка уже существует, ничего не делаем
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            download_count INTEGER DEFAULT 0,
            last_reset TEXT,
            language_code TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- Новые тексты и клавиатуры ---
# Словарь с новыми, подробными приветствиями
GREETING_TEXTS = {
    "uk": (
        "<b>Ласкаво просимо!</b>\n\n"
        "Я допоможу вам завантажити відео з TikTok, Instagram та YouTube без водяних знаків.\n\n"
        "Просто надішліть мені посилання на відео.\n\n"
        "ℹ️ <b>Важлива інформація:</b>\n"
        "🔹 **Ліміт:** Ви можете завантажити до {limit} відео на добу.\n"
        "🔹 **Автовидалення:** Надіслані мною відео будуть автоматично видалені через 5 хвилин для економії місця."
    ),
    "pl": (
        "<b>Witaj!</b>\n\n"
        "Pomogę Ci pobrać filmy z TikToka, Instagrama i YouTube bez znaków wodnych.\n\n"
        "Po prostu wyślij mi link do filmu.\n\n"
        "ℹ️ <b>Ważne informacje:</b>\n"
        "🔹 **Limit:** Możesz pobrać do {limit} filmów dziennie.\n"
        "🔹 **Automatyczne usuwanie:** Wysłane przeze mnie filmy zostaną automatycznie usunięte po 5 minutach, aby zaoszczędzić miejsce."
    ),
    "en": (
        "<b>Welcome!</b>\n\n"
        "I will help you download videos from TikTok, Instagram, and YouTube without watermarks.\n\n"
        "Just send me a link to a video.\n\n"
        "ℹ️ <b>Important Information:</b>\n"
        "🔹 **Limit:** You can download up to {limit} videos per day.\n"
        "🔹 **Auto-deletion:** Videos sent by me will be automatically deleted after 5 minutes to save space."
    )
}

# Клавиатура для выбора языка
language_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk"),
        InlineKeyboardButton(text="🇵🇱 Polski", callback_data="lang_pl"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
    ]
])


def get_user_db(user_id: int):
    """Вспомогательная функция для получения данных пользователя из БД."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

# ... остальная часть файла ...
# (check_and_update_limit, bot, dp, keyboard, warning_texts)

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
        # При первом контакте создаем пользователя без языка
        cursor.execute("INSERT INTO users (user_id, download_count, last_reset) VALUES (?, 1, ?)", (user_id, now.isoformat()))

    conn.commit()
    conn.close()
    return True

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁 Скачати ще", callback_data="download_more")]])
warning_texts = {
    "uk": "⚠️ <b>Увага:</b> відео буде автоматично видалено через 5 хвилин.\nЗбережіть його заздалегідь.",
    "pl": "⚠️ <b>Uwaga:</b> film zostanie automatycznie usunięty za 5 minut.\nPobierz go wcześniej."
}

# ИЗМЕНЕНИЕ: /start теперь предлагает выбор языка
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Please select your language / Будь ласка, оберіть мову / Proszę wybrać język:", reply_markup=language_keyboard)

# НОВЫЙ ОБРАБОТЧИК: Реагирует на нажатие кнопок выбора языка
@dp.callback_query(F.data.startswith("lang_"))
async def select_language(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    # Сохраняем выбор языка в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Используем INSERT OR IGNORE и UPDATE для атомарности
    cursor.execute("INSERT OR IGNORE INTO users (user_id, language_code) VALUES (?, ?)", (user_id, lang_code))
    cursor.execute("UPDATE users SET language_code = ? WHERE user_id = ?", (lang_code, user_id))
    conn.commit()
    conn.close()

    # Отправляем новое приветствие
    text = GREETING_TEXTS.get(lang_code, GREETING_TEXTS["en"]).format(limit=MAX_DOWNLOADS_PER_USER)
    
    # Редактируем исходное сообщение, чтобы убрать кнопки
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await callback.answer() # Подтверждаем получение колбэка


@dp.message(F.text.regexp(r'(https?://\S+)'))
async def handle_video_request(message: Message):
    # Логика этой функции остается прежней, но теперь get_user_locale будет работать по-новому
    user_id = message.from_user.id
    locale = await get_user_locale(message) # get_user_locale теперь асинхронная

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
    locale = await get_user_locale(callback_query) # get_user_locale теперь асинхронная
    text = {"uk": "🔁 Надішліть нове посилання для завантаження.", "pl": "🔁 Wyślij nowy link do pobrania."}.get(locale)
    await callback_query.message.answer(text)
    await callback_query.answer()
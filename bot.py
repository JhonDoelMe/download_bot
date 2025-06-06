import asyncio
import re
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from config import BOT_TOKEN, MAX_DOWNLOADS_PER_USER
from utils import detect_platform, download_video, get_user_locale, cleanup_message_later

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

user_downloads = {}

keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Скачати ще", callback_data="download_more")]
    ]
)

warning_texts = {
    "uk": "⚠️ <b>Увага:</b> відео буде автоматично видалено через 5 хвилин.\n"
          "Збережіть його заздалегідь.",
    "pl": "⚠️ <b>Uwaga:</b> film zostanie automatycznie usunięty za 5 minut.\n"
          "Pobierz go wcześniej."
}


@dp.message(CommandStart())
async def start(message: Message):
    locale = get_user_locale(message)
    text = {
        "uk": "👋 Вітаю! Надішліть посилання на відео з TikTok, Instagram або YouTube.",
        "pl": "👋 Cześć! Wyślij link do filmu z TikToka, Instagrama lub YouTube."
    }.get(locale, "👋 Send me a video link.")
    await message.answer(text)


@dp.message(F.text.regexp(r'(https?://\S+)'))
async def handle_video_request(message: Message):
    user_id = message.from_user.id
    locale = get_user_locale(message)

    if user_downloads.get(user_id, 0) >= MAX_DOWNLOADS_PER_USER:
        text = {
            "uk": "🚫 Ви досягли ліміту завантажень.",
            "pl": "🚫 Osiągnięto limit pobierania."
        }.get(locale, "🚫 Download limit reached.")
        await message.reply(text)
        return

    url_match = re.search(r'(https?://\S+)', message.text)
    if not url_match:
        return

    url = url_match.group(1)
    platform = detect_platform(url)

    if platform:
        await message.answer("⏬ Завантажую відео...")
        try:
            video_path = await download_video(url, platform)
            sent = await message.answer_video(
                video=open(video_path, "rb"),
                reply_markup=keyboard
            )
            await message.answer(warning_texts.get(locale))
            user_downloads[user_id] = user_downloads.get(user_id, 0) + 1
            await cleanup_message_later(sent.chat.id, sent.message_id, 300)
        except Exception as e:
            print(f"Помилка при завантаженні: {e}")
            await message.answer("❌ Помилка під час завантаження відео.")
    else:
        await message.reply("❌ Невідома або непідтримувана платформа.")


@dp.callback_query(F.data == "download_more")
async def handle_repeat(callback_query):
    locale = get_user_locale(callback_query)
    text = {
        "uk": "🔁 Надішліть нове посилання для завантаження.",
        "pl": "🔁 Wyślij nowy link do pobrania."
    }.get(locale)
    await callback_query.message.answer(text)

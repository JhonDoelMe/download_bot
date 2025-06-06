import asyncio
import re
import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart

from config import BOT_TOKEN, MAX_DOWNLOADS_PER_USER
from utils import detect_platform, download_video, cleanup_message_later
from database import check_and_update_limit, update_user_language, get_user_locale as db_get_user_locale

GREETING_TEXTS = {
    "uk": ("<b>Ласкаво просимо!</b>\n\nЯ допоможу вам завантажити відео з TikTok, Instagram та YouTube без водяних знаків.\n\nПросто надішліть мені посилання на відео.\n\nℹ️ <b>Важлива інформація:</b>\n🔹 <b>Ліміт:</b> Ви можете завантажити до {limit} відео на добу.\n🔹 <b>Автовидалення:</b> Надіслані мною відео будуть автоматично видалені через 5 хвилин для економії місця."),
    "pl": ("<b>Witaj!</b>\n\nPomogę Ci pobrać filmy z TikToka, Instagrama i YouTube bez znaków wodnych.\n\nPo prostu wyślij mi link do filmu.\n\nℹ️ <b>Ważne informacje:</b>\n🔹 <b>Limit:</b> Możesz pobrać do {limit} filmów dziennie.\n🔹 <b>Automatyczne usuwanie:</b> Wysłane przeze mnie filmy zostaną automatycznie usunięte po 5 minutach, aby zaoszczędzić miejsce."),
    "en": ("<b>Welcome!</b>\n\nI will help you download videos from TikTok, Instagram, and YouTube without watermarks.\n\nJust send me a link to a video.\n\nℹ️ <b>Important Information:</b>\n🔹 <b>Limit:</b> You can download up to {limit} videos per day.\n🔹 <b>Auto-deletion:</b> Videos sent by me will be automatically deleted after 5 minutes to save space.")
}
language_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk"), InlineKeyboardButton(text="🇵🇱 Polski", callback_data="lang_pl"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]])
keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁 Скачати ще", callback_data="download_more")]])
warning_texts = {"uk": "⚠️ <b>Увага:</b> відео буде автоматично видалено через 5 хвилин.\nЗбережіть його заздалегідь.", "pl": "⚠️ <b>Uwaga:</b> film zostanie automatycznie usunięty za 5 minut.\nPobierz go wcześniej.", "en": "⚠️ <b>Attention:</b> the video will be automatically deleted in 5 minutes.\nPlease save it beforehand."}

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

async def get_user_locale(message: Message | CallbackQuery) -> str:
    user_lang = await db_get_user_locale(message.from_user.id)
    if user_lang: return user_lang
    lang_from_tg = message.from_user.language_code
    if lang_from_tg:
        if lang_from_tg.startswith("pl"): return "pl"
        if lang_from_tg.startswith("uk"): return "uk"
    return "en"

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Please select your language / Будь ласка, оберіть мову / Proszę wybrać język:", reply_markup=language_keyboard)

@dp.callback_query(F.data.startswith("lang_"))
async def select_language(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1]
    await update_user_language(callback.from_user.id, lang_code)
    text = GREETING_TEXTS.get(lang_code, GREETING_TEXTS["en"]).format(limit=MAX_DOWNLOADS_PER_USER)
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.message(F.text.regexp(r'(https?://\S+)'))
async def handle_video_request(message: Message):
    user_id = message.from_user.id
    locale = await get_user_locale(message)
    if not await check_and_update_limit(user_id):
        limit_exceeded_texts = {"uk": f"🚫 Ви досягли денного ліміту завантажень ({MAX_DOWNLOADS_PER_USER}).", "pl": f"🚫 Osiągnięto dzienny limit pobierania ({MAX_DOWNLOADS_PER_USER}).", "en": f"🚫 Daily download limit reached ({MAX_DOWNLOADS_PER_USER})."}
        await message.reply(limit_exceeded_texts.get(locale, limit_exceeded_texts['en']))
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
                await message.answer(warning_texts.get(locale, warning_texts['en']))
                asyncio.create_task(cleanup_message_later(bot, sent_video.chat.id, sent_video.message_id, 300))
            except Exception as e:
                logging.error(f"Ошибка при отправке видео: {e}", exc_info=True)
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
    locale = await get_user_locale(callback_query)
    repeat_texts = {"uk": "🔁 Надішліть нове посилання для завантаження.", "pl": "🔁 Wyślij nowy link do pobrania.", "en": "🔁 Send a new link to download."}
    await callback_query.message.answer(repeat_texts.get(locale, repeat_texts['en']))
    await callback_query.answer()
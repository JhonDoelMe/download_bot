import os
import asyncio
import tempfile
import re
import yt_dlp
import pyktok
import glob
from aiogram.types import Message
from aiogram import Bot

# Импортируем путь к cookies из конфига
from config import COOKIE_FILE_PATH

SUPPORTED_PATTERNS = {
    r'(?:https?:\/\/)?(?:www\.)?tiktok\.com': 'tiktok',
    r'(?:https?:\/\/)?(?:www\.)?instagram\.com': 'instagram',
    r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)': 'youtube'
}

def detect_platform(url: str) -> str | None:
    for pattern, platform in SUPPORTED_PATTERNS.items():
        if re.search(pattern, url):
            return platform
    return None

async def run_yt_dlp(url: str, platform: str) -> str | None:
    """Общая функция для запуска yt-dlp с поддержкой cookies для Instagram."""
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, f"{os.urandom(8).hex()}.%(ext)s")
    
    ydl_opts = {
        "outtmpl": output_path,
        "format": "best[ext=mp4]/bestvideo+bestaudio/best",
        "quiet": True,
        "noplaylist": True,
    }

    # ИСПРАВЛЕНИЕ: Добавляем cookies, если это Instagram и файл существует
    if platform == 'instagram' and os.path.exists(COOKIE_FILE_PATH):
        ydl_opts['cookiefile'] = COOKIE_FILE_PATH
        print(f"Using cookies from {COOKIE_FILE_PATH} for Instagram")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        print(f"yt-dlp error for {platform}: {e}")
        return None


async def download_from_tiktok_pyktok(url: str) -> str | None:
    """ИСПРАВЛЕНИЕ: Скачивает видео из TikTok, используя правильный метод pyktok."""
    temp_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()  # Запоминаем текущую директорию
    
    try:
        os.chdir(temp_dir)  # Переходим во временную директорию
        
        await asyncio.to_thread(
            pyktok.save_tiktok,
            video_url=url,
            save_video=True
        )
        
        video_files = glob.glob(os.path.join(temp_dir, '*.mp4'))
        if video_files:
            return video_files[0]
        else:
            print("pyktok отработал, но видеофайл не найден.")
            return None
            
    except Exception as e:
        print(f"Произошла ошибка при скачивании с помощью pyktok: {e}")
        return None
    finally:
        os.chdir(original_dir) # Возвращаемся в исходную директорию


async def download_video(url: str, platform: str) -> str | None:
    """Главная функция-диспетчер для скачивания видео."""
    try:
        if platform == "youtube" or platform == "instagram":
            return await run_yt_dlp(url, platform)
        elif platform == "tiktok":
            return await download_from_tiktok_pyktok(url)
        else:
            raise ValueError("Unsupported platform")
    except Exception as e:
        print(f"Ошибка в download_video: {e}")
        return None

# Остальные функции (get_user_locale, cleanup_message_later) остаются без изменений

def get_user_locale(message: Message | dict) -> str:
    lang = (message.from_user.language_code if isinstance(message, Message)
            else message.get("from", {}).get("language_code", "uk"))
    if lang.startswith("pl"):
        return "pl"
    if lang.startswith("uk"):
        return "uk"
    return "uk"

async def cleanup_message_later(chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await Bot.get_current().delete_message(chat_id, message_id)
    except Exception as e:
        print(f"❌ Не удалось удалить сообщение: {e}")
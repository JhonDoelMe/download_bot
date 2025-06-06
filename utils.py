import os
import asyncio
import tempfile
import re
import yt_dlp
import httpx  # httpx теперь используется для TikTok
from aiogram.types import Message
from aiogram import Bot

# Импортируем ключи из конфига
from config import COOKIE_FILE_PATH, RAPIDAPI_KEY

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

async def download_from_tiktok_api(url: str) -> str | None:
    """
    Скачивает видео из TikTok, используя API, предоставленный пользователем.
    """
    api_url = "https://tiktok-download-without-watermark.p.rapidapi.com/analysis"
    headers = {
        "x-rapidapi-host": "tiktok-download-without-watermark.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    # Параметры из вашего curl запроса
    params = {"url": url, "hd": "0"}

    try:
        async with httpx.AsyncClient(timeout=40) as client:
            # 1. Запрашиваем у API информацию о видео и ссылку на скачивание
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            # ВАЖНО: Структура ответа API может быть разной.
            # Я предполагаю, что ссылка на видео без водяного знака находится в `data['data']['play_nowm']`.
            # Если это не так, вам нужно будет посмотреть реальный ответ от API и поменять ключ.
            video_download_url = data.get("data", {}).get("play_nowm")
            if not video_download_url:
                print(f"Не удалось найти ссылку на видео в ответе API. Ответ: {data}")
                return None

            # 2. Скачиваем видео по полученной прямой ссылке
            video_response = await client.get(video_download_url, follow_redirects=True)
            video_response.raise_for_status()

            # 3. Сохраняем видео во временный файл
            path = os.path.join(tempfile.gettempdir(), f"{os.urandom(8).hex()}_tiktok.mp4")
            with open(path, "wb") as f:
                f.write(video_response.content)
            
            return path

    except (httpx.RequestError, httpx.HTTPStatusError, KeyError) as e:
        print(f"Ошибка при работе с TikTok API: {e}")
        return None

async def download_video(url: str, platform: str) -> str | None:
    """Главная функция-диспетчер для скачивания видео."""
    try:
        if platform == "youtube" or platform == "instagram":
            return await run_yt_dlp(url, platform)
        elif platform == "tiktok":
            # ИСПОЛЬЗУЕМ НОВУЮ ФУНКЦИЮ
            return await download_from_tiktok_api(url)
        else:
            raise ValueError("Unsupported platform")
    except Exception as e:
        print(f"Ошибка в download_video: {e}")
        return None

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
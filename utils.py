import os
import asyncio
import tempfile
import re
import yt_dlp
import httpx
import logging
from aiogram import Bot

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
        logging.info(f"Using cookies from {COOKIE_FILE_PATH} for Instagram")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        logging.error(f"yt-dlp error for {platform}: {e}", exc_info=True)
        return None

async def download_from_tiktok_api(url: str) -> str | None:
    api_url = "https://tiktok-download-without-watermark.p.rapidapi.com/analysis"
    headers = {"x-rapidapi-host": "tiktok-download-without-watermark.p.rapidapi.com", "x-rapidapi-key": RAPIDAPI_KEY}
    params = {"url": url, "hd": "0"}

    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json().get("data", {})

            if data.get("images"):
                logging.warning("Обнаружено слайд-шоу TikTok. Этот тип контента не поддерживается.")
                return None

            video_download_url = data.get("play_nowm") or data.get("hdplay") or data.get("play")
            
            if not video_download_url or 'mp3' in video_download_url:
                logging.warning(f"Не удалось найти валидную ссылку на видео в ответе API. Ответ: {data}")
                return None

            video_response = await client.get(video_download_url, follow_redirects=True)
            video_response.raise_for_status()
            path = os.path.join(tempfile.gettempdir(), f"{os.urandom(8).hex()}_tiktok.mp4")
            with open(path, "wb") as f:
                f.write(video_response.content)
            return path
    except Exception as e:
        logging.error(f"Ошибка при работе с TikTok API: {e}", exc_info=True)
        return None

async def download_video(url: str, platform: str) -> str | None:
    try:
        if platform == "youtube" or platform == "instagram":
            return await run_yt_dlp(url, platform)
        elif platform == "tiktok":
            return await download_from_tiktok_api(url)
        else:
            raise ValueError("Unsupported platform")
    except Exception as e:
        logging.error(f"Ошибка в download_video: {e}", exc_info=True)
        return None

async def cleanup_message_later(bot: Bot, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception as e:
        logging.error(f"Не удалось удалить сообщение: {e}", exc_info=True)
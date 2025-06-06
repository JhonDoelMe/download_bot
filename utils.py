import os
import asyncio
import httpx
import tempfile
from aiogram.types import Message
from aiogram import Bot
from config import HEADERS

SUPPORTED_DOMAINS = {
    "tiktok.com": "tiktok",
    "instagram.com": "instagram",
    "youtube.com": "youtube",
    "youtu.be": "youtube"
}


def detect_platform(url: str) -> str | None:
    for domain, platform in SUPPORTED_DOMAINS.items():
        if domain in url:
            return platform
    return None


async def download_video(url: str, platform: str) -> str:
    if platform == "youtube":
        return await download_youtube(url)
    elif platform == "tiktok":
        return await download_from_ttdownloader(url)
    elif platform == "instagram":
        return await download_from_instasupersave(url)
    else:
        raise ValueError("Unsupported platform")


async def download_youtube(url: str) -> str:
    import yt_dlp
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_path,
        "format": "mp4",
        "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename


async def download_from_ttdownloader(url: str) -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        resp = await client.post("https://ttdownloader.com/req/", data={"url": url})
        video_url = resp.text.split('id="withoutWatermark"')[1].split('href="')[1].split('"')[0]
        video_data = await client.get(video_url)
        path = os.path.join(tempfile.gettempdir(), "tiktok.mp4")
        with open(path, "wb") as f:
            f.write(video_data.content)
    return path


async def download_from_instasupersave(url: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        api_url = "https://saveig.app/api/ajaxSearch"
        resp = await client.post(api_url, data={"q": url})
        data = resp.json()
        video_url = data["links"][0]["url"]
        video_data = await client.get(video_url)
        path = os.path.join(tempfile.gettempdir(), "instagram.mp4")
        with open(path, "wb") as f:
            f.write(video_data.content)
    return path


def get_user_locale(message: Message | dict) -> str:
    lang = (message.from_user.language_code if isinstance(message, Message)
            else message.get("from", {}).get("language_code", "uk"))
    return "pl" if lang.startswith("pl") else "uk"


async def cleanup_message_later(chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await Bot.get_current().delete_message(chat_id, message_id)
    except Exception as e:
        print(f"❌ Не вдалося видалити повідомлення: {e}")

import os
from dotenv import load_dotenv

load_dotenv()

# --- Основные токены ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# --- Настройки Вебхука ---
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").strip('/')
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "").strip()
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}" if WEBHOOK_BASE_URL and WEBHOOK_PATH else ""
USE_WEBHOOK = bool(WEBHOOK_URL)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# --- Настройки Веб-сервера ---
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", 8000))

# --- Настройки Базы Данных ---
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Настройки Бота ---
MAX_DOWNLOADS_PER_USER = int(os.getenv("MAX_DOWNLOADS_PER_USER", 10))

# Опциональный путь к файлу с cookies для Instagram
COOKIE_FILE_PATH = os.path.join(os.path.dirname(__file__), 'instagram_cookies.txt')
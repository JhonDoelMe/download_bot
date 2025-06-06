import os
from dotenv import load_dotenv

load_dotenv()

# --- Основные токены ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# --- Настройки Вебхука ---
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").strip('/')
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "").strip()
# Собираем полный URL из частей
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}" if WEBHOOK_BASE_URL and WEBHOOK_PATH else ""
USE_WEBHOOK = bool(WEBHOOK_URL)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# --- Настройки Веб-сервера ---
# Используем значения по умолчанию, если они не заданы
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", 8000))

# --- Настройки Базы Данных ---
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Настройки Бота ---
CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
MAX_DOWNLOADS_PER_USER = int(os.getenv("MAX_DOWNLOADS_PER_USER", 10))
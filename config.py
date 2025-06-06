import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
USE_WEBHOOK = bool(WEBHOOK_URL)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8443))

CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
MAX_DOWNLOADS_PER_USER = int(os.getenv("MAX_DOWNLOADS_PER_USER", 10))

COOKIE_FILE_PATH = os.path.join(os.path.dirname(__file__), 'instagram_cookies.txt')

# УБЕДИТЕСЬ, ЧТО ЭТА СТРОКА ПРИСУТСТВУЕТ:
# Она считывает ключ из вашего .env файла.
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
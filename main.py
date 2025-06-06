import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from aiogram.types import Update

from config import USE_WEBHOOK, WEBHOOK_URL, WEBHOOK_SECRET, WEBAPP_HOST, WEBAPP_PORT
from bot import dp, bot
# Импортируем функцию настройки БД из нового файла
from database import setup_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет запуском и остановкой."""
    # Создаем таблицы в БД при старте
    await setup_database()
    
    if USE_WEBHOOK:
        await bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    
    yield
    
    if USE_WEBHOOK:
        await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def bot_webhook(update: dict, request: Request):
    """Принимает вебхуки и проверяет секрет."""
    if WEBHOOK_SECRET:
        telegram_secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if telegram_secret_token != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Forbidden: invalid secret token")
    
    telegram_update = Update(**update)
    await dp.feed_update(bot, telegram_update)

async def run_polling():
    """Запускает бота в режиме опроса."""
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    if USE_WEBHOOK:
        # Запускаем uvicorn для режима вебхука
        uvicorn.run(
            app,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT
        )
    else:
        # Запускаем polling
        asyncio.run(run_polling())
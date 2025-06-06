import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from aiogram.types import Update

from config import USE_WEBHOOK, WEBHOOK_URL, WEBHOOK_SECRET, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT
from bot import dp, bot
from database import setup_database

def setup_logging():
    """Настраивает систему логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
    )
    logging.info("Logging is configured.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет запуском и остановкой."""
    await setup_database()
    if USE_WEBHOOK:
        await bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
        logging.info("Webhook is set.")
    yield
    if USE_WEBHOOK:
        await bot.delete_webhook()
        logging.info("Webhook is deleted.")

setup_logging()
app = FastAPI(lifespan=lifespan)

if USE_WEBHOOK and WEBHOOK_PATH:
    @app.post(WEBHOOK_PATH)
    async def bot_webhook(update: dict, request: Request):
        if WEBHOOK_SECRET:
            telegram_secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
            if telegram_secret_token != WEBHOOK_SECRET:
                logging.warning("Invalid secret token received.")
                raise HTTPException(status_code=403, detail="Forbidden: invalid secret token")
        telegram_update = Update(**update)
        await dp.feed_update(bot, telegram_update)

async def run_polling():
    """Запускает бота в режиме опроса."""
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        if USE_WEBHOOK:
            uvicorn.run(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
        else:
            asyncio.run(run_polling())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
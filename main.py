import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiogram.types import Update

from config import USE_WEBHOOK, WEBHOOK_URL
from bot import dp, bot, setup_database

# Инициализация базы данных при старте
setup_database()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Современный способ обработки событий startup и shutdown в FastAPI.
    """
    if USE_WEBHOOK:
        # Устанавливаем вебхук при запуске
        await bot.set_webhook(url=WEBHOOK_URL)
    
    yield
    
    if USE_WEBHOOK:
        # Удаляем вебхук при остановке
        await bot.delete_webhook()

# Создаем экземпляр FastAPI с использованием lifespan
app = FastAPI(lifespan=lifespan)

if USE_WEBHOOK:
    @app.post("/webhook")
    async def bot_webhook(update: dict) -> None:
        """
        Этот эндпоинт принимает обновления от Telegram
        и передает их в диспетчер aiogram.
        """
        telegram_update = Update(**update)
        await dp.feed_update(bot, telegram_update)

else:
    # Логика для запуска в режиме polling (остается без изменений)
    async def main():
        logging.basicConfig(level=logging.INFO)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    if __name__ == "__main__":
        asyncio.run(main())
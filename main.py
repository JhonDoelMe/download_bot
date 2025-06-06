import logging
from fastapi import FastAPI
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import USE_WEBHOOK, WEBHOOK_URL, HOST, PORT
from bot import dp, bot

app = FastAPI()

if USE_WEBHOOK:
    @app.on_event("startup")
    async def on_startup():
        await bot.set_webhook(WEBHOOK_URL)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
else:
    import asyncio

    async def main():
        logging.basicConfig(level=logging.INFO)
        await dp.start_polling(bot)

    if __name__ == "__main__":
        asyncio.run(main())

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from publisher import start_publisher
from app.handlers import DeviceManager, MQQTClient, BotHandler

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

device_manager = DeviceManager()
mqtt_client = MQQTClient(bot, device_manager)
bot_handler = BotHandler(bot, device_manager, mqtt_client)

async def start_bot():
    dp.include_router(router)
    await dp.start_polling(bot)
    
async def main():
    await asyncio.gather(
        start_bot(),
        start_publisher()
    )

if __name__ == '__main__':
    router = bot_handler.router
    mqtt_client.bot = bot_handler.bot
    bot_handler.bot = bot

    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('exit')
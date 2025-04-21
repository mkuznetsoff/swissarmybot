import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import API_TOKEN  # убедись, что файл config.py существует и содержит API_TOKEN
from menu import router as menu_router
from video_processor import router as video_router

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()
    
    # Подключаем обработчики
    dp.include_router(menu_router)
    dp.include_router(video_router)

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

"""
Точка входа приложения TaskGroupBot.

Выполняет следующую последовательность:
1. Загружает переменные окружения из .env файла
2. Настраивает логирование
3. Инициализирует базу данных (создаёт/мигрирует таблицы)
4. Создаёт бота и диспетчер через bot/creator.py
5. Регистрирует роутеры обработчиков команд
6. Запускает фоновую корутину проверки просрочки
7. Запускает long-polling для получения обновлений от Telegram

Запуск: python main.py
"""

import asyncio
import logging
import sys

from dotenv import load_dotenv

from bot.creator import create_bot
from db.connection import init_db
from handlers.start import router as start_router
from handlers.add_task import router as add_task_router
from handlers.list_tasks import router as list_tasks_router
from handlers.export_csv import router as export_csv_router
from handlers.edit_task import router as edit_task_router
from services.overdue_service import start_overdue_checker


def setup_logging() -> None:
    """
    Настраивает логирование приложения.

    Формат: [ВРЕМЯ] [УРОВЕНЬ] [МОДУЛЬ] — Сообщение
    Уровень по умолчанию: INFO
    """
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main() -> None:
    """
    Основная асинхронная функция: инициализация и запуск бота.
    """
    # 1. Загружаем переменные окружения из .env файла (в корне проекта)
    load_dotenv()

    # 2. Настраиваем логирование
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Запуск TaskGroupBot...")

    # 3. Инициализируем БД (создаёт таблицы, применяет миграции)
    await init_db()

    # 4. Создаём бота и диспетчер
    bot, dispatcher = create_bot()

    # 5. Регистрируем роутеры обработчиков команд
    # Порядок регистрации важен: более специфичные роутеры — первыми
    dispatcher.include_router(start_router)       # /start
    dispatcher.include_router(add_task_router)     # /add + FSM
    dispatcher.include_router(edit_task_router)    # /edit + FSM + callbacks
    dispatcher.include_router(list_tasks_router)   # /list
    dispatcher.include_router(export_csv_router)   # /list_csv

    # 6. Запускаем фоновую корутину проверки просрочки (раз в 1 час)
    asyncio.create_task(start_overdue_checker(bot))
    logger.info("Фоновая проверка просрочки запланирована")

    # Удаляем webhook, если был установлен ранее
    # (иначе polling не запустится: TelegramConflictError)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Роутеры зарегистрированы, запуск polling...")

    # 7. Запускаем long-polling
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    # Запускаем основную корутину через asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Корректное завершение по Ctrl+C — без стектрейса
        logging.getLogger(__name__).info("Бот остановлен пользователем.")
        sys.exit(0)
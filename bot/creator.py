"""
Модуль создания экземпляра бота и диспетчера.

Содержит фабричную функцию create_bot(), которая:
- Читает BOT_TOKEN из переменных окружения
- Создаёт экземпляр Bot (aiogram 3.x)
- Создаёт Dispatcher для роутинга обновлений
"""

import os
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

logger = logging.getLogger(__name__)


def create_bot() -> tuple[Bot, Dispatcher]:
    """
    Фабрика для создания бота и диспетчера.

    Читает BOT_TOKEN из переменных окружения.
    Если токен не найден — выбрасывает ValueError.

    Returns:
        tuple[Bot, Dispatcher]: Кортеж (бот, диспетчер).
    """
    # Чтение токена из окружения (загруженного через python-dotenv в main.py)
    token = os.getenv("BOT_TOKEN")

    if not token:
        logger.error("BOT_TOKEN не найден в переменных окружения")
        raise ValueError(
            "BOT_TOKEN не задан. "
            "Создайте файл .env с переменной BOT_TOKEN=<ваш_токен>"
        )

    # Создаём бота с настройками по умолчанию
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    # Создаём диспетчер — он управляет роутерами и middleware
    dispatcher = Dispatcher()

    logger.info("Бот и диспетчер успешно созданы")
    return bot, dispatcher

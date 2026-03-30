"""
Обработчик команды /list — вывод всех задач в чат.

Получает задачи из БД через сервисный слой, форматирует в читаемый список
и отправляет текстовым сообщением в групповой чат.
Личные сообщения игнорируются.
"""

import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from services import task_service

logger = logging.getLogger(__name__)

# Создаём роутер для этого обработчика
router = Router()


@router.message(Command("list"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_list(message: Message) -> None:
    """
    Обработчик команды /list в групповом чате.

    Получает все задачи из БД, форматирует и отправляет в чат.
    Если список пуст — отправляет соответствующее сообщение.

    Фильтры:
        Command("list") — реагирует только на /list
        F.chat.type.in_({"group", "supergroup"}) — только в группах

    Args:
        message: Объект входящего сообщения Telegram.
    """
    logger.info(
        "/list от %s в чате %s",
        message.from_user.full_name,
        message.chat.title,
    )

    try:
        # Получаем все задачи через сервисный слой
        tasks = await task_service.fetch_all_tasks()

        # Форматируем список задач в текст
        formatted_text = task_service.format_tasks_list(tasks)

        await message.answer(formatted_text)
    except Exception as e:
        logger.error("Ошибка при получении списка задач: %s", e)
        await message.answer("❌ Ошибка загрузки задач. Попробуйте позже.")

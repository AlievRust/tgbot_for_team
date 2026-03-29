"""
Модуль бизнес-логики работы с задачами.

Содержит функции:
- create_task(): формирует created_at (GMT+3) и делегирует запись в БД
- fetch_all_tasks(): получает все задачи из БД
- format_tasks_list(): форматирует список задач для вывода в чат
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

from db import queries

logger = logging.getLogger(__name__)

# Фиксированный часовой пояс: Москва (GMT+3)
TIMEZONE = ZoneInfo("Europe/Moscow")


async def create_task(text: str, user: str) -> int:
    """
    Создаёт новую задачу: формирует timestamp и сохраняет в БД.

    Args:
        text: Текст задачи (не пустой).
        user: Имя пользователя из Telegram.

    Returns:
        int: ID созданной задачи.
    """
    # Текущее время в часовом поясе GMT+3, формат ISO 8601
    created_at = datetime.now(TIMEZONE).isoformat()

    # Делегируем запись в БД модулю queries
    task_id = await queries.add_task(text=text, user=user, created_at=created_at)
    logger.info("Задача #%d создана: '%s' от %s", task_id, text, user)
    return task_id


async def fetch_all_tasks() -> list[dict[str, Optional[str | int]]]:
    """
    Получает все задачи из БД через модуль queries.

    Returns:
        list[dict]: Список задач (пустой, если нет ни одной).
    """
    tasks = await queries.get_all_tasks()
    return tasks


def format_tasks_list(tasks: list[dict[str, Optional[str | int]]]) -> str:
    """
    Форматирует список задач в текст для отправки в чат.

    Формат каждой строки:
        1. Текст задачи — @username, 2024-01-15 14:30

    Args:
        tasks: Список словарей с ключами id, text, user, created_at.

    Returns:
        str: Отформатированный текст со списком задач.
             Если список пуст — сообщение "Список задач пуст."
    """
    if not tasks:
        return "📋 Список задач пуст."

    lines = []
    for task in tasks:
        task_id = task["id"]
        text = task["text"]
        user = task["user"]
        # created_at хранится в ISO 8601, берём только дату и время до минут
        created_at = str(task["created_at"])[:16]

        # Формируем строку: ID. текст — @user, дата время
        line = f"{task_id}. {text} — @{user}, {created_at}"
        lines.append(line)

    # Склеиваем строки с переносами, добавляем заголовок
    result = "📋 Список задач:\n" + "\n".join(lines)
    return result
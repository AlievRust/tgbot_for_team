"""
Модуль бизнес-логики работы с задачами.

Содержит функции:
- create_task(): формирует created_at (GMT+3), запись в БД
- fetch_all_tasks(): получает все задачи из БД
- get_task(): получает задачу по ID
- update_task_field(): обновляет указанное поле задачи
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

# Допустимые поля для обновления через /edit
_EDITABLE_FIELDS = {"assignee", "deadline", "status"}

# Допустимые значения статуса (ручное управление)
_MANUAL_STATUSES = {"в работе", "выполнено"}


async def create_task(text: str, user: str, chat_id: str) -> int:
    """
    Создаёт новую задачу: формирует timestamp и сохраняет в БД.

    Args:
        text: Текст задачи (не пустой).
        user: Имя пользователя из Telegram.
        chat_id: ID группового чата.

    Returns:
        int: ID созданной задачи.
    """
    # Текущее время в часовом поясе GMT+3, формат ISO 8601
    created_at = datetime.now(TIMEZONE).isoformat()

    # Делегируем запись в БД модулю queries
    task_id = await queries.add_task(
        text=text, user=user, created_at=created_at, chat_id=chat_id
    )
    logger.info("Задача #%d создана: '%s' от %s в чате %s", task_id, text, user, chat_id)
    return task_id


async def fetch_all_tasks() -> list[dict[str, Optional[str | int]]]:
    """
    Получает все задачи из БД через модуль queries.

    Returns:
        list[dict]: Список задач (пустой, если нет ни одной).
    """
    tasks = await queries.get_all_tasks()
    return tasks


async def get_task(task_id: int) -> Optional[dict[str, Optional[str | int]]]:
    """
    Получает задачу по ID через модуль queries.

    Args:
        task_id: ID задачи.

    Returns:
        dict | None: Словарь с полями задачи или None, если не найдена.
    """
    return await queries.get_task_by_id(task_id)


async def update_task_field(
    task_id: int, field: str, value: Optional[str]
) -> None:
    """
    Обновляет указанное поле задачи с валидацией.

    Args:
        task_id: ID задачи.
        field: Имя поля (assignee, deadline, status).
        value: Новое значение (None для снятия assignee/deadline).

    Raises:
        ValueError: Если поле или значение недопустимы.
    """
    if field not in _EDITABLE_FIELDS:
        raise ValueError(f"Поле '{field}' не доступно для редактирования")

    # Валидация статуса: 'просрочено' можно установить только автоматически
    if field == "status" and value not in _MANUAL_STATUSES:
        raise ValueError(
            f"Статус '{value}' нельзя установить вручную. "
            f"Допустимо: {', '.join(sorted(_MANUAL_STATUSES))}"
        )

    await queries.update_task_field(task_id, field, value)


def format_tasks_list(tasks: list[dict[str, Optional[str | int]]]) -> str:
    """
    Форматирует список задач в текст для отправки в чат.

    Формат каждой задачи:
        1. Текст задачи — @user, 2024-01-15 14:30
           📌 Ответственный: @ivan | 📅 Дедлайн: 2024-01-20 | Статус: в работе

    Поля ответственного, дедлайна и статуса выводятся только если заданы.

    Args:
        tasks: Список словарей с полями задачи.

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

        # Основная строка: ID. текст — @user, дата время
        line = f"{task_id}. {text} — {user}, {created_at}"
        lines.append(line)

        # Дополнительная строка с атрибутами (только если хоть что-то задано)
        details = []

        assignee = task.get("assignee")
        if assignee:
            details.append(f"📌 Ответственный: {assignee}")

        deadline = task.get("deadline")
        if deadline:
            details.append(f"📅 Дедлайн: {deadline}")

        status = task.get("status")
        if status:
            details.append(f"Статус: {status}")

        if details:
            lines.append("   " + " | ".join(details))

    # Склеиваем строки с переносами, добавляем заголовок
    result = "📋 Список задач:\n" + "\n".join(lines)
    return result
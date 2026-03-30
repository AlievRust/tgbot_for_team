""""
Модуль SQL-запросов для работы с таблицей tasks.

Содержит асинхронные функции для CRUD-операций:
- add_task(): вставка новой задачи
- get_all_tasks(): получение всех задач с сортировкой по ID
"""

import logging
from typing import Optional

import aiosqlite

from db.connection import DB_PATH

logger = logging.getLogger(__name__)


async def add_task(text: str, user: str, created_at: str) -> int:
    """
    Добавляет новую задачу в базу данных.

    Args:
        text: Текст задачи (не должен быть пустым).
        user: Имя пользователя (telegram username или display name).
        created_at: Дата/время создания в формате ISO 8601 (GMT+3).

    Returns:
        int: ID созданной задачи (последний вставленный rowid).

    Raises:
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    # Параметризованный запрос для защиты от SQL-инъекций
    insert_sql = """
        INSERT INTO tasks (text, user, created_at)
        VALUES (?, ?, ?)
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(insert_sql, (text, user, created_at))
            await db.commit()
            # lastrowid содержит ID только что вставленной строки
            task_id = cursor.lastrowid
            logger.info("Задача #%d добавлена пользователем %s", task_id, user)
            return task_id
    except aiosqlite.Error as e:
        logger.error("Ошибка добавления задачи в БД: %s", e)
        raise


async def get_all_tasks() -> list[dict[str, Optional[str | int]]]:
    """
    Получает все задачи из базы данных, отсортированные по ID (по возрастанию).

    Returns:
        list[dict]: Список словарей с ключами:
            - id: int — ID задачи
            - text: str — текст задачи
            - user: str — имя пользователя
            - created_at: str — дата/время создания

        Пустой список, если задач нет.

    Raises:
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    # Сортировка по id — задачи в хронологическом порядке добавления
    select_sql = """
        SELECT id, text, user, created_at
        FROM tasks
        ORDER BY id ASC
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # row_factory возвращает каждую строку как dict (по именам колонок)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(select_sql)
            rows = await cursor.fetchall()

            # Преобразуем объекты Row в обычные словари для удобной работы
            tasks = [dict(row) for row in rows]
            logger.info("Получено задач из БД: %d", len(tasks))
            return tasks
    except aiosqlite.Error as e:
        logger.error("Ошибка получения задач из БД: %s", e)
        raise

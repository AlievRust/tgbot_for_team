"""
Модуль SQL-запросов для работы с таблицами tasks и chat_members.

Содержит асинхронные функции для CRUD-операций:
- add_task(): вставка новой задачи
- get_all_tasks(): получение всех задач с сортировкой по ID
- get_task_by_id(): получение задачи по ID
- update_task_field(): обновление произвольного поля задачи
- update_task_status(): обновление статуса задачи
- upsert_member(): добавление/обновление участника чата
- get_chat_members(): получение списка участников чата
- get_overdue_tasks(): получение просроченных задач
"""

import logging
from typing import Optional

import aiosqlite

from db.connection import DB_PATH

logger = logging.getLogger(__name__)

# Допустимые имена колонок для обновления (защита от SQL-инъекций в имени поля)
_ALLOWED_TASK_FIELDS = {"assignee", "deadline", "status"}


async def add_task(
    text: str, user: str, created_at: str, chat_id: str
) -> int:
    """
    Добавляет новую задачу в базу данных.

    Args:
        text: Текст задачи (не должен быть пустым).
        user: Имя пользователя (telegram username или display name).
        created_at: Дата/время создания в формате ISO 8601 (GMT+3).
        chat_id: ID группового чата (строка).

    Returns:
        int: ID созданной задачи (последний вставленный rowid).

    Raises:
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    insert_sql = """
        INSERT INTO tasks (text, user, created_at, chat_id)
        VALUES (?, ?, ?, ?)
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(insert_sql, (text, user, created_at, chat_id))
            await db.commit()
            task_id = cursor.lastrowid
            logger.info("Задача #%d добавлена пользователем %s в чат %s", task_id, user, chat_id)
            return task_id
    except aiosqlite.Error as e:
        logger.error("Ошибка добавления задачи в БД: %s", e)
        raise


async def get_all_tasks() -> list[dict[str, Optional[str | int]]]:
    """
    Получает все задачи из базы данных, отсортированные по ID (по возрастанию).

    Returns:
        list[dict]: Список словарей с ключами:
            - id, text, user, created_at, chat_id, assignee, deadline, status

        Пустой список, если задач нет.

    Raises:
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    select_sql = """
        SELECT id, text, user, created_at, chat_id, assignee, deadline, status
        FROM tasks
        ORDER BY id ASC
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(select_sql)
            rows = await cursor.fetchall()
            tasks = [dict(row) for row in rows]
            logger.info("Получено задач из БД: %d", len(tasks))
            return tasks
    except aiosqlite.Error as e:
        logger.error("Ошибка получения задач из БД: %s", e)
        raise


async def get_task_by_id(task_id: int) -> Optional[dict[str, Optional[str | int]]]:
    """
    Получает задачу по её ID.

    Args:
        task_id: ID задачи.

    Returns:
        dict | None: Словарь с полями задачи или None, если задача не найдена.

    Raises:
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    select_sql = """
        SELECT id, text, user, created_at, chat_id, assignee, deadline, status
        FROM tasks
        WHERE id = ?
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(select_sql, (task_id,))
            row = await cursor.fetchone()
            if row is None:
                logger.info("Задача #%d не найдена", task_id)
                return None
            logger.info("Задача #%d найдена", task_id)
            return dict(row)
    except aiosqlite.Error as e:
        logger.error("Ошибка поиска задачи #%d: %s", task_id, e)
        raise


async def update_task_field(task_id: int, field: str, value: Optional[str]) -> None:
    """
    Обновляет произвольное поле задачи по ID.

    Допустимые поля: assignee, deadline, status.
    Для снятия значения (assignee/deadline) передаётся value=None.

    Args:
        task_id: ID задачи.
        field: Имя колонки (проверяется против белого списка).
        value: Новое значение (или None для сброса).

    Raises:
        ValueError: Если передано недопустимое имя поля.
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    if field not in _ALLOWED_TASK_FIELDS:
        raise ValueError(f"Поле '{field}' не допускается для обновления")

    update_sql = f"UPDATE tasks SET {field} = ? WHERE id = ?"

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(update_sql, (value, task_id))
            await db.commit()
            logger.info("Задача #%d: поле '%s' обновлено на '%s'", task_id, field, value)
    except aiosqlite.Error as e:
        logger.error("Ошибка обновления задачи #%d: %s", task_id, e)
        raise


async def update_task_status(task_id: int, status: str) -> None:
    """
    Обновляет статус задачи по ID.

    Args:
        task_id: ID задачи.
        status: Новый статус ('в работе', 'выполнено', 'просрочено').

    Raises:
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    update_sql = "UPDATE tasks SET status = ? WHERE id = ?"

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(update_sql, (status, task_id))
            await db.commit()
            logger.info("Задача #%d: статус обновлён на '%s'", task_id, status)
    except aiosqlite.Error as e:
        logger.error("Ошибка обновления статуса задачи #%d: %s", task_id, e)
        raise


async def upsert_member(
    chat_id: str, username: str, display_name: str, last_seen: str
) -> None:
    """
    Добавляет или обновляет запись об участнике чата.

    Используется для сбора списка известных участников группы.
    INSERT OR REPLACE перезаписывает строку при совпадении PRIMARY KEY (chat_id, username).

    Args:
        chat_id: ID группового чата.
        username: Telegram username участника.
        display_name: Отображаемое имя (first_name + last_name).
        last_seen: Дата/время последнего взаимодействия (ISO 8601, GMT+3).

    Raises:
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    upsert_sql = """
        INSERT OR REPLACE INTO chat_members (chat_id, username, display_name, last_seen)
        VALUES (?, ?, ?, ?)
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(upsert_sql, (chat_id, username, display_name, last_seen))
            await db.commit()
            logger.debug("Участник %s обновлён в чате %s", username, chat_id)
    except aiosqlite.Error as e:
        logger.error("Ошибка upsert участника %s: %s", username, e)
        raise


async def get_chat_members(chat_id: str) -> list[dict[str, str]]:
    """
    Получает список всех известных участников указанного чата.

    Args:
        chat_id: ID группового чата.

    Returns:
        list[dict]: Список словарей с ключами: chat_id, username, display_name, last_seen.
        Пустой список, если участников нет.

    Raises:
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    select_sql = """
        SELECT chat_id, username, display_name, last_seen
        FROM chat_members
        WHERE chat_id = ?
        ORDER BY username ASC
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(select_sql, (chat_id,))
            rows = await cursor.fetchall()
            members = [dict(row) for row in rows]
            logger.info("Получено участников чата %s: %d", chat_id, len(members))
            return members
    except aiosqlite.Error as e:
        logger.error("Ошибка получения участников чата %s: %s", chat_id, e)
        raise


async def get_overdue_tasks(today_str: str) -> list[dict[str, Optional[str | int]]]:
    """
    Получает список задач со статусом 'в работе', у которых дедлайн истёк.

    Задача считается просроченной, если:
    - status = 'в работе'
    - deadline IS NOT NULL
    - deadline < today_str (формат YYYY-MM-DD)
    - chat_id не пустой (нужен для отправки уведомления)

    Args:
        today_str: Текущая дата в формате YYYY-MM-DD (GMT+3).

    Returns:
        list[dict]: Список просроченных задач. Пустой список, если таких нет.

    Raises:
        aiosqlite.Error: При ошибке выполнения SQL-запроса.
    """
    select_sql = """
        SELECT id, text, chat_id, assignee, deadline
        FROM tasks
        WHERE status = 'в работе'
          AND deadline IS NOT NULL
          AND deadline < ?
          AND chat_id != ''
        ORDER BY id ASC
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(select_sql, (today_str,))
            rows = await cursor.fetchall()
            tasks = [dict(row) for row in rows]
            logger.info("Найдено просроченных задач: %d", len(tasks))
            return tasks
    except aiosqlite.Error as e:
        logger.error("Ошибка поиска просроченных задач: %s", e)
        raise

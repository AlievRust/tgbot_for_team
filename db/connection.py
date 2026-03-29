"""
Модуль управления подключением к SQLite.

Содержит:
- DB_PATH: путь к файлу базы данных (tasks.db в корне проекта)
- init_db(): асинхронная функция создания таблицы tasks при первом запуске
"""

import logging
import os

import aiosqlite

logger = logging.getLogger(__name__)

# Путь к файлу БД — в корне проекта, рядом с main.py
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tasks.db")


async def init_db() -> None:
    """
    Инициализация базы данных: создаёт таблицу tasks, если она не существует.

    Схема таблицы:
    - id: INTEGER PRIMARY KEY AUTOINCREMENT — уникальный ID задачи
    - text: TEXT NOT NULL — текст задачи
    - user: TEXT NOT NULL — имя пользователя (username или display name)
    - created_at: TEXT NOT NULL — дата/время создания в формате ISO 8601 (GMT+3)

    Вызывать при старте бота в main.py перед запуском polling.
    """
    # SQL-запрос для создания таблицы (IF NOT EXISTS — безопасно при повторных вызовах)
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS tasks (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            text    TEXT    NOT NULL,
            user    TEXT    NOT NULL,
            created_at TEXT NOT NULL
        )
    """

    try:
        # Открываем асинхронное соединение с SQLite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(create_table_sql)
            await db.commit()
            logger.info("База данных инициализирована: %s", DB_PATH)
    except aiosqlite.Error as e:
        logger.error("Ошибка инициализации БД: %s", e)
        raise
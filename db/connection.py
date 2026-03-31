"""
Модуль управления подключением к SQLite.

Содержит:
- DB_PATH: путь к файлу базы данных (tasks.db в корне проекта)
- init_db(): создание таблиц tasks и chat_members, миграция новых колонок
"""

import logging
import os

import aiosqlite

logger = logging.getLogger(__name__)

# Путь к файлу БД — в корне проекта, рядом с main.py
_BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BASE, "..", "tasks.db")


async def _migrate_tasks_table(db: aiosqlite.Connection) -> None:
    """
    Миграция таблицы tasks: добавление новых колонок, если они не существуют.

    Добавляемые колонки:
    - chat_id: TEXT NOT NULL DEFAULT '' — ID чата для привязки задачи
    - assignee: TEXT DEFAULT NULL — username ответственного
    - deadline: TEXT DEFAULT NULL — дата дедлайна YYYY-MM-DD
    - status: TEXT NOT NULL DEFAULT 'в работе' — статус задачи

    Используем pragma table_info для проверки существования колонки,
    чтобы ALTER TABLE не падал при повторных запусках.
    """
    # Получаем список существующих колонок таблицы tasks
    cursor = await db.execute("PRAGMA table_info(tasks)")
    existing_columns = {row[1] for row in await cursor.fetchall()}

    # Словарь: имя_колонки -> SQL-определение для ALTER TABLE
    new_columns = {
        "chat_id": "TEXT NOT NULL DEFAULT ''",
        "assignee": "TEXT DEFAULT NULL",
        "deadline": "TEXT DEFAULT NULL",
        "status": "TEXT NOT NULL DEFAULT 'в работе'",
    }

    for col_name, col_def in new_columns.items():
        if col_name not in existing_columns:
            alter_sql = f"ALTER TABLE tasks ADD COLUMN {col_name} {col_def}"
            await db.execute(alter_sql)
            logger.info("Миграция tasks: добавлена колонка '%s'", col_name)


async def init_db() -> None:
    """
    Инициализация базы данных:
    1. Создаёт таблицу tasks, если она не существует.
    2. Мигрирует таблицу tasks (добавляет новые колонки).
    3. Создаёт таблицу chat_members, если она не существует.

    Схема tasks (итоговая):
    - id: INTEGER PRIMARY KEY AUTOINCREMENT
    - text: TEXT NOT NULL
    - user: TEXT NOT NULL
    - created_at: TEXT NOT NULL
    - chat_id: TEXT NOT NULL DEFAULT ''
    - assignee: TEXT DEFAULT NULL
    - deadline: TEXT DEFAULT NULL
    - status: TEXT NOT NULL DEFAULT 'в работе'

    Схема chat_members:
    - chat_id: TEXT NOT NULL
    - username: TEXT NOT NULL
    - display_name: TEXT NOT NULL
    - last_seen: TEXT NOT NULL
    - PRIMARY KEY (chat_id, username)

    Вызывать при старте бота перед запуском polling.
    """
    # Создание таблицы tasks (если не существует)
    create_tasks_sql = """
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            text        TEXT    NOT NULL,
            user        TEXT    NOT NULL,
            created_at  TEXT    NOT NULL,
            chat_id     TEXT    NOT NULL DEFAULT '',
            assignee    TEXT    DEFAULT NULL,
            deadline    TEXT    DEFAULT NULL,
            status      TEXT    NOT NULL DEFAULT 'в работе'
        )
    """

    # Создание таблицы chat_members (если не существует)
    create_members_sql = """
        CREATE TABLE IF NOT EXISTS chat_members (
            chat_id      TEXT    NOT NULL,
            username     TEXT    NOT NULL,
            display_name TEXT    NOT NULL,
            last_seen    TEXT    NOT NULL,
            PRIMARY KEY (chat_id, username)
        )
    """

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(create_tasks_sql)
            # Миграция для случаев, когда таблица уже существовала без новых колонок
            await _migrate_tasks_table(db)
            await db.execute(create_members_sql)
            await db.commit()
            logger.info("База данных инициализирована: %s", DB_PATH)
    except aiosqlite.Error as e:
        logger.error("Ошибка инициализации БД: %s", e)
        raise
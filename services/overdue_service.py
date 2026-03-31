"""
Модуль фоновой проверки просроченных задач.

Содержит:
- start_overdue_checker(): фоновая корутина, запускаемая при старте бота
- format_overdue_message(): формирование текста уведомления о просрочке

Логика:
- Каждые 1 час проверяет задачи со статусом 'в работе' и истёкшим дедлайном.
- Для каждой найденной задачи:
  1. Обновляет статус на 'просрочено'.
  2. Отправляет уведомление в чат с тегом ответственного.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot

from db import queries

logger = logging.getLogger(__name__)

# Часовой пояс Europe/Moscow (GMT+3)
_MOSCOW_TZ = timezone(timedelta(hours=3))

# Интервал проверки просрочки: 1 час (3600 секунд)
_CHECK_INTERVAL_SECONDS = 3600


def _today_moscow() -> str:
    """
    Возвращает текущую дату в формате YYYY-MM-DD (GMT+3).

    Returns:
        str: Пример: '2024-01-15'
    """
    return datetime.now(_MOSCOW_TZ).strftime("%Y-%m-%d")


def format_overdue_message(task: dict) -> str:
    """
    Формирует текст уведомления о просроченной задаче.

    Формат:
    - Если есть ответственный: ⚠️ Задача #<id> просрочена! @<assignee> — дедлайн был <deadline>
    - Если ответственного нет: ⚠️ Задача #<id> просрочена! Дедлайн был <deadline>

    Args:
        task: Словарь с полями задачи (id, text, assignee, deadline).

    Returns:
        str: Текст уведомления для отправки в чат.
    """
    assignee = task.get("assignee")
    deadline = task.get("deadline", "?")
    task_id = task.get("id", "?")

    if assignee:
        return (
            f"⚠️ Задача #{task_id} просрочена! "
            f"{assignee} — дедлайн был {deadline}"
        )
    return f"⚠️ Задача #{task_id} просрочена! Дедлайн был {deadline}"


async def _check_and_notify(bot: Bot) -> None:
    """
    Единичный цикл проверки: находит просроченные задачи,
    обновляет их статус и отправляет уведомления в чат.
    """
    today_str = _today_moscow()

    try:
        overdue_tasks = await queries.get_overdue_tasks(today_str)
    except Exception as e:
        logger.error("Ошибка при запросе просроченных задач: %s", e)
        return

    if not overdue_tasks:
        logger.debug("Просроченных задач не найдено (проверка %s)", today_str)
        return

    logger.info("Найдено просроченных задач: %d", len(overdue_tasks))

    for task in overdue_tasks:
        task_id = task["id"]
        chat_id = task.get("chat_id")

        # Обновляем статус задачи на 'просрочено'
        try:
            await queries.update_task_status(task_id, "просрочено")
        except Exception as e:
            logger.error(
                "Ошибка обновления статуса задачи #%d: %s", task_id, e
            )
            continue

        # Отправляем уведомление в чат
        if not chat_id:
            logger.warning(
                "Задача #%d просрочена, но chat_id пуст — уведомление пропущено",
                task_id,
            )
            continue

        message_text = format_overdue_message(task)
        try:
            await bot.send_message(chat_id=chat_id, text=message_text)
            logger.info(
                "Уведомление о просрочке задачи #%d отправлено в чат %s",
                task_id,
                chat_id,
            )
        except Exception as e:
            # Бот может быть удалён из чата, заблокирован и т.п.
            logger.error(
                "Ошибка отправки уведомления о просрочке задачи #%d в чат %s: %s",
                task_id,
                chat_id,
                e,
            )


async def start_overdue_checker(bot: Bot) -> None:
    """
    Фоновая корутина: бесконечный цикл проверки просроченных задач.

    Запускается через asyncio.create_task() при старте бота.
    Интервал проверки — 1 час (3600 секунд).

    Args:
        bot: Экземпляр aiogram Bot для отправки уведомлений.
    """
    logger.info("Фоновая проверка просрочки запущена (интервал: %d сек)", _CHECK_INTERVAL_SECONDS)

    # Небольшая задержка при старте, чтобы бот успел инициализироваться
    await asyncio.sleep(10)

    while True:
        try:
            await _check_and_notify(bot)
        except Exception as e:
            # Ловим непредвиденные ошибки, чтобы корутина не падала
            logger.error("Критическая ошибка в цикле проверки просрочки: %s", e)

        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
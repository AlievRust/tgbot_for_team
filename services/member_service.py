"""
Модуль бизнес-логики работы с участниками чата (chat_members).

Содержит:
- track_member(): запись/обновление участника в БД
- get_chat_members(): получение списка участников чата
- ensure_tracked(): утилита для автоматического трекинга из объекта Message
"""

import logging
from datetime import datetime, timezone, timedelta
from aiogram.types import Message

from db import queries

logger = logging.getLogger(__name__)

# Часовой пояс Europe/Moscow (GMT+3)
_MOSCOW_TZ = timezone(timedelta(hours=3))


def _now_moscow() -> str:
    """
    Возвращает текущую дату/время в формате ISO 8601 (GMT+3).

    Returns:
        str: Пример: '2024-01-15T14:30:00+03:00'
    """
    return datetime.now(_MOSCOW_TZ).isoformat()


def _extract_username(message: Message) -> str:
    """
    Извлекает username из объекта Message.

    Если username не задан (пользователь его скрыл), используется
    формат 'id:<user_id>' как уникальный идентификатор.

    Args:
        message: Объект сообщения aiogram.

    Returns:
        str: Username с '@' или 'id:<user_id>'.
    """
    if message.from_user and message.from_user.username:
        return f"@{message.from_user.username}"
    # Fallback: используем Telegram user_id как идентификатор
    user_id = message.from_user.id if message.from_user else 0
    return f"id:{user_id}"


def _extract_display_name(message: Message) -> str:
    """
    Извлекает отображаемое имя из объекта Message.

    Склеивает first_name и last_name через пробел.

    Args:
        message: Объект сообщения aiogram.

    Returns:
        str: Отображаемое имя (не пустое).
    """
    if not message.from_user:
        return "Unknown"
    parts = [message.from_user.first_name or ""]
    if message.from_user.last_name:
        parts.append(message.from_user.last_name)
    result = " ".join(parts).strip()
    return result or "Unknown"


async def track_member(
    chat_id: str, username: str, display_name: str
) -> None:
    """
    Записывает или обновляет участника чата в таблице chat_members.

    Используется для накопления списка известных участников группы.
    Вызывается при любом взаимодействии пользователя с ботом.

    Args:
        chat_id: ID группового чата (строка).
        username: Telegram username (с '@' или 'id:<user_id>').
        display_name: Отображаемое имя участника.
    """
    last_seen = _now_moscow()
    await queries.upsert_member(chat_id, username, display_name, last_seen)


async def get_chat_members(chat_id: str) -> list[dict[str, str]]:
    """
    Возвращает список всех известных участников указанного чата.

    Args:
        chat_id: ID группового чата.

    Returns:
        list[dict]: Список словарей с ключами: username, display_name.
    """
    members = await queries.get_chat_members(chat_id)
    # Оставляем только нужные поля для UI
    return [{"username": m["username"], "display_name": m["display_name"]} for m in members]


async def ensure_tracked(message: Message) -> None:
    """
    Утилита: извлекает данные из Message и вызывает track_member().

    Предназначена для вызова в начале каждого обработчика команд,
    чтобы автоматически собирать список участников группы.

    Args:
        message: Объект сообщения aiogram.
    """
    chat_id = str(message.chat.id)
    username = _extract_username(message)
    display_name = _extract_display_name(message)
    await track_member(chat_id, username, display_name)

"""
Обработчик команды /start.

Отправляет приветственное сообщение со списком доступных команд.
Бот работает только в групповых чатах — личные сообщения игнорируются.
"""

import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

logger = logging.getLogger(__name__)

# Создаём роутер для этого обработчика
router = Router()

# Текст приветственного сообщения с описанием команд
WELCOME_TEXT = (
    "👋 Привет! Я бот для управления задачами команды.\n\n"
    "<strong>Доступные команды:</strong>\n"
    "/add — добавить задачу\n"
    "/list — показать все задачи\n"
    "/list_csv — экспортировать задачи в CSV"
)


@router.message(CommandStart(), F.chat.type.in_({"group", "supergroup"}))
async def cmd_start(message: Message) -> None:
    """
    Обработчик команды /start в групповом чате.

    Фильтры:
        CommandStart() — реагирует только на /start
        F.chat.type.in_({"group", "supergroup"}) — только в группах

    Args:
        message: Объект входящего сообщения Telegram.
    """
    logger.info(
        "/start от %s в чате %s",
        message.from_user.full_name,
        message.chat.title,
    )
    await message.answer(WELCOME_TEXT)

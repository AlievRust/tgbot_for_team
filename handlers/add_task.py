"""
Обработчик команды /add — добавление задачи через FSM.

Двухшаговый процесс (FSM — Finite State Machine):
1. Пользователь отправляет /add → бот переходит в состояние waiting_for_text
   и просит ввести текст задачи
2. Пользователь отправляет текст → бот сохраняет задачу в БД и сбрасывает FSM

Бот работает только в групповых чатах — личные сообщения игнорируются.
"""

import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services import task_service, member_service

logger = logging.getLogger(__name__)

# Создаём роутер для этого обработчика
router = Router()


class AddTask(StatesGroup):
    """Состояния FSM для процесса добавления задачи."""
    # Ожидание текста задачи от пользователя
    waiting_for_text = State()


@router.message(Command("add"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_add(message: Message, state: FSMContext) -> None:
    """
    Первый шаг: пользователь отправил /add.

    Устанавливает FSM в состояние waiting_for_text,
    просит ввести текст задачи. Трекает участника.

    Фильтры:
        Command("add") — реагирует только на /add
        F.chat.type.in_({"group", "supergroup"}) — только в группах

    Args:
        message: Объект входящего сообщения Telegram.
        state: Контекст FSM для управления состояниями.
    """
    # Трекаем участника для накопления списка members
    await member_service.ensure_tracked(message)

    # Устанавливаем состояние — теперь бот ждёт текст задачи
    await state.set_state(AddTask.waiting_for_text)
    logger.info(
        "/add от %s в чате %s — ожидание текста",
        message.from_user.full_name,
        message.chat.title,
    )
    await message.answer("✏️ Введите текст задачи:")


@router.message(
    AddTask.waiting_for_text,
    F.chat.type.in_({"group", "supergroup"}),
)
async def process_task_text(message: Message, state: FSMContext) -> None:
    """
    Второй шаг: пользователь отправил текст задачи.

    Проверяет текст, сохраняет задачу в БД (с chat_id),
    сбрасывает FSM.

    Фильтры:
        AddTask.waiting_for_text — только если FSM в этом состоянии
        F.chat.type.in_({"group", "supergroup"}) — только в группах

    Args:
        message: Объект входящего сообщения с текстом задачи.
        state: Контекст FSM для сброса состояния.
    """
    # Текст задачи, убираем лишние пробелы
    task_text = message.text.strip() if message.text else ""

    # Валидация: текст не должен быть пустым
    if not task_text:
        logger.warning("Пустой текст от %s", message.from_user.full_name)
        await message.answer(
            "❌ Текст не может быть пустым."
            " Попробуйте ещё раз:"
        )
        return

    # Определяем имя пользователя: username если есть, иначе display name
    user = message.from_user.username or message.from_user.full_name

    # ID чата для привязки задачи
    chat_id = str(message.chat.id)

    try:
        # Сохраняем задачу через сервисный слой (с привязкой к чату)
        task_id = await task_service.create_task(
            text=task_text, user=user, chat_id=chat_id
        )
        logger.info(
            "Задача #%d создана: '%s' от %s в чате %s",
            task_id,
            task_text,
            user,
            chat_id,
        )
        await message.answer(f"✅ Задача #{task_id} добавлена: {task_text}")
    except Exception as e:
        logger.error("Ошибка при сохранении задачи: %s", e)
        await message.answer("❌ Ошибка сохранения задачи. Попробуйте позже.")
    finally:
        # Сбрасываем FSM, чтобы бот не застрял
        await state.clear()
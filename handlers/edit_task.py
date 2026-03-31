"""
Модуль обработчика команды /edit — редактирование существующей задачи.

Поток взаимодействия (через inline-кнопки):
1. /edit → бот просит ввести ID задачи
2. Пользователь вводит ID → проверка существования → кнопки выбора поля
3. Выбор поля → кнопки с вариантами значений
4. Выбор значения → сохранение → подтверждение

FSM-состояния:
- waiting_for_id: ожидание ввода ID задачи
- waiting_for_field: ожидание выбора поля (inline-кнопка)
"""

import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from services import member_service, task_service

logger = logging.getLogger(__name__)

# Роутер для регистрации в диспетчере
router = Router()

# Часовой пояс Europe/Moscow (GMT+3)
_MOSCOW_TZ = timezone(timedelta(hours=3))

# Префиксы для callback_data (формат: prefix:task_id:value)
_CB_FIELD = "ef"       # edit field
_CB_ASSIGNEE = "ea"    # edit assignee
_CB_DEADLINE = "ed"    # edit deadline
_CB_STATUS = "es"      # edit status


class EditTask(StatesGroup):
    """FSM-состояния для команды /edit."""
    waiting_for_id = State()
    waiting_for_field = State()


# ─── Утилиты для работы с датами ────────────────────────────────────────────


def _today_moscow() -> str:
    """Текущая дата в формате YYYY-MM-DD (GMT+3)."""
    return datetime.now(_MOSCOW_TZ).strftime("%Y-%m-%d")


def _offset_date(days: int) -> str:
    """
    Возвращает дату, сдвинутую на указанное количество дней от сегодня.

    Args:
        days: Сдвиг в днях (может быть отрицательным).

    Returns:
        str: Дата в формате YYYY-MM-DD.
    """
    target = datetime.now(_MOSCOW_TZ) + timedelta(days=days)
    return target.strftime("%Y-%m-%d")


# ─── Построители клавиатур ───────────────────────────────────────────────────


def _field_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора поля для редактирования.

    Три кнопки в один ряд: ответственный, дедлайн, статус.
    """
    buttons = [
        InlineKeyboardButton(
            text="📌 Назначить ответственного",
            callback_data=f"{_CB_FIELD}:{task_id}:assignee",
        ),
        InlineKeyboardButton(
            text="📅 Установить дедлайн",
            callback_data=f"{_CB_FIELD}:{task_id}:deadline",
        ),
        InlineKeyboardButton(
            text="✅ Сменить статус",
            callback_data=f"{_CB_FIELD}:{task_id}:status",
        ),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def _assignee_keyboard(
    task_id: int, members: list[dict[str, str]]
) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора ответственного из списка участников группы.

    Кнопки по 2 в ряд, последняя — «❌ Снять».
    """
    buttons = []
    for member in members:
        username = member["username"]
        display_name = member["display_name"]
        # Текст кнопки: "@username (Имя Фамилия)"
        button_text = f"{username} ({display_name})"
        buttons.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"{_CB_ASSIGNEE}:{task_id}:{username}",
            )
        )

    # Кнопка снятия ответственного
    buttons.append(
        InlineKeyboardButton(
            text="❌ Снять",
            callback_data=f"{_CB_ASSIGNEE}:{task_id}:none",
        )
    )

    # Раскладываем по 2 кнопки в ряд
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _deadline_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора дедлайна.

    Кнопки: Сегодня, Завтра, +3 дня, +7 дней (с подстановкой реальной даты),
    последняя — «❌ Снять».
    """
    today = _today_moscow()
    tomorrow = _offset_date(1)
    in_3_days = _offset_date(3)
    in_7_days = _offset_date(7)

    buttons = [
        [
            InlineKeyboardButton(
                text=f"Сегодня ({today})",
                callback_data=f"{_CB_DEADLINE}:{task_id}:{today}",
            ),
            InlineKeyboardButton(
                text=f"Завтра ({tomorrow})",
                callback_data=f"{_CB_DEADLINE}:{task_id}:{tomorrow}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"+3 дня ({in_3_days})",
                callback_data=f"{_CB_DEADLINE}:{task_id}:{in_3_days}",
            ),
            InlineKeyboardButton(
                text=f"+7 дней ({in_7_days})",
                callback_data=f"{_CB_DEADLINE}:{task_id}:{in_7_days}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Снять",
                callback_data=f"{_CB_DEADLINE}:{task_id}:none",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _status_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура смены статуса.

    Только «В работе» и «Выполнено» — «Просрочено» устанавливается автоматически.
    """
    buttons = [
        InlineKeyboardButton(
            text="В работе",
            callback_data=f"{_CB_STATUS}:{task_id}:в работе",
        ),
        InlineKeyboardButton(
            text="Выполнено",
            callback_data=f"{_CB_STATUS}:{task_id}:выполнено",
        ),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


# ─── Обработчики ─────────────────────────────────────────────────────────────


@router.message(F.text == "/edit")
async def cmd_edit(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /edit.
    Проверяет тип чата, трекает участника, запрашивает ID задачи.
    """
    # Игнорируем личные сообщения
    if message.chat.type not in ("group", "supergroup"):
        return

    # Трекаем участника
    await member_service.ensure_tracked(message)

    # Запрашиваем ID задачи
    await state.set_state(EditTask.waiting_for_id)
    await message.answer("✏️ Введите ID задачи для редактирования:")


@router.message(EditTask.waiting_for_id)
async def process_task_id(message: Message, state: FSMContext) -> None:
    """
    Обработчик ввода ID задачи.
    Проверяет, что введено число и задача существует.
    """
    raw_id = message.text.strip() if message.text else ""

    # Валидация: должно быть числом
    if not raw_id.isdigit():
        await message.answer("❌ ID задачи должен быть числом. Попробуйте снова:")
        return

    task_id = int(raw_id)

    # Поиск задачи в БД
    task = await task_service.get_task(task_id)
    if task is None:
        await message.answer(f"❌ Задача #{task_id} не найдена. Попробуйте другой ID:")
        return

    # Сохраняем ID задачи в состоянии
    await state.update_data(task_id=task_id)

    # Показываем клавиатуру выбора поля
    keyboard = _field_keyboard(task_id)
    await state.set_state(EditTask.waiting_for_field)
    await message.answer(
        f"📝 Задача #{task_id}: {task['text']}\n\nЧто хотите изменить?",
        reply_markup=keyboard,
    )


# ─── Callback: выбор поля ────────────────────────────────────────────────────


@router.callback_query(
    EditTask.waiting_for_field, F.data.startswith(f"{_CB_FIELD}:")
)
async def process_field_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик выбора поля для редактирования (ответственный/дедлайн/статус).
    Показывает соответствующую клавиатуру со значениями.
    """
    # Парсим callback_data: "ef:<task_id>:<field>"
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Ошибка выбора поля", show_alert=True)
        return

    task_id = int(parts[1])
    field = parts[2]

    # Трекаем участника (нажатие кнопки — тоже взаимодействие)
    await member_service.ensure_tracked(callback.message)

    try:
        if field == "assignee":
            # Получаем список участников чата
            chat_id = str(callback.message.chat.id)
            members = await member_service.get_chat_members(chat_id)

            if not members:
                await callback.message.edit_text(
                    "❌ Список участников группы пуст.\n"
                    "Сначала участники должны взаимодействовать с ботом "
                    "(написать любую команду).",
                )
                await state.clear()
                return

            keyboard = _assignee_keyboard(task_id, members)
            await callback.message.edit_text(
                f"📌 Назначить ответственного для задачи #{task_id}:",
                reply_markup=keyboard,
            )

        elif field == "deadline":
            keyboard = _deadline_keyboard(task_id)
            await callback.message.edit_text(
                f"📅 Установить дедлайн для задачи #{task_id}:",
                reply_markup=keyboard,
            )

        elif field == "status":
            keyboard = _status_keyboard(task_id)
            await callback.message.edit_text(
                f"✅ Сменить статус задачи #{task_id}:",
                reply_markup=keyboard,
            )

        else:
            await callback.answer("❌ Неизвестное поле", show_alert=True)
            return

        await callback.answer()

    except Exception as e:
        logger.error("Ошибка при выборе поля '%s' для задачи #%d: %s", field, task_id, e)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# ─── Callback: назначение ответственного ─────────────────────────────────────


@router.callback_query(
    EditTask.waiting_for_field, F.data.startswith(f"{_CB_ASSIGNEE}:")
)
async def process_assignee_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик выбора ответственного.
    Сохраняет выбранного username или снимает назначение.
    """
    # Парсим callback_data: "ea:<task_id>:<username|none>"
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Ошибка выбора", show_alert=True)
        return

    task_id = int(parts[1])
    username = parts[2]

    # Трекаем участника
    await member_service.ensure_tracked(callback.message)

    try:
        # Если "none" — снимаем ответственного (None)
        value = None if username == "none" else username
        await task_service.update_task_field(task_id, "assignee", value)

        if value:
            text = f"✅ Задача #{task_id}: ответственный назначен — {value}"
        else:
            text = f"✅ Задача #{task_id}: ответственный снят"

        await callback.message.edit_text(text)
        await state.clear()
        await callback.answer()

    except Exception as e:
        logger.error("Ошибка назначения ответственного для задачи #%d: %s", task_id, e)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# ─── Callback: установка дедлайна ────────────────────────────────────────────


@router.callback_query(
    EditTask.waiting_for_field, F.data.startswith(f"{_CB_DEADLINE}:")
)
async def process_deadline_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик выбора дедлайна.
    Сохраняет выбранную дату или снимает дедлайн.
    """
    # Парсим callback_data: "ed:<task_id>:<YYYY-MM-DD|none>"
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Ошибка выбора", show_alert=True)
        return

    task_id = int(parts[1])
    date_str = parts[2]

    # Трекаем участника
    await member_service.ensure_tracked(callback.message)

    try:
        # Если "none" — снимаем дедлайн (None)
        value = None if date_str == "none" else date_str
        await task_service.update_task_field(task_id, "deadline", value)

        if value:
            text = f"✅ Задача #{task_id}: дедлайн установлен на {value}"
        else:
            text = f"✅ Задача #{task_id}: дедлайн снят"

        await callback.message.edit_text(text)
        await state.clear()
        await callback.answer()

    except Exception as e:
        logger.error("Ошибка установки дедлайна для задачи #%d: %s", task_id, e)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# ─── Callback: смена статуса ─────────────────────────────────────────────────


@router.callback_query(
    EditTask.waiting_for_field, F.data.startswith(f"{_CB_STATUS}:")
)
async def process_status_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик смены статуса.
    Допустимо только «в работе» и «выполнено».
    """
    # Парсим callback_data: "es:<task_id>:<status>"
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Ошибка выбора", show_alert=True)
        return

    task_id = int(parts[1])
    status = parts[2]

    # Трекаем участника
    await member_service.ensure_tracked(callback.message)

    try:
        await task_service.update_task_field(task_id, "status", status)
        text = f"✅ Задача #{task_id}: статус изменён на «{status}»"
        await callback.message.edit_text(text)
        await state.clear()
        await callback.answer()

    except ValueError as e:
        # Ошибка валидации (например, попытались установить «просрочено»)
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error("Ошибка смены статуса задачи #%d: %s", task_id, e)
        await callback.answer("❌ Произошла ошибка", show_alert=True)
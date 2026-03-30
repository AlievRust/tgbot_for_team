"""
Обработчик команды /list_csv — экспорт всех задач в CSV-файл.

Получает задачи из БД через сервисный слой, генерирует CSV-файл в памяти
и отправляет как документ в групповой чат.
Личные сообщения игнорируются.
"""

import logging

from aiogram import Router, F
from aiogram.types import BufferedInputFile, Message
from aiogram.filters import Command

from services import task_service, csv_service

logger = logging.getLogger(__name__)

# Создаём роутер для этого обработчика
router = Router()


@router.message(Command("list_csv"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_list_csv(message: Message) -> None:
    """
    Обработчик команды /list_csv в групповом чате.

    Получает все задачи из БД, генерирует CSV-файл и отправляет как документ.
    Если список пуст — отправляет соответствующее сообщение (без файла).

    Фильтры:
        Command("list_csv") — реагирует только на /list_csv
        F.chat.type.in_({"group", "supergroup"}) — только в группах

    Args:
        message: Объект входящего сообщения Telegram.
    """
    logger.info(
        "/list_csv от %s в чате %s",
        message.from_user.full_name,
        message.chat.title,
    )

    try:
        # Получаем все задачи через сервисный слой
        tasks = await task_service.fetch_all_tasks()

        # Если задач нет — сообщаем об этом без отправки файла
        if not tasks:
            await message.answer("📋 Список задач пуст — нечего экспорт..")
            return

        # Генерируем CSV в памяти (BytesIO с UTF-8 BOM)
        csv_buffer = csv_service.generate_csv(tasks)

        # Отправляем CSV как документ в чат
        document = BufferedInputFile(
            file=csv_buffer.getvalue(),
            filename=csv_service.CSV_FILENAME,
        )
        await message.answer_document(
            document=document,
            caption="📊 Экспорт задач в CSV",
        )
        logger.info("CSV отправлен в чат %s", message.chat.title)

    except Exception as e:
        logger.error("Ошибка при экспорте задач в CSV: %s", e)
        await message.answer("❌ Ошибка экспорта. Попробуйте позже.")

"""
Модуль генерации CSV-файла из списка задач.

Содержит функцию:
- generate_csv(): создаёт CSV в памяти (BytesIO) с UTF-8 BOM для Excel-совместимости.
"""

import csv
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Имя файла для экспорта
CSV_FILENAME = "tasks.csv"

# Заголовки колонок в CSV
CSV_HEADERS = ["id", "text", "user", "created_at"]


def generate_csv(tasks: list[dict[str, Optional[str | int]]]) -> io.BytesIO:
    """
    Генерирует CSV-файл в памяти из списка задач.

    CSV-формат:
    - Кодировка: UTF-8 с BOM (маркер байтового порядка)
      — обеспечивает корректное отображение кириллицы в Excel
    - Разделитель: запятая (стандарт CSV)
    - Первая строка: заголовки колонок

    Args:
        tasks: Список словарей с ключами id, text, user, created_at.

    Returns:
        io.BytesIO: Поток байтов с CSV-данными.
            Указатель потока установлен в начало (seek(0)).
    """
    # Создаём текстовый буфер для записи CSV
    text_buffer = io.StringIO()

    # Пишем CSV с заголовками
    writer = csv.DictWriter(text_buffer, fieldnames=CSV_HEADERS)
    writer.writeheader()
    writer.writerows(tasks)

    # Получаем строку с CSV-данными
    csv_string = text_buffer.getvalue()

    # Кодируем в UTF-8 с BOM для совместимости с Excel
    # BOM = b'\xef\xbb\xbf' — сигнатура, которую Excel распознаёт как UTF-8
    csv_bytes = b"\xef\xbb\xbf" + csv_string.encode("utf-8")

    # Оборачиваем в BytesIO для передачи в aiogram как документ
    byte_buffer = io.BytesIO(csv_bytes)
    byte_buffer.seek(0)  # Устанавливаем указатель в начало

    logger.info("CSV сгенерирован: %d задач", len(tasks))
    return byte_buffer
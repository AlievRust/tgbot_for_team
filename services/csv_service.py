"""
Модуль генерации CSV-файла из списка задач.

Содержит функцию:
- generate_csv(): CSV в памяти (BytesIO), UTF-8 BOM
"""

import csv
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Имя файла для экспорта
CSV_FILENAME = "tasks.csv"

# Заголовки колонок в CSV (расширенные)
CSV_HEADERS = [
    "id", "text", "user", "created_at",
    "assignee", "deadline", "status",
]

# Разделитель полей: точка с запятой для корректного открытия
# в Excel с русской локалью (запятая воспринимается как разделитель разрядов)
CSV_DELIMITER = ";"


def generate_csv(tasks: list[dict[str, Optional[str | int]]]) -> io.BytesIO:
    """
    Генерирует CSV-файл в памяти из списка задач.

    CSV-формат:
    - Кодировка: UTF-8 с BOM (маркер байтового порядка)
      — обеспечивает корректное отображение кириллицы в Excel
    - Разделитель: точка с запятой (для Excel с русской локалью)
    - Первая строка: заголовки колонок
    - Дополнительные колонки: assignee, deadline, status

    Args:
        tasks: Список словарей с полями задачи.

    Returns:
        io.BytesIO: Поток байтов с CSV-данными.
            Указатель потока установлен в начало (seek(0)).
    """
    # Создаём текстовый буфер для записи CSV
    text_buffer = io.StringIO()

    # Пишем CSV с заголовками и разделителем ';'
    writer = csv.DictWriter(
        text_buffer, fieldnames=CSV_HEADERS, delimiter=CSV_DELIMITER
    )
    writer.writeheader()

    # Формируем строки, оставляя пустые значения для отсутствующих полей
    for task in tasks:
        row = {
            "id": task.get("id", ""),
            "text": task.get("text", ""),
            "user": task.get("user", ""),
            "created_at": task.get("created_at", ""),
            "assignee": task.get("assignee") or "",
            "deadline": task.get("deadline") or "",
            "status": task.get("status") or "",
        }
        writer.writerow(row)

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
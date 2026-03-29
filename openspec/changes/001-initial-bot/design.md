# Design: Базовый функционал TaskGroupBot

## Архитектура проекта

```
tgbot_for_team/
├── main.py                  # Точка входа: запуск бота
├── .env                     # BOT_TOKEN (не в репозитории)
├── .env.example             # Шаблон .env для разработчиков
├── .gitignore               # Исключения для Git
├── pyproject.toml           # Зависимости и метаданные
├── README.md                # Документация проекта
├── bot/
│   ├── __init__.py          # Инициализация пакета
│   └── creator.py           # Фабрика Bot (aiogram 3.x)
├── handlers/
│   ├── __init__.py          # Инициализация пакета
│   ├── start.py             # Обработчик /start
│   ├── add_task.py          # Обработчик /add (FSM)
│   ├── list_tasks.py        # Обработчик /list
│   └── export_csv.py        # Обработчик /list_csv
├── db/
│   ├── __init__.py          # Инициализация пакета
│   ├── connection.py        # Управление подключением к aiosqlite
│   └── queries.py           # SQL-запросы (CRUD операций с tasks)
└── services/
    ├── __init__.py          # Инициализация пакета
    ├── task_service.py      # Бизнес-логика работы с задачами
    └── csv_service.py       # Логика генерации CSV
```

## Ключевые компоненты

### main.py
- Загружает .env через python-dotenv
- Создаёт бота через bot/creator.py
- Инициализирует БД (создаёт таблицу при первом запуске)
- Регистрирует роутеры handlers
- Запускает polling

### bot/creator.py
- Функция `create_bot()` → возвращает экземпляр `Bot` и `Dispatcher`
- Читает BOT_TOKEN из окружения

### handlers/
- Каждый обработчик — отдельный модуль с роутером
- Все обработчики проверяют `message.chat.type != "group"` и `"supergroup"`
  и игнорируют личные сообщения
- **start.py**: отправляет приветствие со списком команд
- **add_task.py**: FSM с двумя состояниями:
  1. `AddTask.waiting_for_text` — после /add бот просит ввести текст
  2. Получает текст → сохраняет через task_service → подтверждает
- **list_tasks.py**: получает все задачи через task_service → форматирует → отправляет
- **export_csv.py**: получает все задачи → генерирует CSV через csv_service → отправляет документ

### db/connection.py
- Функция `get_db()` → возвращает путь к SQLite-файлу (tasks.db в корне)
- Функция `init_db()` → создаёт таблицу tasks если не существует

### db/queries.py
- `add_task(text, user, created_at)` → INSERT
- `get_all_tasks()` → SELECT * ORDER BY id

### services/task_service.py
- `create_task(text, user)` — формирует created_at (GMT+3), вызывает db.queries.add_task
- `fetch_all_tasks()` — вызывает db.queries.get_all_tasks, возвращает список dict
- `format_tasks_list(tasks)` — формирует строку для /list

### services/csv_service.py
- `generate_csv(tasks)` — создаёт CSV в памяти (io.StringIO), возвращает BytesIO
- Кодировка UTF-8 с BOM для Excel-совместимости

## Потоки данных

### /add
```
Пользователь → /add → handler проверяет тип чата
  →.enter(AddTask.waiting_for_text) → бот: "Введите текст задачи"
Пользователь → текст задачи → handler
  → task_service.create_task(text, user)
    → db.queries.add_task(text, user, created_at)
  → бот: "✅ Задача добавлена"
```

### /list
```
Пользователь → /list → handler проверяет тип чата
  → task_service.fetch_all_tasks()
    → db.queries.get_all_tasks()
  → task_service.format_tasks_list(tasks)
  → бот: список задач или "Список пуст"
```

### /list_csv
```
Пользователь → /list_csv → handler проверяет тип чата
  → task_service.fetch_all_tasks()
  → csv_service.generate_csv(tasks)
  → бот: отправка документа tasks.csv или "Список пуст"
```

## Обработка ошибок
- Личные сообщения: бот игнорирует (без ответа, чтобы не спамить)
- Пустой текст задачи при /add: бот просит повторить ввод
- Ошибки БД: логирование + сообщение пользователю об ошибке
# Tasks: Базовый функционал TaskGroupBot

## Подготовка проекта
- [x] Создать pyproject.toml с зависимостями (aiogram, aiosqlite, python-dotenv)
- [x] Создать .gitignore (Python, .env, *.db, __pycache__, .idea, .vscode)
- [x] Создать .env.example с шаблоном BOT_TOKEN (заблокировано политикой — формат в README.md)

## Точка входа
- [x] Создать main.py: загрузка .env, инициализация БД, создание бота, регистрация роутеров, запуск polling

## Пакет bot/
- [x] Создать bot/__init__.py
- [x] Создать bot/creator.py: фабрика Bot + Dispatcher

## Пакет db/
- [x] Создать db/__init__.py
- [x] Создать db/connection.py: путь к БД, функция init_db() с CREATE TABLE IF NOT EXISTS
- [x] Создать db/queries.py: add_task(), get_all_tasks()

## Пакет services/
- [x] Создать services/__init__.py
- [x] Создать services/task_service.py: create_task(), fetch_all_tasks(), format_tasks_list()
- [x] Создать services/csv_service.py: generate_csv() с UTF-8 BOM

## Пакет handlers/
- [x] Создать handlers/__init__.py
- [x] Создать handlers/start.py: обработчик /start с проверкой типа чата
- [x] Создать handlers/add_task.py: FSM (два состояния), проверка типа чата, валидация пустого текста
- [x] Создать handlers/list_tasks.py: обработчик /list с проверкой типа чата
- [x] Создать handlers/export_csv.py: обработчик /list_csv с проверкой типа чата

## Документация
- [x] Создать README.md с описанием проекта, установкой, запуском, командами бота
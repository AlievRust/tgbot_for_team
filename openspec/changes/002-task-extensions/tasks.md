# Tasks: Расширение задач — ответственный, дедлайн, статус, автопросрочка

## Миграция БД
- [x] Обновить db/connection.py: init_db() — CREATE TABLE chat_members, ALTER TABLE tasks (assignee, deadline, status, chat_id) с обработкой уже существующих колонок
- [x] Обновить db/queries.py: добавить get_task_by_id(), update_task_field(), update_task_status(), upsert_member(), get_chat_members(), get_overdue_tasks()

## Пакет services/
- [x] Создать services/member_service.py: track_member(), get_chat_members(), ensure_tracked()
- [x] Создать services/overdue_service.py: start_overdue_checker(bot), format_overdue_message(task)
- [x] Обновить services/task_service.py: create_task() — параметр chat_id; update_task_field(); формат format_tasks_list() с новыми полями
- [x] Обновить services/csv_service.py: новые колонки (Ответственный, Дедлайн, Статус) в заголовках и данных

## Пакет handlers/
- [x] Создать handlers/edit_task.py: FSM (waiting_for_id, waiting_for_field), inline-клавиатуры для выбора поля/ответственного/дедлайна/статуса, callback-обработчики
- [x] Обновить handlers/__init__.py: зарегистрировать роутер edit_task
- [x] Обновить handlers/add_task.py: добавить вызов member_service.ensure_tracked(), передать chat_id в create_task()
- [x] Обновить handlers/list_tasks.py: добавить вызов member_service.ensure_tracked()
- [x] Обновить handlers/export_csv.py: добавить вызов member_service.ensure_tracked()
- [x] Обновить handlers/start.py: добавить вызов member_service.ensure_tracked()

## Точка входа
- [x] Обновить main.py: запуск фоновой корутины overdue_service.start_overdue_checker(bot) через asyncio.create_task()

## Документация
- [x] Обновить README.md: описание /edit, новых полей в /list и /list_csv, описание автопросрочки
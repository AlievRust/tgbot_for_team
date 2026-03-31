 ## Design: Расширение задач — ответственный, дедлайн, статус, автопросрочка

## Изменения в архитектуре

### Новые файлы
```
handlers/
│   └── edit_task.py          # Обработчик /edit (FSM + inline-кнопки)
services/
│   ├── member_service.py     # Бизнес-логика работы с chat_members
│   └── overdue_service.py    # Фоновая корутина проверки просрочки
db/
│   └── queries.py            # Расширен: новые SQL-запросы
```

### Изменяемые файлы
```
db/connection.py   # init_db(): новая таблица chat_members, ALTER TABLE tasks
db/queries.py      # Новые запросы: update_task, get_task_by_id, upsert_member, get_overdue_tasks, ...
services/task_service.py  # Новые функции: update_task_field, format_tasks_list (обновлён)
services/csv_service.py   # Обновление: новые колонки в CSV
handlers/add_task.py      # Добавить вызов member_service.track_member()
handlers/list_tasks.py    # Добавить вызов member_service.track_member()
handlers/export_csv.py    # Добавить вызов member_service.track_member()
handlers/start.py         # Добавить вызов member_service.track_member()
handlers/__init__.py      # Зарегистрировать роутер edit_task
main.py                   # Запуск фоновой корутины overdue_service
```

## БД-схема

### Таблица tasks (миграция через ALTER TABLE)
```sql
-- Добавляемые колонки (с defaults для обратной совместимости)
ALTER TABLE tasks ADD COLUMN assignee TEXT DEFAULT NULL;
ALTER TABLE tasks ADD COLUMN deadline TEXT DEFAULT NULL;
ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'в работе';
```

### Таблица chat_members (создание)
```sql
CREATE TABLE IF NOT EXISTS chat_members (
    chat_id     TEXT    NOT NULL,
    username    TEXT    NOT NULL,
    display_name TEXT   NOT NULL,
    last_seen   TEXT    NOT NULL,
    PRIMARY KEY (chat_id, username)
);
```

> **Привязка задачи к чату:** Текущая схема не хранит chat_id в таблице tasks.
> Для фоновой проверки просрочки боту нужно знать, в какой чат отправлять уведомление.
> **Решение:** добавить колонку `chat_id TEXT NOT NULL` в таблицу tasks.
> При миграции — для существующих задач chat_id останется пустым (они не будут участвовать
> в автопросрочке, что допустимо для MVP).

### Итоговая схема tasks после миграции
```sql
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    text        TEXT    NOT NULL,
    user        TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    chat_id     TEXT    NOT NULL DEFAULT '',
    assignee    TEXT    DEFAULT NULL,
    deadline    TEXT    DEFAULT NULL,
    status      TEXT    NOT NULL DEFAULT 'в работе'
);
```

## Ключевые компоненты

### handlers/edit_task.py
FSM с состояниями:
1. `EditTask.waiting_for_id` — после /edit бот просит ввести ID
2. Пользователь вводит ID → проверка существования → inline-кнопки выбора поля
3. `EditTask.waiting_for_field` — callback_data = `edit_field:<task_id>:assignee|deadline|status`
4. В зависимости от выбора:
   - **assignee** → callback `edit_assignee:<task_id>:<username|none>`
   - **deadline** → callback `edit_deadline:<task_id>:<YYYY-MM-DD|none>`
   - **status** → callback `edit_status:<task_id>:в работе|выполнено`

**Inline-клавиатуры:**
- Выбор поля: 3 кнопки в один ряд
- Назначение ответственного: кнопки по 2 в ряд (username), последняя — «❌ Снять»
- Дедлайн: кнопки по 2 в ряд с рассчитанными датами, последняя — «❌ Снять»
- Статус: 2 кнопки в один ряд

После каждого действия — сообщение с подтверждением изменений.

### services/member_service.py
- `track_member(chat_id, username, display_name)` — UPSERT в chat_members
  (insert or replace по PK chat_id+username)
- `get_chat_members(chat_id)` → list[dict] — все известные участники чата
- `ensure_tracked(message)` — утилита: извлекает chat_id, username, display_name
  из объекта Message и вызывает track_member(). Используется во всех handlers.

### services/overdue_service.py
- `start_overdue_checker(bot)` — фоновая корутина
  ```
  while True:
      await asyncio.sleep(3600)  # 1 час
      overdue = get_overdue_tasks()  # SQL: status='в работе' AND deadline < today AND chat_id != ''
      for task in overdue:
          update_task_status(task['id'], 'просрочено')
          await bot.send_message(task['chat_id'], format_overdue_message(task))
  ```
- `format_overdue_message(task)` — формирует текст уведомления

### db/queries.py — новые запросы
- `update_task_field(task_id, field, value)` — UPDATE tasks SET <field>=? WHERE id=?
- `get_task_by_id(task_id)` — SELECT * FROM tasks WHERE id=?
- `upsert_member(chat_id, username, display_name, last_seen)` — INSERT OR REPLACE
- `get_chat_members(chat_id)` — SELECT * FROM chat_members WHERE chat_id=?
- `get_overdue_tasks(today_str)` — SELECT для задач с истёкшим дедлайном
- `update_task_status(task_id, status)` — UPDATE status WHERE id=?

### services/task_service.py — изменения
- `create_task()` — добавляет параметр `chat_id`
- `format_tasks_list()` — обновлённый формат вывода:
  ```
  1. Текст задачи — @user, создана 2024-01-15
     📌 Ответственный: @ivan | 📅 Дедлайн: 2024-01-20 | Статус: в работе
  ```
- `update_task_field(task_id, field, value)` — валидация поля + вызов db

### services/csv_service.py — изменения
- Заголовки CSV: ID, Текст, Автор, Дата создания, Ответственный, Дедлайн, Статус
- Соответствующее расширение генерации строк

## Потоки данных

### /edit (полный поток)
```
Пользователь → /edit → track_member()
  → enter(EditTask.waiting_for_id) → бот: "Введите ID задачи"
Пользователь → "5" → get_task_by_id(5)
  → не найдена: бот: "Задача не найдена"
  → найдена: inline-клавиатура [📌 Ответственный] [📅 Дедлайн] [✅ Статус]
     → enter(EditTask.waiting_for_field)

--- выбор "Ответственный" ---
Callback edit_field:5:assignee → get_chat_members(chat_id)
  → пустой список: бот: "Список участников пуст"
  → есть участники: inline-клавиатура [@user1] [@user2] / [❌ Снять]
Callback edit_assignee:5:@user1 → update_task_field(5, 'assignee', '@user1')
  → бот: "✅ Задача #5: ответственный изменён на @user1"

--- выбор "Дедлайн" ---
Callback edit_field:5:deadline → рассчитываем даты (сегодня, завтра, +3, +7 в GMT+3)
  → inline-клавиатура [Сегодня (2024-01-15)] [Завтра (2024-01-16)] / [+3 дня (2024-01-18)] [+7 дней (2024-01-22)] / [❌ Снять]
Callback edit_deadline:5:2024-01-20 → update_task_field(5, 'deadline', '2024-01-20')
  → бот: "✅ Задача #5: дедлайн установлен на 2024-01-20"

--- выбор "Статус" ---
Callback edit_field:5:status → inline-клавиатура [В работе] [Выполнено]
Callback edit_status:5:выполнено → update_task_field(5, 'status', 'выполнено')
  → бот: "✅ Задача #5: статус изменён на 'выполнено'"
```

### Фоновая проверка просрочки
```
main.py → asyncio.create_task(start_overdue_checker(bot))
  → every 3600s:
    → get_overdue_tasks(today_str)  -- status='в работе' AND deadline < today AND chat_id != ''
    → for each task:
      → update_task_status(task.id, 'просрочено')
      → bot.send_message(task.chat_id, "⚠️ Задача #5 просрочена! @ivan — дедлайн был 2024-01-20")
```

## Обработка ошибок
- Несуществующий ID задачи при /edit: сообщение об ошибке
- Пустой список members при назначении: сообщение «Сначала участники группы должны взаимодействовать с ботом»
- Некорректный ввод ID (не число): сообщение с просьбой ввести число
- Callback от устаревшего сообщения (нажатие на старые кнопки): try/except + тихое игнорирование
- Ошибка отправки уведомления о просрочке (бот удалён из чата и т.п.): логирование, продолжение цикла
# Миграции БД (Alembic)

Инициализация Alembic и стартовые ревизии будут выполнены на этапе 2 (модель данных).

Стандартные команды (актуальны после настройки Alembic):
- Инициализация: `alembic init migrations`
- Создать ревизию: `alembic revision -m "init schema"`
- Применить миграции: `alembic upgrade head`

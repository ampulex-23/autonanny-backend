-- ============================================================================
-- Миграция: 001_init_aerich
-- Описание: Инициализация системы миграций Aerich
-- Дата: 2025-10-26
-- Автор: AutoNanny Team
-- ============================================================================

-- Создание таблицы для отслеживания миграций
CREATE TABLE IF NOT EXISTS aerich (
    id SERIAL PRIMARY KEY,
    version VARCHAR(255) NOT NULL,
    app VARCHAR(100) NOT NULL,
    content JSONB NOT NULL
);

-- Создание индекса для быстрого поиска по версии
CREATE INDEX IF NOT EXISTS idx_aerich_version ON aerich(version);
CREATE INDEX IF NOT EXISTS idx_aerich_app ON aerich(app);

-- Вставка записи о начальной миграции (snapshot текущей схемы)
-- Эта запись указывает, что все существующие таблицы уже созданы
INSERT INTO aerich (version, app, content) 
VALUES (
    '0_initial',
    'models',
    '{"models": "existing_schema"}'::jsonb
)
ON CONFLICT DO NOTHING;

-- Комментарии к таблице
COMMENT ON TABLE aerich IS 'Таблица для отслеживания версий миграций базы данных';
COMMENT ON COLUMN aerich.version IS 'Версия миграции (например: 0_initial, 1_add_column)';
COMMENT ON COLUMN aerich.app IS 'Название приложения (обычно: models)';
COMMENT ON COLUMN aerich.content IS 'JSON с деталями миграции';

-- ============================================================================
-- Проверка успешности выполнения
-- ============================================================================
SELECT 
    'Aerich initialized successfully' AS status,
    COUNT(*) AS migration_count 
FROM aerich;

-- ============================================================================
-- Миграция: 004_add_sos_events_be_mvp_020
-- Описание: Создание таблицы для SOS-событий (экстренные вызовы)
-- Задача: BE-MVP-020
-- User Story: US-SAFE-01
-- Дата: 2025-10-27
-- Автор: AutoNanny Team
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Создание таблицы users.sos_event
-- ============================================================================

CREATE TABLE IF NOT EXISTS users.sos_event (
    id BIGSERIAL PRIMARY KEY,
    id_user BIGINT NOT NULL,
    id_order BIGINT NULL,
    latitude DOUBLE PRECISION NULL,
    longitude DOUBLE PRECISION NULL,
    message TEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    resolved_by BIGINT NULL,
    resolved_at TIMESTAMP NULL,
    datetime_create TIMESTAMP NULL DEFAULT NOW(),
    
    -- Внешние ключи
    CONSTRAINT fk_sos_event_user FOREIGN KEY (id_user) 
        REFERENCES users.user(id) ON DELETE CASCADE,
    CONSTRAINT fk_sos_event_order FOREIGN KEY (id_order) 
        REFERENCES data.order(id) ON DELETE SET NULL,
    CONSTRAINT fk_sos_event_resolved_by FOREIGN KEY (resolved_by) 
        REFERENCES users.user(id) ON DELETE SET NULL,
    
    -- Ограничения
    CONSTRAINT chk_sos_status CHECK (status IN ('active', 'resolved', 'cancelled'))
);

-- ============================================================================
-- 2. Добавление комментариев для документации
-- ============================================================================

COMMENT ON TABLE users.sos_event IS 'Таблица для хранения SOS-событий (экстренные вызовы)';
COMMENT ON COLUMN users.sos_event.id IS 'Уникальный идентификатор SOS-события';
COMMENT ON COLUMN users.sos_event.id_user IS 'ID пользователя, активировавшего SOS (водитель или родитель)';
COMMENT ON COLUMN users.sos_event.id_order IS 'ID связанного заказа (если есть)';
COMMENT ON COLUMN users.sos_event.latitude IS 'GPS широта местоположения';
COMMENT ON COLUMN users.sos_event.longitude IS 'GPS долгота местоположения';
COMMENT ON COLUMN users.sos_event.message IS 'Дополнительное сообщение от пользователя';
COMMENT ON COLUMN users.sos_event.status IS 'Статус события: active (активно), resolved (разрешено), cancelled (отменено)';
COMMENT ON COLUMN users.sos_event.resolved_by IS 'ID администратора, который разрешил ситуацию';
COMMENT ON COLUMN users.sos_event.resolved_at IS 'Время разрешения ситуации';
COMMENT ON COLUMN users.sos_event.datetime_create IS 'Время создания SOS-события';

-- ============================================================================
-- 3. Создание индексов для оптимизации
-- ============================================================================

-- Индекс для поиска активных SOS-событий
CREATE INDEX IF NOT EXISTS idx_sos_event_status ON users.sos_event(status) 
    WHERE status = 'active';

-- Индекс для поиска по пользователю
CREATE INDEX IF NOT EXISTS idx_sos_event_user ON users.sos_event(id_user);

-- Индекс для поиска по заказу
CREATE INDEX IF NOT EXISTS idx_sos_event_order ON users.sos_event(id_order) 
    WHERE id_order IS NOT NULL;

-- Индекс для поиска по времени создания (для аналитики)
CREATE INDEX IF NOT EXISTS idx_sos_event_datetime ON users.sos_event(datetime_create DESC);

-- Составной индекс для быстрого поиска активных событий по пользователю
CREATE INDEX IF NOT EXISTS idx_sos_event_user_status ON users.sos_event(id_user, status) 
    WHERE status = 'active';

-- ============================================================================
-- 4. Проверка результата
-- ============================================================================

DO $$
DECLARE
    table_exists BOOLEAN;
    index_count INTEGER;
BEGIN
    -- Проверка существования таблицы
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'users' 
        AND table_name = 'sos_event'
    ) INTO table_exists;
    
    -- Подсчет индексов
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'users' 
    AND tablename = 'sos_event';
    
    -- Проверка результата
    IF table_exists THEN
        RAISE NOTICE 'Миграция успешна: таблица users.sos_event создана';
        RAISE NOTICE 'Создано индексов: %', index_count;
    ELSE
        RAISE EXCEPTION 'Ошибка миграции: таблица users.sos_event не создана';
    END IF;
END $$;

-- ============================================================================
-- 5. Регистрация миграции в системе Aerich
-- ============================================================================

INSERT INTO aerich (version, app, content) 
VALUES (
    '4_add_sos_events_be_mvp_020',
    'models',
    '{
        "description": "Создание таблицы для SOS-событий",
        "task": "BE-MVP-020",
        "user_stories": ["US-SAFE-01"],
        "changes": [
            "Создана таблица users.sos_event",
            "Добавлены поля: id_user, id_order, latitude, longitude, message, status",
            "Добавлены поля для разрешения: resolved_by, resolved_at",
            "Созданы внешние ключи на users.user и data.order",
            "Созданы индексы для оптимизации поиска",
            "Добавлено ограничение на статус (active, resolved, cancelled)"
        ]
    }'::jsonb
)
ON CONFLICT DO NOTHING;

COMMIT;

-- ============================================================================
-- Проверка успешности выполнения
-- ============================================================================
SELECT 
    'Migration 004 completed successfully' AS status,
    NOW() AS completed_at;

-- ============================================================================
-- Примеры использования (для тестирования)
-- ============================================================================

-- Пример 1: Создание SOS-события
-- INSERT INTO users.sos_event (id_user, latitude, longitude, message, status)
-- VALUES (1, 55.751244, 37.618423, 'Экстренная ситуация!', 'active');

-- Пример 2: Поиск активных SOS-событий
-- SELECT * FROM users.sos_event WHERE status = 'active' ORDER BY datetime_create DESC;

-- Пример 3: Разрешение SOS-события администратором
-- UPDATE users.sos_event 
-- SET status = 'resolved', resolved_by = 3, resolved_at = NOW()
-- WHERE id = 1;

-- Пример 4: Статистика SOS-событий
-- SELECT 
--     status,
--     COUNT(*) as count,
--     AVG(EXTRACT(EPOCH FROM (resolved_at - datetime_create))/60) as avg_resolution_time_minutes
-- FROM users.sos_event
-- WHERE resolved_at IS NOT NULL
-- GROUP BY status;

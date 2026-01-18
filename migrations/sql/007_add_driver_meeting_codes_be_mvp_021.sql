-- ============================================================================
-- Миграция: 007_add_driver_meeting_codes_be_mvp_021
-- Описание: Создание таблицы для кодов встречи водителя с родителем
-- Задача: BE-MVP-021
-- User Story: US-SAFE-03, US-SAFE-04
-- Дата: 2025-10-27
-- Автор: AutoNanny Team
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Создание таблицы users.driver_meeting_code
-- ============================================================================

CREATE TABLE IF NOT EXISTS users.driver_meeting_code (
    id BIGSERIAL PRIMARY KEY,
    id_driver BIGINT NOT NULL,
    id_schedule_road BIGINT NOT NULL,
    meeting_code VARCHAR(4) NOT NULL,
    
    -- Статусы
    is_used BOOLEAN DEFAULT FALSE,
    verified_by BIGINT NULL,
    verified_at TIMESTAMP NULL,
    
    -- Время действия
    expires_at TIMESTAMP NOT NULL,
    
    -- Служебные поля
    isActive BOOLEAN DEFAULT TRUE,
    datetime_create TIMESTAMP NULL DEFAULT NOW(),
    
    -- Внешние ключи
    CONSTRAINT fk_meeting_code_driver FOREIGN KEY (id_driver) 
        REFERENCES users.user(id) ON DELETE CASCADE,
    CONSTRAINT fk_meeting_code_road FOREIGN KEY (id_schedule_road) 
        REFERENCES data.schedule_road(id) ON DELETE CASCADE,
    
    -- Ограничения
    CONSTRAINT chk_meeting_code_format CHECK (meeting_code ~ '^\d{4}$')
);

-- ============================================================================
-- 2. Добавление комментариев для документации
-- ============================================================================

COMMENT ON TABLE users.driver_meeting_code IS 'Таблица для хранения кодов встречи водителя с родителем';
COMMENT ON COLUMN users.driver_meeting_code.id IS 'Уникальный идентификатор кода';
COMMENT ON COLUMN users.driver_meeting_code.id_driver IS 'ID водителя';
COMMENT ON COLUMN users.driver_meeting_code.id_schedule_road IS 'ID маршрута';
COMMENT ON COLUMN users.driver_meeting_code.meeting_code IS '4-значный код встречи';
COMMENT ON COLUMN users.driver_meeting_code.is_used IS 'Использован ли код';
COMMENT ON COLUMN users.driver_meeting_code.verified_by IS 'ID родителя, который верифицировал';
COMMENT ON COLUMN users.driver_meeting_code.verified_at IS 'Время верификации';
COMMENT ON COLUMN users.driver_meeting_code.expires_at IS 'Время истечения кода';
COMMENT ON COLUMN users.driver_meeting_code.isActive IS 'Активность записи';
COMMENT ON COLUMN users.driver_meeting_code.datetime_create IS 'Время создания записи';

-- ============================================================================
-- 3. Создание индексов для оптимизации
-- ============================================================================

-- Индекс для поиска активных кодов водителя
CREATE INDEX IF NOT EXISTS idx_meeting_code_driver ON users.driver_meeting_code(id_driver, isActive) 
    WHERE isActive = TRUE AND is_used = FALSE;

-- Индекс для поиска по коду и маршруту
CREATE INDEX IF NOT EXISTS idx_meeting_code_verification 
    ON users.driver_meeting_code(meeting_code, id_schedule_road, isActive) 
    WHERE isActive = TRUE;

-- Индекс для поиска истекших кодов
CREATE INDEX IF NOT EXISTS idx_meeting_code_expires ON users.driver_meeting_code(expires_at) 
    WHERE isActive = TRUE;

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
        AND table_name = 'driver_meeting_code'
    ) INTO table_exists;
    
    -- Подсчет индексов
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'users' 
    AND tablename = 'driver_meeting_code';
    
    -- Проверка результата
    IF table_exists THEN
        RAISE NOTICE 'Миграция успешна: таблица users.driver_meeting_code создана';
        RAISE NOTICE 'Создано индексов: %', index_count;
    ELSE
        RAISE EXCEPTION 'Ошибка миграции: таблица users.driver_meeting_code не создана';
    END IF;
END $$;

-- ============================================================================
-- 5. Регистрация миграции в системе Aerich
-- ============================================================================

INSERT INTO aerich (version, app, content) 
VALUES (
    '7_add_driver_meeting_codes_be_mvp_021',
    'models',
    '{
        "description": "Создание таблицы для кодов встречи водителя с родителем",
        "task": "BE-MVP-021",
        "user_stories": ["US-SAFE-03", "US-SAFE-04"],
        "changes": [
            "Создана таблица users.driver_meeting_code",
            "Добавлены поля: id_driver, id_schedule_road, meeting_code",
            "Добавлены поля статуса: is_used, verified_by, verified_at",
            "Добавлено поле expires_at для времени истечения кода",
            "Добавлены внешние ключи на users.user и data.schedule_road",
            "Созданы индексы для оптимизации поиска",
            "Добавлено ограничение на формат кода (4 цифры)"
        ]
    }'::jsonb
)
ON CONFLICT DO NOTHING;

COMMIT;

-- ============================================================================
-- Проверка успешности выполнения
-- ============================================================================
SELECT 
    'Migration 007 completed successfully' AS status,
    NOW() AS completed_at;

-- ============================================================================
-- Примеры использования (для тестирования)
-- ============================================================================

-- Пример 1: Генерация кода встречи
-- INSERT INTO users.driver_meeting_code (id_driver, id_schedule_road, meeting_code, expires_at)
-- VALUES (123, 456, '1234', NOW() + INTERVAL '24 hours');

-- Пример 2: Поиск активных кодов водителя
-- SELECT * FROM users.driver_meeting_code 
-- WHERE id_driver = 123 
--   AND isActive = TRUE 
--   AND is_used = FALSE 
--   AND expires_at > NOW()
-- ORDER BY datetime_create DESC;

-- Пример 3: Верификация кода
-- SELECT * FROM users.driver_meeting_code 
-- WHERE meeting_code = '1234' 
--   AND id_schedule_road = 456 
--   AND isActive = TRUE 
--   AND is_used = FALSE 
--   AND expires_at > NOW();

-- Пример 4: Пометить код как использованный
-- UPDATE users.driver_meeting_code 
-- SET is_used = TRUE, 
--     verified_by = 789, 
--     verified_at = NOW() 
-- WHERE id = 1;

-- Пример 5: Статистика по верификациям
-- SELECT 
--     d.name as driver_name,
--     d.surname as driver_surname,
--     COUNT(*) as total_codes,
--     COUNT(CASE WHEN is_used THEN 1 END) as verified_codes,
--     COUNT(CASE WHEN expires_at < NOW() THEN 1 END) as expired_codes
-- FROM users.driver_meeting_code c
-- JOIN users.user d ON c.id_driver = d.id
-- WHERE c.isActive = TRUE
-- GROUP BY d.id, d.name, d.surname
-- ORDER BY total_codes DESC;

-- Пример 6: Очистка истекших кодов (можно запускать периодически)
-- UPDATE users.driver_meeting_code 
-- SET isActive = FALSE 
-- WHERE expires_at < NOW() - INTERVAL '7 days' 
--   AND isActive = TRUE;

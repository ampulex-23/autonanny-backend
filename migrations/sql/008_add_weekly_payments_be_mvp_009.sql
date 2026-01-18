-- ============================================================================
-- Миграция: 008_add_weekly_payments_be_mvp_009
-- Описание: Создание таблиц для автоматического еженедельного списания
-- Задача: BE-MVP-009
-- User Story: US-PAY-02
-- Дата: 2025-10-27
-- Автор: AutoNanny Team
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Создание таблицы users.weekly_payment_schedule
-- ============================================================================

CREATE TABLE IF NOT EXISTS users.weekly_payment_schedule (
    id BIGSERIAL PRIMARY KEY,
    id_user BIGINT NOT NULL,
    id_schedule BIGINT NOT NULL,
    
    -- Сумма и карта
    amount DECIMAL(10, 2) NOT NULL,
    id_card BIGINT NULL,
    
    -- Расписание
    next_payment_date DATE NOT NULL,
    last_payment_date DATE NULL,
    
    -- Статусы
    status VARCHAR(20) DEFAULT 'active',
    failed_attempts INTEGER DEFAULT 0,
    last_error TEXT NULL,
    
    -- Служебные поля
    isActive BOOLEAN DEFAULT TRUE,
    datetime_create TIMESTAMP NULL DEFAULT NOW(),
    datetime_update TIMESTAMP NULL,
    
    -- Внешние ключи
    CONSTRAINT fk_payment_schedule_user FOREIGN KEY (id_user) 
        REFERENCES users.user(id) ON DELETE CASCADE,
    CONSTRAINT fk_payment_schedule_schedule FOREIGN KEY (id_schedule) 
        REFERENCES data.schedule(id) ON DELETE CASCADE,
    CONSTRAINT fk_payment_schedule_card FOREIGN KEY (id_card) 
        REFERENCES users.debit_card(id) ON DELETE SET NULL,
    
    -- Ограничения
    CONSTRAINT chk_payment_status CHECK (status IN ('active', 'suspended', 'cancelled')),
    CONSTRAINT chk_payment_amount CHECK (amount > 0)
);

-- ============================================================================
-- 2. Создание таблицы users.weekly_payment_history
-- ============================================================================

CREATE TABLE IF NOT EXISTS users.weekly_payment_history (
    id BIGSERIAL PRIMARY KEY,
    id_schedule_payment BIGINT NOT NULL,
    id_user BIGINT NOT NULL,
    id_schedule BIGINT NOT NULL,
    
    -- Детали платежа
    amount DECIMAL(10, 2) NOT NULL,
    id_card BIGINT NULL,
    
    -- Результат
    status VARCHAR(20) NOT NULL,
    error_message TEXT NULL,
    payment_id TEXT NULL,
    
    -- Служебные поля
    datetime_create TIMESTAMP NULL DEFAULT NOW(),
    
    -- Внешние ключи
    CONSTRAINT fk_payment_history_schedule FOREIGN KEY (id_schedule_payment) 
        REFERENCES users.weekly_payment_schedule(id) ON DELETE CASCADE,
    CONSTRAINT fk_payment_history_user FOREIGN KEY (id_user) 
        REFERENCES users.user(id) ON DELETE CASCADE,
    
    -- Ограничения
    CONSTRAINT chk_history_status CHECK (status IN ('success', 'failed', 'pending'))
);

-- ============================================================================
-- 3. Добавление комментариев для документации
-- ============================================================================

COMMENT ON TABLE users.weekly_payment_schedule IS 'Таблица для хранения расписания еженедельных списаний';
COMMENT ON COLUMN users.weekly_payment_schedule.id IS 'Уникальный идентификатор расписания';
COMMENT ON COLUMN users.weekly_payment_schedule.id_user IS 'ID родителя';
COMMENT ON COLUMN users.weekly_payment_schedule.id_schedule IS 'ID контракта/графика';
COMMENT ON COLUMN users.weekly_payment_schedule.amount IS 'Сумма еженедельного списания';
COMMENT ON COLUMN users.weekly_payment_schedule.next_payment_date IS 'Дата следующего списания';
COMMENT ON COLUMN users.weekly_payment_schedule.status IS 'Статус: active, suspended, cancelled';
COMMENT ON COLUMN users.weekly_payment_schedule.failed_attempts IS 'Количество неудачных попыток';

COMMENT ON TABLE users.weekly_payment_history IS 'Таблица для хранения истории еженедельных списаний';
COMMENT ON COLUMN users.weekly_payment_history.status IS 'Результат: success, failed, pending';
COMMENT ON COLUMN users.weekly_payment_history.payment_id IS 'ID платежа в платежной системе';

-- ============================================================================
-- 4. Создание индексов для оптимизации
-- ============================================================================

-- Индекс для поиска активных расписаний по дате
CREATE INDEX IF NOT EXISTS idx_payment_schedule_active_date 
    ON users.weekly_payment_schedule(next_payment_date, isActive, status) 
    WHERE isActive = TRUE AND status = 'active';

-- Индекс для поиска расписаний пользователя
CREATE INDEX IF NOT EXISTS idx_payment_schedule_user 
    ON users.weekly_payment_schedule(id_user, isActive);

-- Индекс для поиска расписаний контракта
CREATE INDEX IF NOT EXISTS idx_payment_schedule_contract 
    ON users.weekly_payment_schedule(id_schedule, isActive);

-- Индекс для истории платежей
CREATE INDEX IF NOT EXISTS idx_payment_history_schedule 
    ON users.weekly_payment_history(id_schedule_payment, datetime_create DESC);

-- Индекс для истории по пользователю
CREATE INDEX IF NOT EXISTS idx_payment_history_user 
    ON users.weekly_payment_history(id_user, datetime_create DESC);

-- ============================================================================
-- 5. Проверка результата
-- ============================================================================

DO $$
DECLARE
    schedule_table_exists BOOLEAN;
    history_table_exists BOOLEAN;
    index_count INTEGER;
BEGIN
    -- Проверка существования таблиц
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'users' 
        AND table_name = 'weekly_payment_schedule'
    ) INTO schedule_table_exists;
    
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'users' 
        AND table_name = 'weekly_payment_history'
    ) INTO history_table_exists;
    
    -- Подсчет индексов
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'users' 
    AND (tablename = 'weekly_payment_schedule' OR tablename = 'weekly_payment_history');
    
    -- Проверка результата
    IF schedule_table_exists AND history_table_exists THEN
        RAISE NOTICE 'Миграция успешна: таблицы созданы';
        RAISE NOTICE 'Создано индексов: %', index_count;
    ELSE
        RAISE EXCEPTION 'Ошибка миграции: таблицы не созданы';
    END IF;
END $$;

-- ============================================================================
-- 6. Регистрация миграции в системе Aerich
-- ============================================================================

INSERT INTO aerich (version, app, content) 
VALUES (
    '8_add_weekly_payments_be_mvp_009',
    'models',
    '{
        "description": "Создание таблиц для автоматического еженедельного списания",
        "task": "BE-MVP-009",
        "user_story": "US-PAY-02",
        "changes": [
            "Создана таблица users.weekly_payment_schedule",
            "Создана таблица users.weekly_payment_history",
            "Добавлены поля для расписания и статусов",
            "Добавлены внешние ключи на users, schedule, debit_card",
            "Созданы индексы для оптимизации cron-job",
            "Добавлены ограничения на статусы и суммы"
        ]
    }'::jsonb
)
ON CONFLICT DO NOTHING;

COMMIT;

-- ============================================================================
-- Проверка успешности выполнения
-- ============================================================================
SELECT 
    'Migration 008 completed successfully' AS status,
    NOW() AS completed_at;

-- ============================================================================
-- Примеры использования (для тестирования)
-- ============================================================================

-- Пример 1: Создание расписания платежей
-- INSERT INTO users.weekly_payment_schedule (id_user, id_schedule, amount, id_card, next_payment_date)
-- VALUES (123, 456, 5000.00, 789, CURRENT_DATE + INTERVAL '7 days');

-- Пример 2: Поиск активных расписаний для списания сегодня
-- SELECT * FROM users.weekly_payment_schedule 
-- WHERE isActive = TRUE 
--   AND status = 'active' 
--   AND next_payment_date <= CURRENT_DATE
-- ORDER BY next_payment_date;

-- Пример 3: Логирование успешного платежа
-- INSERT INTO users.weekly_payment_history (id_schedule_payment, id_user, id_schedule, amount, id_card, status, payment_id)
-- VALUES (1, 123, 456, 5000.00, 789, 'success', 'tinkoff_payment_12345');

-- Пример 4: Приостановка расписания после неудач
-- UPDATE users.weekly_payment_schedule 
-- SET status = 'suspended', 
--     failed_attempts = failed_attempts + 1,
--     last_error = 'Insufficient funds',
--     datetime_update = NOW()
-- WHERE id = 1;

-- Пример 5: Статистика по платежам
-- SELECT 
--     u.name,
--     u.surname,
--     COUNT(*) as total_payments,
--     COUNT(CASE WHEN h.status = 'success' THEN 1 END) as successful,
--     COUNT(CASE WHEN h.status = 'failed' THEN 1 END) as failed,
--     SUM(CASE WHEN h.status = 'success' THEN h.amount ELSE 0 END) as total_paid
-- FROM users.weekly_payment_history h
-- JOIN users.user u ON h.id_user = u.id
-- WHERE h.datetime_create >= CURRENT_DATE - INTERVAL '30 days'
-- GROUP BY u.id, u.name, u.surname
-- ORDER BY total_paid DESC;

-- Пример 6: Возобновление приостановленного расписания
-- UPDATE users.weekly_payment_schedule 
-- SET status = 'active',
--     failed_attempts = 0,
--     last_error = NULL,
--     next_payment_date = CURRENT_DATE + INTERVAL '7 days',
--     datetime_update = NOW()
-- WHERE id = 1 AND status = 'suspended';

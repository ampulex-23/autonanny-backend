-- ============================================================================
-- Миграция: 005_add_emergency_contacts_be_mvp_018
-- Описание: Создание таблицы для экстренных контактов детей
-- Задача: BE-MVP-018
-- User Story: US-CHILD-03
-- Дата: 2025-10-27
-- Автор: AutoNanny Team
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Создание таблицы users.child_emergency_contact
-- ============================================================================

CREATE TABLE IF NOT EXISTS users.child_emergency_contact (
    id BIGSERIAL PRIMARY KEY,
    id_child BIGINT NOT NULL,
    name TEXT NOT NULL,
    relationship TEXT NOT NULL,
    phone TEXT NOT NULL,
    priority INTEGER DEFAULT 1,
    notes TEXT NULL,
    isActive BOOLEAN DEFAULT TRUE,
    datetime_create TIMESTAMP NULL DEFAULT NOW(),
    
    -- Внешний ключ
    CONSTRAINT fk_emergency_contact_child FOREIGN KEY (id_child) 
        REFERENCES users.child(id) ON DELETE CASCADE,
    
    -- Ограничения
    CONSTRAINT chk_priority_positive CHECK (priority > 0),
    CONSTRAINT chk_phone_format CHECK (phone ~ '^\+7 \(\d{3}\) \d{3} \d{2} \d{2}$')
);

-- ============================================================================
-- 2. Добавление комментариев для документации
-- ============================================================================

COMMENT ON TABLE users.child_emergency_contact IS 'Таблица для хранения экстренных контактов детей';
COMMENT ON COLUMN users.child_emergency_contact.id IS 'Уникальный идентификатор контакта';
COMMENT ON COLUMN users.child_emergency_contact.id_child IS 'ID ребенка';
COMMENT ON COLUMN users.child_emergency_contact.name IS 'Имя контактного лица';
COMMENT ON COLUMN users.child_emergency_contact.relationship IS 'Родство/отношение (мама, папа, бабушка, дедушка, тетя, дядя, друг семьи)';
COMMENT ON COLUMN users.child_emergency_contact.phone IS 'Телефон в формате +7 (999) 999 99 99';
COMMENT ON COLUMN users.child_emergency_contact.priority IS 'Приоритет контакта (1 - первый, 2 - второй и т.д.)';
COMMENT ON COLUMN users.child_emergency_contact.notes IS 'Дополнительные заметки о контакте';
COMMENT ON COLUMN users.child_emergency_contact.isActive IS 'Активность контакта (мягкое удаление)';
COMMENT ON COLUMN users.child_emergency_contact.datetime_create IS 'Время создания записи';

-- ============================================================================
-- 3. Создание индексов для оптимизации
-- ============================================================================

-- Индекс для поиска по ребенку
CREATE INDEX IF NOT EXISTS idx_emergency_contact_child ON users.child_emergency_contact(id_child) 
    WHERE isActive = TRUE;

-- Индекс для поиска активных контактов с приоритетом
CREATE INDEX IF NOT EXISTS idx_emergency_contact_child_priority 
    ON users.child_emergency_contact(id_child, priority) 
    WHERE isActive = TRUE;

-- Индекс для поиска по телефону (для дедупликации)
CREATE INDEX IF NOT EXISTS idx_emergency_contact_phone ON users.child_emergency_contact(phone) 
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
        AND table_name = 'child_emergency_contact'
    ) INTO table_exists;
    
    -- Подсчет индексов
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'users' 
    AND tablename = 'child_emergency_contact';
    
    -- Проверка результата
    IF table_exists THEN
        RAISE NOTICE 'Миграция успешна: таблица users.child_emergency_contact создана';
        RAISE NOTICE 'Создано индексов: %', index_count;
    ELSE
        RAISE EXCEPTION 'Ошибка миграции: таблица users.child_emergency_contact не создана';
    END IF;
END $$;

-- ============================================================================
-- 5. Регистрация миграции в системе Aerich
-- ============================================================================

INSERT INTO aerich (version, app, content) 
VALUES (
    '5_add_emergency_contacts_be_mvp_018',
    'models',
    '{
        "description": "Создание таблицы для экстренных контактов детей",
        "task": "BE-MVP-018",
        "user_stories": ["US-CHILD-03"],
        "changes": [
            "Создана таблица users.child_emergency_contact",
            "Добавлены поля: id_child, name, relationship, phone, priority, notes",
            "Добавлен внешний ключ на users.child",
            "Созданы индексы для оптимизации поиска",
            "Добавлено ограничение на формат телефона",
            "Добавлено ограничение на положительный приоритет"
        ]
    }'::jsonb
)
ON CONFLICT DO NOTHING;

COMMIT;

-- ============================================================================
-- Проверка успешности выполнения
-- ============================================================================
SELECT 
    'Migration 005 completed successfully' AS status,
    NOW() AS completed_at;

-- ============================================================================
-- Примеры использования (для тестирования)
-- ============================================================================

-- Пример 1: Создание экстренного контакта
-- INSERT INTO users.child_emergency_contact (id_child, name, relationship, phone, priority)
-- VALUES (1, 'Иванова Мария Петровна', 'мама', '+7 (999) 123 45 67', 1);

-- Пример 2: Получение всех контактов ребенка по приоритету
-- SELECT * FROM users.child_emergency_contact 
-- WHERE id_child = 1 AND isActive = TRUE 
-- ORDER BY priority;

-- Пример 3: Поиск контактов для нескольких детей (для SOS)
-- SELECT c.*, ch.name as child_name
-- FROM users.child_emergency_contact c
-- JOIN users.child ch ON c.id_child = ch.id
-- WHERE c.id_child IN (1, 2, 3) AND c.isActive = TRUE
-- ORDER BY c.id_child, c.priority;

-- Пример 4: Статистика по контактам
-- SELECT 
--     relationship,
--     COUNT(*) as count,
--     AVG(priority) as avg_priority
-- FROM users.child_emergency_contact
-- WHERE isActive = TRUE
-- GROUP BY relationship
-- ORDER BY count DESC;

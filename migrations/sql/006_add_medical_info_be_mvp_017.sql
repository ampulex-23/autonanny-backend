-- ============================================================================
-- Миграция: 006_add_medical_info_be_mvp_017
-- Описание: Создание таблицы для медицинской информации детей
-- Задача: BE-MVP-017
-- User Story: US-CHILD-02
-- Дата: 2025-10-27
-- Автор: AutoNanny Team
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Создание таблицы users.child_medical_info
-- ============================================================================

CREATE TABLE IF NOT EXISTS users.child_medical_info (
    id BIGSERIAL PRIMARY KEY,
    id_child BIGINT NOT NULL,
    
    -- Медицинская информация
    allergies TEXT NULL,
    chronic_diseases TEXT NULL,
    medications TEXT NULL,
    medical_policy_number TEXT NULL,
    blood_type VARCHAR(10) NULL,
    
    -- Дополнительные заметки
    special_needs TEXT NULL,
    doctor_notes TEXT NULL,
    
    -- Документы
    policy_document_path TEXT NULL,
    medical_certificate_path TEXT NULL,
    
    -- Служебные поля
    isActive BOOLEAN DEFAULT TRUE,
    datetime_create TIMESTAMP NULL DEFAULT NOW(),
    datetime_update TIMESTAMP NULL,
    
    -- Внешний ключ
    CONSTRAINT fk_medical_info_child FOREIGN KEY (id_child) 
        REFERENCES users.child(id) ON DELETE CASCADE,
    
    -- Ограничения
    CONSTRAINT chk_blood_type_format CHECK (
        blood_type IS NULL OR 
        blood_type ~ '^(A|B|AB|O)[+-]$'
    ),
    
    -- Уникальность: один ребенок - одна активная медицинская карта
    CONSTRAINT uq_child_medical_info_active UNIQUE (id_child) 
        WHERE isActive = TRUE
);

-- ============================================================================
-- 2. Добавление комментариев для документации
-- ============================================================================

COMMENT ON TABLE users.child_medical_info IS 'Таблица для хранения медицинской информации детей';
COMMENT ON COLUMN users.child_medical_info.id IS 'Уникальный идентификатор медицинской карты';
COMMENT ON COLUMN users.child_medical_info.id_child IS 'ID ребенка';
COMMENT ON COLUMN users.child_medical_info.allergies IS 'Аллергии (текстовое описание)';
COMMENT ON COLUMN users.child_medical_info.chronic_diseases IS 'Хронические заболевания';
COMMENT ON COLUMN users.child_medical_info.medications IS 'Медикаменты (название, дозировка, график приема)';
COMMENT ON COLUMN users.child_medical_info.medical_policy_number IS 'Номер медицинского полиса';
COMMENT ON COLUMN users.child_medical_info.blood_type IS 'Группа крови (A+, A-, B+, B-, AB+, AB-, O+, O-)';
COMMENT ON COLUMN users.child_medical_info.special_needs IS 'Особые потребности (инвалидность, диета и т.д.)';
COMMENT ON COLUMN users.child_medical_info.doctor_notes IS 'Рекомендации врача';
COMMENT ON COLUMN users.child_medical_info.policy_document_path IS 'Путь к скану медицинского полиса';
COMMENT ON COLUMN users.child_medical_info.medical_certificate_path IS 'Путь к медицинской справке';
COMMENT ON COLUMN users.child_medical_info.isActive IS 'Активность записи (мягкое удаление)';
COMMENT ON COLUMN users.child_medical_info.datetime_create IS 'Время создания записи';
COMMENT ON COLUMN users.child_medical_info.datetime_update IS 'Время последнего обновления';

-- ============================================================================
-- 3. Создание индексов для оптимизации
-- ============================================================================

-- Индекс для поиска по ребенку
CREATE INDEX IF NOT EXISTS idx_medical_info_child ON users.child_medical_info(id_child) 
    WHERE isActive = TRUE;

-- Индекс для поиска детей с аллергиями
CREATE INDEX IF NOT EXISTS idx_medical_info_allergies ON users.child_medical_info(id_child) 
    WHERE isActive = TRUE AND allergies IS NOT NULL;

-- Индекс для поиска детей с хроническими заболеваниями
CREATE INDEX IF NOT EXISTS idx_medical_info_chronic ON users.child_medical_info(id_child) 
    WHERE isActive = TRUE AND chronic_diseases IS NOT NULL;

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
        AND table_name = 'child_medical_info'
    ) INTO table_exists;
    
    -- Подсчет индексов
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'users' 
    AND tablename = 'child_medical_info';
    
    -- Проверка результата
    IF table_exists THEN
        RAISE NOTICE 'Миграция успешна: таблица users.child_medical_info создана';
        RAISE NOTICE 'Создано индексов: %', index_count;
    ELSE
        RAISE EXCEPTION 'Ошибка миграции: таблица users.child_medical_info не создана';
    END IF;
END $$;

-- ============================================================================
-- 5. Регистрация миграции в системе Aerich
-- ============================================================================

INSERT INTO aerich (version, app, content) 
VALUES (
    '6_add_medical_info_be_mvp_017',
    'models',
    '{
        "description": "Создание таблицы для медицинской информации детей",
        "task": "BE-MVP-017",
        "user_stories": ["US-CHILD-02"],
        "changes": [
            "Создана таблица users.child_medical_info",
            "Добавлены поля: allergies, chronic_diseases, medications, medical_policy_number, blood_type",
            "Добавлены поля: special_needs, doctor_notes",
            "Добавлены поля для документов: policy_document_path, medical_certificate_path",
            "Добавлен внешний ключ на users.child",
            "Созданы индексы для оптимизации поиска",
            "Добавлено ограничение на формат группы крови",
            "Добавлено ограничение уникальности активной медицинской карты на ребенка"
        ]
    }'::jsonb
)
ON CONFLICT DO NOTHING;

COMMIT;

-- ============================================================================
-- Проверка успешности выполнения
-- ============================================================================
SELECT 
    'Migration 006 completed successfully' AS status,
    NOW() AS completed_at;

-- ============================================================================
-- Примеры использования (для тестирования)
-- ============================================================================

-- Пример 1: Создание медицинской информации
-- INSERT INTO users.child_medical_info (id_child, allergies, blood_type, medical_policy_number)
-- VALUES (1, 'Аллергия на орехи, пыльцу березы', 'A+', '1234567890123456');

-- Пример 2: Получение медицинской информации ребенка
-- SELECT * FROM users.child_medical_info 
-- WHERE id_child = 1 AND isActive = TRUE;

-- Пример 3: Поиск всех детей с аллергиями
-- SELECT 
--     c.id,
--     c.name,
--     c.surname,
--     m.allergies,
--     m.blood_type
-- FROM users.child c
-- JOIN users.child_medical_info m ON c.id = m.id_child
-- WHERE m.isActive = TRUE 
--   AND m.allergies IS NOT NULL
--   AND c.isActive = TRUE;

-- Пример 4: Поиск детей с хроническими заболеваниями
-- SELECT 
--     c.id,
--     c.name,
--     c.surname,
--     m.chronic_diseases,
--     m.medications,
--     m.doctor_notes
-- FROM users.child c
-- JOIN users.child_medical_info m ON c.id = m.id_child
-- WHERE m.isActive = TRUE 
--   AND m.chronic_diseases IS NOT NULL
--   AND c.isActive = TRUE;

-- Пример 5: Статистика по группам крови
-- SELECT 
--     blood_type,
--     COUNT(*) as count
-- FROM users.child_medical_info
-- WHERE isActive = TRUE AND blood_type IS NOT NULL
-- GROUP BY blood_type
-- ORDER BY count DESC;

-- Пример 6: Дети без медицинской информации
-- SELECT 
--     c.id,
--     c.name,
--     c.surname,
--     u.phone as parent_phone
-- FROM users.child c
-- JOIN users.user u ON c.id_user = u.id
-- LEFT JOIN users.child_medical_info m ON c.id = m.id_child AND m.isActive = TRUE
-- WHERE c.isActive = TRUE
--   AND m.id IS NULL;

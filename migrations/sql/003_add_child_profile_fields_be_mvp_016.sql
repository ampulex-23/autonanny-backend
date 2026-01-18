-- ============================================================================
-- Миграция: 003_add_child_profile_fields_be_mvp_016
-- Описание: Добавление полей профиля ребенка для BE-MVP-016
-- Задача: BE-MVP-016
-- User Story: US-CHILD-01, US-CHILD-04
-- Дата: 2025-10-26
-- Автор: AutoNanny Team
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Добавление новых полей в таблицу users.child
-- ============================================================================

-- Дата рождения ребенка
ALTER TABLE users.child 
ADD COLUMN IF NOT EXISTS birthday DATE NULL;

-- Фото ребенка (путь к файлу)
ALTER TABLE users.child 
ADD COLUMN IF NOT EXISTS photo_path TEXT NULL;

-- Класс/Школа
ALTER TABLE users.child 
ADD COLUMN IF NOT EXISTS school_class TEXT NULL;

-- Особенности характера/поведения
ALTER TABLE users.child 
ADD COLUMN IF NOT EXISTS character_notes TEXT NULL;

-- Пол ребенка (M/F)
ALTER TABLE users.child 
ADD COLUMN IF NOT EXISTS gender VARCHAR(1) NULL;

-- ============================================================================
-- 2. Добавление комментариев для документации
-- ============================================================================

COMMENT ON COLUMN users.child.birthday IS 'Дата рождения ребенка';
COMMENT ON COLUMN users.child.photo_path IS 'Путь к фото ребенка';
COMMENT ON COLUMN users.child.school_class IS 'Класс/Школа ребенка (например: "3А класс, Школа №1")';
COMMENT ON COLUMN users.child.character_notes IS 'Особенности характера, поведения, предпочтения';
COMMENT ON COLUMN users.child.gender IS 'Пол ребенка: M (мужской) или F (женский)';

-- ============================================================================
-- 3. Создание индексов для оптимизации
-- ============================================================================

-- Индекс для поиска по пользователю (если еще нет)
CREATE INDEX IF NOT EXISTS idx_child_id_user ON users.child(id_user) WHERE isActive = true;

-- Индекс для поиска активных детей
CREATE INDEX IF NOT EXISTS idx_child_active ON users.child(isActive) WHERE isActive = true;

-- ============================================================================
-- 4. Проверка результата
-- ============================================================================

DO $$
DECLARE
    column_count INTEGER;
BEGIN
    -- Подсчет новых колонок
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns
    WHERE table_schema = 'users' 
    AND table_name = 'child'
    AND column_name IN ('birthday', 'photo_path', 'school_class', 'character_notes', 'gender');
    
    -- Проверка результата
    IF column_count = 5 THEN
        RAISE NOTICE 'Миграция успешна: добавлено % новых полей в users.child', column_count;
    ELSE
        RAISE EXCEPTION 'Ошибка миграции: добавлено только % полей из 5', column_count;
    END IF;
END $$;

-- ============================================================================
-- 5. Вывод информации о существующих детях
-- ============================================================================

SELECT 
    'Информация о детях' AS info,
    COUNT(*) AS total_children,
    COUNT(DISTINCT id_user) AS unique_parents,
    COUNT(*) FILTER (WHERE isActive = true) AS active_children
FROM users.child;

-- ============================================================================
-- 6. Регистрация миграции в системе Aerich
-- ============================================================================

INSERT INTO aerich (version, app, content) 
VALUES (
    '3_add_child_profile_fields_be_mvp_016',
    'models',
    '{
        "description": "Добавление полей профиля ребенка",
        "task": "BE-MVP-016",
        "user_stories": ["US-CHILD-01", "US-CHILD-04"],
        "changes": [
            "Добавлено поле birthday (дата рождения)",
            "Добавлено поле photo_path (фото ребенка)",
            "Добавлено поле school_class (класс/школа)",
            "Добавлено поле character_notes (особенности характера)",
            "Добавлено поле gender (пол)",
            "Созданы индексы для оптимизации"
        ]
    }'::jsonb
)
ON CONFLICT DO NOTHING;

COMMIT;

-- ============================================================================
-- Проверка успешности выполнения
-- ============================================================================
SELECT 
    'Migration 003 completed successfully' AS status,
    NOW() AS completed_at;

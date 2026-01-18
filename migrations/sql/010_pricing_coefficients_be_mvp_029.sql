-- ============================================================================
-- BE-MVP-029: API настройки коэффициентов формул
-- ============================================================================
-- Миграция для создания таблицы коэффициентов ценообразования
-- Дата создания: 27.10.2025
-- Автор: Backend Team

-- Создаем таблицу для хранения коэффициентов
CREATE TABLE IF NOT EXISTS data.pricing_coefficients (
    id BIGSERIAL PRIMARY KEY,
    
    -- Коэффициенты
    vm FLOAT NOT NULL DEFAULT 27,  -- Средняя скорость движения автомобиля (км/ч)
    s1 FLOAT NOT NULL DEFAULT 3,   -- Радиус подачи автомобиля (км)
    kc FLOAT NOT NULL DEFAULT 3,   -- Коэффициент кэшбека (%)
    ks FLOAT NOT NULL DEFAULT 1,   -- Коэффициент страховки (%)
    kg FLOAT NOT NULL DEFAULT 1,   -- Городской коэффициент (%)
    
    -- Служебные поля
    is_active BOOLEAN DEFAULT TRUE,
    datetime_create TIMESTAMP,
    datetime_update TIMESTAMP,
    updated_by BIGINT  -- ID админа, который обновил
);

-- Создаем индекс для быстрого поиска активных коэффициентов
CREATE INDEX IF NOT EXISTS idx_pricing_coefficients_active 
ON data.pricing_coefficients(is_active);

-- Добавляем комментарии к таблице и полям
COMMENT ON TABLE data.pricing_coefficients IS 'Коэффициенты для расчета стоимости поездок (BE-MVP-029)';
COMMENT ON COLUMN data.pricing_coefficients.vm IS 'Средняя скорость движения автомобиля (км/ч)';
COMMENT ON COLUMN data.pricing_coefficients.s1 IS 'Радиус подачи автомобиля (км)';
COMMENT ON COLUMN data.pricing_coefficients.kc IS 'Коэффициент кэшбека (%)';
COMMENT ON COLUMN data.pricing_coefficients.ks IS 'Коэффициент страховки (%)';
COMMENT ON COLUMN data.pricing_coefficients.kg IS 'Городской коэффициент (%)';
COMMENT ON COLUMN data.pricing_coefficients.updated_by IS 'ID администратора, который последним обновил коэффициенты';

-- Вставляем дефолтные значения
INSERT INTO data.pricing_coefficients (vm, s1, kc, ks, kg, is_active, datetime_create)
VALUES (27, 3, 3, 1, 1, TRUE, NOW())
ON CONFLICT DO NOTHING;

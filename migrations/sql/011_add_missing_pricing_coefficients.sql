-- ============================================================================
-- Добавление недостающих коэффициентов ценообразования
-- ============================================================================
-- Добавляем недостающие поля согласно ТЗ раздел 4.4
-- Дата создания: 01.11.2025

-- Добавляем T1 - время за 1 км пути (в минутах)
ALTER TABLE data.pricing_coefficients 
ADD COLUMN IF NOT EXISTS t1 FLOAT NOT NULL DEFAULT 2.0;

-- Добавляем M - стоимость 1 км пути (в рублях)
ALTER TABLE data.pricing_coefficients 
ADD COLUMN IF NOT EXISTS m FLOAT NOT NULL DEFAULT 15.0;

-- Добавляем X5 - процент на маркетинг (для разовых поездок)
ALTER TABLE data.pricing_coefficients 
ADD COLUMN IF NOT EXISTS x5 FLOAT NOT NULL DEFAULT 5.0;

-- Добавляем P_insurance - сумма страховки (в рублях)
ALTER TABLE data.pricing_coefficients 
ADD COLUMN IF NOT EXISTS p_insurance FLOAT NOT NULL DEFAULT 50.0;

-- Обновляем комментарии
COMMENT ON COLUMN data.pricing_coefficients.t1 IS 'Заранее установленное время за 1 км пути (мин)';
COMMENT ON COLUMN data.pricing_coefficients.m IS 'Стоимость 1 км пути для класса авто (руб)';
COMMENT ON COLUMN data.pricing_coefficients.x5 IS 'Процент на маркетинг для разовых поездок (%)';
COMMENT ON COLUMN data.pricing_coefficients.p_insurance IS 'Сумма страховой компании (руб)';

-- Обновляем существующую запись
UPDATE data.pricing_coefficients 
SET 
    t1 = 2.0,
    m = 15.0,
    x5 = 5.0,
    p_insurance = 50.0
WHERE is_active = TRUE;

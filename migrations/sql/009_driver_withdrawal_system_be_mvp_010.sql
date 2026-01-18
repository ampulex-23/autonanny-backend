-- ============================================================================
-- BE-MVP-010: Система выплат водителям
-- ============================================================================
-- Миграция для добавления полей в таблицу запросов на вывод средств
-- Дата создания: 27.10.2025
-- Автор: Backend Team

-- Добавляем поле для хранения номера карты (последние 4 цифры)
ALTER TABLE history.request_payment 
ADD COLUMN IF NOT EXISTS card_last_4 VARCHAR(4);

-- Добавляем поле для статуса запроса
ALTER TABLE history.request_payment 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending';

-- Добавляем поле для комментария/причины отклонения
ALTER TABLE history.request_payment 
ADD COLUMN IF NOT EXISTS comment TEXT;

-- Добавляем поле для даты обработки
ALTER TABLE history.request_payment 
ADD COLUMN IF NOT EXISTS datetime_processed TIMESTAMP;

-- Создаем индекс для быстрого поиска по пользователю и статусу
CREATE INDEX IF NOT EXISTS idx_request_payment_user_status 
ON history.request_payment(id_user, status);

-- Создаем индекс для поиска по дате создания
CREATE INDEX IF NOT EXISTS idx_request_payment_datetime 
ON history.request_payment(datetime_create);

-- Добавляем комментарии к полям
COMMENT ON COLUMN history.request_payment.card_last_4 IS 'Последние 4 цифры карты для вывода';
COMMENT ON COLUMN history.request_payment.status IS 'Статус запроса: pending, approved, rejected, completed';
COMMENT ON COLUMN history.request_payment.comment IS 'Комментарий администратора или причина отклонения';
COMMENT ON COLUMN history.request_payment.datetime_processed IS 'Дата и время обработки запроса';

-- Обновляем существующие записи
UPDATE history.request_payment 
SET status = CASE 
    WHEN isSuccess = true THEN 'completed'
    WHEN isSuccess = false AND isActive = false THEN 'rejected'
    ELSE 'pending'
END
WHERE status IS NULL;

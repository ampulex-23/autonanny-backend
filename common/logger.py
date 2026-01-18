"""
Структурированное JSON логирование для АвтоНяня
Обратная совместимость: экспортирует logger для существующего кода
"""
from common.logger_new import (
    logger,
    setup_logger,
    log_with_context,
    log_request,
    log_db_query,
    log_error,
    log_business_event,
    setup_tortoise_logger
)

# Экспортируем для обратной совместимости
__all__ = [
    'logger',
    'setup_logger',
    'log_with_context',
    'log_request',
    'log_db_query',
    'log_error',
    'log_business_event',
    'setup_tortoise_logger'
]
"""
Структурированное JSON логирование для АвтоНяня
Поддерживает rotation, разные уровни логирования и structured fields
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
from config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Кастомный JSON форматтер с дополнительными полями"""
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Добавляем стандартные поля
        log_record['timestamp'] = self.formatTime(record, self.datefmt)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Добавляем application context
        log_record['app'] = settings.app_name
        
        # Если есть exception info
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Настройка логгера с JSON форматированием и rotation
    
    Args:
        name: Имя логгера
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Устанавливаем уровень логирования из конфига
    log_level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    logger.setLevel(log_level_map.get(settings.log_level.lower(), logging.INFO))
    
    # Избегаем дублирования handlers
    if logger.handlers:
        return logger
    
    # JSON форматтер
    json_formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    
    # Console handler (stdout) - для Docker logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    # File handler с rotation - для персистентных логов
    log_dir = Path(settings.report_file_path) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,  # Храним 5 файлов
        encoding='utf-8'
    )
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # Отдельный файл для ошибок
    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,  # Храним больше файлов для ошибок
        encoding='utf-8'
    )
    error_handler.setFormatter(json_formatter)
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)
    
    return logger


# Создаём глобальный логгер для приложения
logger = setup_logger("autonanny")


# Вспомогательные функции для structured logging
def log_with_context(level: str, message: str, **kwargs):
    """
    Логирование с дополнительным контекстом
    
    Args:
        level: Уровень логирования (debug, info, warning, error, critical)
        message: Сообщение
        **kwargs: Дополнительные поля для логирования
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=kwargs)


def log_request(method: str, path: str, status_code: int, duration_ms: float, user_id: int = None):
    """Логирование HTTP запроса"""
    logger.info(
        "HTTP request",
        extra={
            "event_type": "http_request",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id
        }
    )


def log_db_query(query: str, duration_ms: float, rows_affected: int = None):
    """Логирование DB запроса"""
    logger.debug(
        "Database query",
        extra={
            "event_type": "db_query",
            "query": query[:200],  # Обрезаем длинные запросы
            "duration_ms": duration_ms,
            "rows_affected": rows_affected
        }
    )


def log_error(error: Exception, context: dict = None):
    """
    Логирование ошибки с контекстом
    
    Args:
        error: Исключение
        context: Дополнительный контекст
    """
    logger.error(
        f"Error occurred: {str(error)}",
        exc_info=True,
        extra={
            "event_type": "error",
            "error_type": type(error).__name__,
            **(context or {})
        }
    )


def log_business_event(event_name: str, **kwargs):
    """Логирование бизнес-событий"""
    logger.info(
        f"Business event: {event_name}",
        extra={
            "event_type": "business",
            "event_name": event_name,
            **kwargs
        }
    )


# Настройка логгера для Tortoise ORM (опционально)
def setup_tortoise_logger():
    """Настройка логгера для SQL запросов Tortoise ORM"""
    tortoise_logger = logging.getLogger("tortoise")
    tortoise_logger.setLevel(logging.DEBUG if settings.log_level == "debug" else logging.WARNING)
    
    # Используем те же handlers что и основной логгер
    for handler in logger.handlers:
        tortoise_logger.addHandler(handler)
    
    return tortoise_logger

"""
Тестовый скрипт для проверки нового JSON логирования
"""
import asyncio
from common.logger import (
    logger,
    log_with_context,
    log_request,
    log_business_event,
    log_error
)


async def test_logging():
    """Тестирование различных типов логирования"""
    
    print("🧪 Тестирование JSON логирования...\n")
    
    # 1. Базовое логирование
    print("1️⃣ Базовое логирование:")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # 2. Логирование с контекстом
    print("\n2️⃣ Логирование с контекстом:")
    log_with_context(
        "info",
        "User logged in successfully",
        user_id=123,
        username="ivan_ivanov",
        ip_address="192.168.1.1"
    )
    
    # 3. HTTP запросы
    print("\n3️⃣ Логирование HTTP запросов:")
    log_request(
        method="POST",
        path="/api/v1.0/authentication/login",
        status_code=200,
        duration_ms=145.5,
        user_id=123
    )
    
    # 4. Бизнес-события
    print("\n4️⃣ Логирование бизнес-событий:")
    log_business_event(
        "order_created",
        order_id=789,
        user_id=123,
        driver_id=456,
        amount=1500.00,
        route="Москва -> Санкт-Петербург"
    )
    
    # 5. Ошибки
    print("\n5️⃣ Логирование ошибок:")
    try:
        # Симулируем ошибку
        result = 10 / 0
    except Exception as e:
        log_error(e, context={
            "user_id": 123,
            "action": "calculate_price",
            "order_id": 789
        })
    
    # 6. Логирование с дополнительными полями
    print("\n6️⃣ Кастомные поля:")
    logger.info(
        "Payment processed",
        extra={
            "event_type": "payment",
            "payment_id": 999,
            "user_id": 123,
            "amount": 1500.00,
            "currency": "RUB",
            "payment_method": "card",
            "card_last4": "1234"
        }
    )
    
    print("\n✅ Тестирование завершено!")
    print("\n📁 Проверьте файлы логов:")
    print("   - logs/app.log")
    print("   - logs/error.log")


if __name__ == "__main__":
    asyncio.run(test_logging())

"""
Конфигурация Tortoise ORM для Aerich (система миграций).
Этот файл используется только для генерации и применения миграций.
"""
from config import settings

TORTOISE_ORM = {
    "connections": {
        "default": settings.database_url
    },
    "apps": {
        "models": {
            "models": [
                "models.authentication_db",
                "models.files_db",
                "models.users_db",
                "models.drivers_db",
                "models.static_data_db",
                "models.chats_db",
                "models.admins_db",
                "models.orders_db",
                "aerich.models"  # Обязательно для Aerich
            ],
            "default_connection": "default",
        },
    },
}

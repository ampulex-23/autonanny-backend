"""
Скрипт для обновления логина суперадмина на телефон
"""
import asyncio
import asyncpg
from config import settings

async def update_admin():
    db_url = settings.database_url
    parts = db_url.replace("postgres://", "").split("@")
    user_pass = parts[0].split(":")
    host_port_db = parts[1].split("/")
    host_port = host_port_db[0].split(":")

    conn = await asyncpg.connect(
        user=user_pass[0],
        password=user_pass[1],
        database=host_port_db[1],
        host=host_port[0],
        port=int(host_port[1])
    )

    try:
        # Обновляем телефон пользователя
        await conn.execute(
            "UPDATE users.user SET phone = $1 WHERE id = 4",
            "+79673201280"
        )
        print("Телефон пользователя обновлен")
        
        # Обновляем логин
        await conn.execute(
            "UPDATE authentication.authorization_data SET login = $1 WHERE id_user = 4",
            "+79673201280"
        )
        print("Логин обновлен")
        
        print("\n✅ Суперадмин обновлен!")
        print("Логин: +79673201280")
        print("Пароль: admin123")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_admin())

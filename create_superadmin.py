"""
Скрипт для создания суперадмина
"""
import asyncio
import hashlib
import asyncpg
from config import settings

async def create_superadmin():
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
        # Проверяем, существует ли уже админ
        existing = await conn.fetchval(
            "SELECT id FROM users.user WHERE phone = $1",
            "admin@autonanny.ru"
        )
        
        if existing:
            print(f"Суперадмин уже существует (ID: {existing})")
            # Обновим пароль
            pwd_hash = hashlib.md5("admin123".encode()).hexdigest()
            await conn.execute(
                "UPDATE authentication.authorization_data SET password = $1 WHERE login = $2",
                pwd_hash, "admin@autonanny.ru"
            )
            print("Пароль обновлен на: admin123")
            return
        
        # Создаем пользователя
        admin_id = await conn.fetchval(
            '''INSERT INTO users.user (surname, name, phone, "isActive", datetime_create) 
               VALUES ($1, $2, $3, TRUE, NOW()) RETURNING id''',
            "Суперадмин", "Админ", "admin@autonanny.ru"
        )
        print(f"Создан пользователь с ID: {admin_id}")
        
        # Хэш пароля (MD5)
        pwd_hash = hashlib.md5("admin123".encode()).hexdigest()
        
        # Авторизационные данные
        await conn.execute(
            "INSERT INTO authentication.authorization_data (login, password, id_user) VALUES ($1, $2, $3)",
            "admin@autonanny.ru", pwd_hash, admin_id
        )
        print("Авторизационные данные созданы")
        
        # Роль администратора (7)
        await conn.execute(
            "INSERT INTO authentication.user_account (id_user, id_type_account) VALUES ($1, $2)",
            admin_id, 7
        )
        print("Роль администратора назначена")
        
        # Верификация аккаунта
        await conn.execute(
            "INSERT INTO authentication.verify_account (id_user) VALUES ($1)",
            admin_id
        )
        print("Аккаунт верифицирован")
        
        print("\n" + "="*50)
        print("✅ Суперадмин создан!")
        print("="*50)
        print(f"Логин: admin@autonanny.ru")
        print(f"Пароль: admin123")
        print("="*50)
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_superadmin())

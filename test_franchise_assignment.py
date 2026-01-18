"""
Тестовый скрипт для проверки автозакрепления за франшизой
"""
import asyncio
import asyncpg
from config import settings

# Парсим DATABASE_URL
db_url = settings.database_url
parts = db_url.replace("postgres://", "").split("@")
user_pass = parts[0].split(":")
host_port_db = parts[1].split("/")
host_port = host_port_db[0].split(":")

DB_USER = user_pass[0]
DB_PASS = user_pass[1]
DB_HOST = host_port[0]
DB_PORT = int(host_port[1])
DB_NAME = host_port_db[1]


async def test_franchise_assignment():
    """Проверка автозакрепления пользователей за франшизой"""
    
    print("🧪 Тестирование автозакрепления за франшизой...\n")
    
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT
    )
    
    try:
        # 1. Проверка франшизы
        print("1️⃣ Проверка франшизы по умолчанию:")
        franchise = await conn.fetchrow(
            "SELECT * FROM users.franchise WHERE id = $1",
            settings.default_franchise_id
        )
        if franchise:
            print(f"   ✅ Франшиза найдена:")
            print(f"      ID: {franchise['id']}")
            print(f"      Название: {franchise['title']}")
            print(f"      Описание: {franchise['description']}")
            print(f"      Активна: {franchise['isActive']}")
        else:
            print(f"   ❌ Франшиза с ID {settings.default_franchise_id} не найдена!")
        
        # 2. Проверка пользователей
        print("\n2️⃣ Проверка привязки пользователей:")
        users_with_franchise = await conn.fetch("""
            SELECT 
                u.id,
                u.name,
                u.surname,
                u.phone,
                t.title as role,
                f.id as franchise_id,
                f.title as franchise_name
            FROM users.user u
            JOIN authentication.user_account ua ON u.id = ua.id_user
            JOIN data.type_account t ON ua.id_type_account = t.id
            LEFT JOIN users.franchise_user fu ON u.id = fu.id_user
            LEFT JOIN users.franchise f ON fu.id_franchise = f.id
            ORDER BY u.id
        """)
        
        for user in users_with_franchise:
            status = "✅" if user['franchise_id'] else "❌"
            print(f"\n   {status} {user['name']} {user['surname']} ({user['role']})")
            print(f"      Телефон: {user['phone']}")
            if user['franchise_id']:
                print(f"      Франшиза: {user['franchise_name']} (ID: {user['franchise_id']})")
            else:
                print(f"      ⚠️  НЕ ПРИВЯЗАН К ФРАНШИЗЕ!")
        
        # 3. Статистика
        print("\n3️⃣ Статистика:")
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(DISTINCT u.id) as total_users,
                COUNT(DISTINCT fu.id_user) as users_with_franchise,
                COUNT(DISTINCT u.id) - COUNT(DISTINCT fu.id_user) as users_without_franchise
            FROM users.user u
            LEFT JOIN users.franchise_user fu ON u.id = fu.id_user
        """)
        
        print(f"   Всего пользователей: {stats['total_users']}")
        print(f"   С франшизой: {stats['users_with_franchise']}")
        print(f"   Без франшизы: {stats['users_without_franchise']}")
        
        if stats['users_without_franchise'] > 0:
            print("\n   ⚠️  ВНИМАНИЕ: Есть пользователи без франшизы!")
        else:
            print("\n   ✅ Все пользователи привязаны к франшизе!")
        
        # 4. Проверка по ролям
        print("\n4️⃣ Распределение по ролям:")
        role_stats = await conn.fetch("""
            SELECT 
                t.title as role,
                COUNT(u.id) as total,
                COUNT(fu.id_user) as with_franchise
            FROM users.user u
            JOIN authentication.user_account ua ON u.id = ua.id_user
            JOIN data.type_account t ON ua.id_type_account = t.id
            LEFT JOIN users.franchise_user fu ON u.id = fu.id_user
            GROUP BY t.title
            ORDER BY t.title
        """)
        
        for role in role_stats:
            coverage = (role['with_franchise'] / role['total'] * 100) if role['total'] > 0 else 0
            print(f"   {role['role']}: {role['with_franchise']}/{role['total']} ({coverage:.0f}%)")
        
        print("\n" + "="*60)
        print("✅ Тестирование завершено!")
        print("="*60)
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(test_franchise_assignment())

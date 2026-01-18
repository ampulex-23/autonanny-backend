"""
Скрипт для применения миграции pricing_coefficients
"""
import asyncio
import asyncpg
from config import settings

async def apply_migration():
    """Применить миграцию для таблицы pricing_coefficients"""
    
    # Читаем SQL миграцию
    with open('migrations/sql/010_pricing_coefficients_be_mvp_029.sql', 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Подключаемся к базе данных используя database_url
    conn = await asyncpg.connect(settings.database_url)
    
    try:
        # Выполняем миграцию
        await conn.execute(migration_sql)
        print('✅ Миграция pricing_coefficients успешно применена!')
        
        # Проверяем, что таблица создана
        result = await conn.fetchval(
            "SELECT COUNT(*) FROM data.pricing_coefficients"
        )
        print(f'✅ Таблица создана, записей: {result}')
        
    except Exception as e:
        print(f'❌ Ошибка при применении миграции: {e}')
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(apply_migration())

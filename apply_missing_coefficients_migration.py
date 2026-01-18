"""
Скрипт для применения миграции недостающих коэффициентов
"""
import asyncio
import asyncpg
from config import settings

async def apply_migration():
    """Применить миграцию для добавления недостающих коэффициентов"""
    
    # Читаем SQL миграцию
    with open('migrations/sql/011_add_missing_pricing_coefficients.sql', 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Подключаемся к базе данных
    conn = await asyncpg.connect(settings.database_url)
    
    try:
        # Выполняем миграцию
        await conn.execute(migration_sql)
        print('✅ Миграция недостающих коэффициентов успешно применена!')
        
        # Проверяем обновленные данные
        result = await conn.fetchrow(
            "SELECT vm, s1, kc, ks, kg, t1, m, x5, p_insurance FROM data.pricing_coefficients WHERE is_active = TRUE"
        )
        print(f'✅ Текущие коэффициенты:')
        print(f'   vm (скорость): {result["vm"]} км/ч')
        print(f'   s1 (радиус подачи): {result["s1"]} км')
        print(f'   kc (кэшбек): {result["kc"]} %')
        print(f'   ks (страховка %): {result["ks"]} %')
        print(f'   kg (городской коэф.): {result["kg"]} %')
        print(f'   t1 (время за 1 км): {result["t1"]} мин')
        print(f'   m (стоимость за км): {result["m"]} руб')
        print(f'   x5 (маркетинг): {result["x5"]} %')
        print(f'   p_insurance (страховка): {result["p_insurance"]} руб')
        
    except Exception as e:
        print(f'❌ Ошибка при применении миграции: {e}')
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(apply_migration())

"""
Скрипт для заполнения БД тестовыми данными
Запуск: python seed_data.py
"""
import asyncio
import hashlib
from datetime import datetime
from tortoise import Tortoise
from config import settings

# Импорт моделей
from models.static_data_db import (
    DataCountry, DataCity, DataColor, DataCarMark, DataCarModel,
    DataTypeAccount, DataOtherDriveParametr, DataCarTariff
)
from models.users_db import UsersUser, UsersChild, UsersFranchiseUser
from models.authentication_db import UsersAuthorizationData, UsersUserAccount
from models.drivers_db import UsersDriverData, UsersCar


async def init_db():
    """Инициализация подключения к БД"""
    await Tortoise.init(
        db_url=settings.database_url,
        modules={
            "models": [
                "models.authentication_db",
                "models.files_db",
                "models.users_db",
                "models.drivers_db",
                "models.static_data_db",
                "models.chats_db",
                "models.admins_db",
                "models.orders_db"
            ]
        }
    )
    
    # Создаём схемы PostgreSQL
    conn = Tortoise.get_connection("default")
    schemas = ["data", "users", "authentication", "drivers", "files", "chats", "admins", "orders"]
    for schema in schemas:
        await conn.execute_script(f"CREATE SCHEMA IF NOT EXISTS {schema};")
    print(f"✅ Созданы схемы: {', '.join(schemas)}")
    
    await Tortoise.generate_schemas()
    print("✅ База данных инициализирована")


async def seed_static_data():
    """Заполнение справочных данных"""
    print("\n📊 Заполнение справочных данных...")
    
    # Страны
    countries = ["Россия", "Беларусь", "Казахстан"]
    for country in countries:
        await DataCountry.get_or_create(title=country)
    print(f"✅ Добавлено стран: {len(countries)}")
    
    # Города
    cities = [
        "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург",
        "Казань", "Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону"
    ]
    for city in cities:
        await DataCity.get_or_create(title=city)
    print(f"✅ Добавлено городов: {len(cities)}")
    
    # Цвета автомобилей
    colors = [
        "Белый", "Черный", "Серый", "Серебристый", "Синий",
        "Красный", "Зеленый", "Коричневый", "Бежевый"
    ]
    for color in colors:
        await DataColor.get_or_create(title=color)
    print(f"✅ Добавлено цветов: {len(colors)}")
    
    # Марки автомобилей
    car_marks = {
        "Toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser"],
        "Volkswagen": ["Polo", "Tiguan", "Passat", "Golf"],
        "Kia": ["Rio", "Sportage", "Ceed", "Sorento"],
        "Hyundai": ["Solaris", "Creta", "Tucson", "Elantra"],
        "Nissan": ["Qashqai", "X-Trail", "Almera", "Juke"],
        "Skoda": ["Octavia", "Rapid", "Kodiaq", "Superb"],
        "Renault": ["Duster", "Logan", "Kaptur", "Arkana"],
        "Mazda": ["CX-5", "3", "6", "CX-9"],
    }
    
    for mark_name, models in car_marks.items():
        mark, _ = await DataCarMark.get_or_create(title=mark_name)
        for model_name in models:
            await DataCarModel.get_or_create(
                title=model_name,
                id_car_mark=mark.id,
                releaseYear=2020
            )
    print(f"✅ Добавлено марок: {len(car_marks)}, моделей: {sum(len(m) for m in car_marks.values())}")
    
    # Типы аккаунтов (роли)
    account_types = [
        (1, "Родитель"),
        (2, "Водитель"),
        (3, "Администратор"),
        (4, "Франчайзи"),
        (5, "Партнер")
    ]
    for type_id, title in account_types:
        await DataTypeAccount.get_or_create(id=type_id, defaults={"title": title})
    print(f"✅ Добавлено типов аккаунтов: {len(account_types)}")
    
    # Дополнительные услуги
    services = [
        ("Детское кресло", 200.00),
        ("Бустер", 150.00),
        ("Встреча с табличкой", 300.00),
        ("Помощь с багажом", 250.00),
    ]
    for title, amount in services:
        await DataOtherDriveParametr.get_or_create(
            title=title,
            defaults={"amount": amount, "isActive": True}
        )
    print(f"✅ Добавлено дополнительных услуг: {len(services)}")


async def seed_test_users():
    """Создание тестовых пользователей"""
    print("\n👥 Создание тестовых пользователей...")
    
    # Тестовый родитель
    parent_user = await UsersUser.create(
        surname="Иванов",
        name="Иван",
        phone="+79991234567",
        isActive=True,
        datetime_create=datetime.now()
    )
    
    # Авторизационные данные для родителя
    password_hash = hashlib.md5("password123".encode()).hexdigest()
    await UsersAuthorizationData.create(
        id_user=parent_user.id,
        login="+79991234567",
        password=password_hash
    )
    
    # Роль родителя
    await UsersUserAccount.create(
        id_user=parent_user.id,
        id_type_account=1  # Родитель
    )
    
    # Дети родителя
    child1 = await UsersChild.create(
        surname="Иванов",
        name="Петр",
        patronymic="Иванович",
        age=7,
        child_phone="+79991234568",
        id_user=parent_user.id,
        isActive=True,
        datetime_create=datetime.now()
    )
    
    child2 = await UsersChild.create(
        surname="Иванова",
        name="Мария",
        patronymic="Ивановна",
        age=5,
        id_user=parent_user.id,
        isActive=True,
        datetime_create=datetime.now()
    )
    
    print(f"✅ Создан родитель: {parent_user.name} {parent_user.surname} (ID: {parent_user.id})")
    print(f"   Логин: +79991234567, Пароль: password123")
    print(f"   Дети: {child1.name} (7 лет), {child2.name} (5 лет)")
    
    # Тестовый водитель
    driver_user = await UsersUser.create(
        surname="Петров",
        name="Петр",
        phone="+79997654321",
        isActive=True,
        datetime_create=datetime.now()
    )
    
    # Авторизационные данные для водителя
    await UsersAuthorizationData.create(
        id_user=driver_user.id,
        login="+79997654321",
        password=password_hash
    )
    
    # Роль водителя
    await UsersUserAccount.create(
        id_user=driver_user.id,
        id_type_account=2  # Водитель
    )
    
    # Данные водителя
    await UsersDriverData.create(
        id_user=driver_user.id,
        experience=5,
        isActive=True,
        datetime_create=datetime.now()
    )
    
    # Автомобиль водителя
    toyota = await DataCarMark.filter(title="Toyota").first()
    camry = await DataCarModel.filter(title="Camry", id_car_mark=toyota.id).first()
    white_color = await DataColor.filter(title="Белый").first()
    
    await UsersCar.create(
        id_user=driver_user.id,
        id_car_mark=toyota.id,
        id_car_model=camry.id,
        id_color=white_color.id,
        number="А123БВ777",
        year=2020,
        isActive=True,
        datetime_create=datetime.now()
    )
    
    print(f"✅ Создан водитель: {driver_user.name} {driver_user.surname} (ID: {driver_user.id})")
    print(f"   Логин: +79997654321, Пароль: password123")
    print(f"   Автомобиль: Toyota Camry 2020, белый, А123БВ777")
    
    # Тестовый администратор
    admin_user = await UsersUser.create(
        surname="Админов",
        name="Админ",
        phone="+79995555555",
        isActive=True,
        datetime_create=datetime.now()
    )
    
    await UsersAuthorizationData.create(
        id_user=admin_user.id,
        login="+79995555555",
        password=password_hash
    )
    
    await UsersUserAccount.create(
        id_user=admin_user.id,
        id_type_account=3  # Администратор
    )
    
    print(f"✅ Создан администратор: {admin_user.name} {admin_user.surname} (ID: {admin_user.id})")
    print(f"   Логин: +79995555555, Пароль: password123")
    
    return {
        "parent": parent_user,
        "driver": driver_user,
        "admin": admin_user
    }


async def seed_franchise_and_tariffs():
    """Создание франшизы и единого тарифа (BE-MVP-011)"""
    print("\n🏢 Создание франшизы и единого тарифа...")
    
    # BE-MVP-011: Единая категория "Заказ маршрута"
    # Убрана привязка к классу авто, акцент на квалификации автоняни
    
    tariff = {
        "title": "Заказ маршрута",
        "description": "Единый тариф для всех поездок. Акцент на квалификации и опыте автоняни, а не на классе автомобиля.",
        "amount": 100,  # 100 руб/км - оптимальная цена
        "one_time": True,
        "percent": 65,  # 65% водителю
        "id_franchise": 1,
        "isActive": True,
        "datetime_create": datetime.now()
    }
    
    await DataCarTariff.create(**tariff)
    
    print(f"✅ Создан единый тариф: {tariff['title']} ({tariff['amount']} руб/км)")


async def main():
    """Главная функция"""
    print("🚀 Начало заполнения БД тестовыми данными...\n")
    
    try:
        await init_db()
        await seed_static_data()
        users = await seed_test_users()
        await seed_franchise_and_tariffs()
        
        print("\n" + "="*60)
        print("✅ База данных успешно заполнена тестовыми данными!")
        print("="*60)
        print("\n📝 Тестовые учетные записи:")
        print("\n1️⃣  Родитель:")
        print("   Логин: +79991234567")
        print("   Пароль: password123")
        print("\n2️⃣  Водитель:")
        print("   Логин: +79997654321")
        print("   Пароль: password123")
        print("\n3️⃣  Администратор:")
        print("   Логин: +79995555555")
        print("   Пароль: password123")
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\n❌ Ошибка при заполнении БД: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()
        print("\n👋 Подключение к БД закрыто")


if __name__ == "__main__":
    asyncio.run(main())

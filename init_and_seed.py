"""
Полный скрипт инициализации и заполнения БД AutoNanny
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from typing import Iterable, Sequence

import asyncpg

from config import settings


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


AUTHENTICATION_TABLES: Sequence[str] = (
    """
    CREATE TABLE IF NOT EXISTS authentication.authorization_data (
        id BIGSERIAL PRIMARY KEY,
        login TEXT NOT NULL,
        password TEXT NOT NULL,
        id_user BIGINT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS authentication.user_account (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_type_account BIGINT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS authentication.verify_account (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS authentication.bearer_authorization (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        fbid TEXT,
        token TEXT NOT NULL,
        datetime_create TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS authentication.mobile_authentication (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        code TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS authentication.referal_code (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        code TEXT NOT NULL,
        percent INTEGER
    );
    """,
)


USERS_TABLES: Sequence[str] = (
    """
    CREATE TABLE IF NOT EXISTS users.user (
        id BIGSERIAL PRIMARY KEY,
        surname TEXT,
        name TEXT,
        phone TEXT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.child (
        id BIGSERIAL PRIMARY KEY,
        surname TEXT,
        name TEXT,
        patronymic TEXT,
        child_phone TEXT,
        age INTEGER,
        birthday DATE,
        photo_path TEXT,
        school_class TEXT,
        character_notes TEXT,
        gender VARCHAR(1),
        contact_phone TEXT,
        id_user BIGINT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.franchise (
        id BIGSERIAL PRIMARY KEY,
        title TEXT,
        description TEXT,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.franchise_user (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_franchise BIGINT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.franchise_city (
        id BIGSERIAL PRIMARY KEY,
        id_franchise BIGINT NOT NULL,
        id_city BIGINT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.user_photo (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        photo_path TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.referal_user (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_user_referal BIGINT NOT NULL,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.driver_card (
        id BIGSERIAL PRIMARY KEY,
        id_country BIGINT NOT NULL,
        license TEXT NOT NULL,
        date_of_issue DATE NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.driver_answer (
        id BIGSERIAL PRIMARY KEY,
        first_answer TEXT,
        second_answer TEXT,
        third_answer TEXT,
        four_answer TEXT,
        five_answer TEXT,
        six_answer TEXT,
        seven_answer TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.car (
        id BIGSERIAL PRIMARY KEY,
        id_car_mark BIGINT NOT NULL,
        id_car_model BIGINT NOT NULL,
        id_color BIGINT NOT NULL,
        year_create INTEGER,
        state_number TEXT NOT NULL,
        ctc TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.driver_data (
        id BIGSERIAL PRIMARY KEY,
        id_driver BIGINT NOT NULL,
        id_city BIGINT NOT NULL,
        description TEXT,
        age BIGINT,
        video_url TEXT,
        id_driver_card BIGINT NOT NULL,
        id_car BIGINT NOT NULL,
        id_driver_answer BIGINT NOT NULL,
        "isActive" BOOLEAN DEFAULT FALSE,
        inn TEXT,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.user_order (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_order BIGINT NOT NULL,
        token TEXT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.user_vk (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        vk_id TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.user_yandex (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        yandex_id TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.payment_client (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        customer_key TEXT NOT NULL,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.sos_event (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_order BIGINT NULL,
        latitude DOUBLE PRECISION NULL,
        longitude DOUBLE PRECISION NULL,
        message TEXT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        resolved_by BIGINT NULL,
        resolved_at TIMESTAMP NULL,
        datetime_create TIMESTAMP NULL DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.child_emergency_contact (
        id BIGSERIAL PRIMARY KEY,
        id_child BIGINT NOT NULL,
        name TEXT NOT NULL,
        relationship TEXT NOT NULL,
        phone TEXT NOT NULL,
        priority INTEGER DEFAULT 1,
        notes TEXT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP NULL DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.child_medical_info (
        id BIGSERIAL PRIMARY KEY,
        id_child BIGINT NOT NULL,
        allergies TEXT NULL,
        chronic_diseases TEXT NULL,
        medications TEXT NULL,
        medical_policy_number TEXT NULL,
        blood_type VARCHAR(10) NULL,
        special_needs TEXT NULL,
        doctor_notes TEXT NULL,
        policy_document_path TEXT NULL,
        medical_certificate_path TEXT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP NULL DEFAULT NOW(),
        datetime_update TIMESTAMP NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS users.driver_meeting_code (
        id BIGSERIAL PRIMARY KEY,
        id_driver BIGINT NOT NULL,
        code TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        is_used BOOLEAN DEFAULT FALSE,
        used_at TIMESTAMP NULL,
        verified_by BIGINT NULL,
        datetime_create TIMESTAMP NULL DEFAULT NOW()
    );
    """,
)


DATA_TABLES: Sequence[str] = (
    """
    CREATE TABLE IF NOT EXISTS data.country (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.city (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.color (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.car_mark (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.car_model (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        id_car_mark BIGINT NOT NULL,
        "releaseYear" INTEGER
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.type_account (
        id BIGINT PRIMARY KEY,
        title TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.other_drive_parametr (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.car_tariff (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        amount BIGINT,
        one_time BOOLEAN DEFAULT TRUE,
        percent BIGINT,
        photo_path TEXT,
        id_franchise BIGINT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.driving_status (
        id BIGSERIAL PRIMARY KEY,
        status TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.message_type (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data."order" (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_driver BIGINT,
        id_status BIGINT NOT NULL,
        id_type_order BIGINT NOT NULL,
        type_drive TEXT DEFAULT '0',
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.order_addresses (
        id BIGSERIAL PRIMARY KEY,
        id_order BIGINT NOT NULL,
        from_address TEXT NOT NULL,
        to_address TEXT NOT NULL,
        from_lon FLOAT NOT NULL,
        from_lat FLOAT NOT NULL,
        to_lon FLOAT NOT NULL,
        to_lat FLOAT NOT NULL,
        "isFinish" BOOLEAN DEFAULT FALSE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.order_info (
        id BIGSERIAL PRIMARY KEY,
        id_order BIGINT NOT NULL,
        client_lon FLOAT NOT NULL,
        client_lat FLOAT NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        distance BIGINT NOT NULL,
        duration BIGINT NOT NULL,
        description TEXT,
        id_tariff BIGINT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.order_other_parametrs (
        id BIGSERIAL PRIMARY KEY,
        id_order BIGINT NOT NULL,
        id_other_parametr BIGINT NOT NULL,
        amount BIGINT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.schedule (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        title TEXT,
        description TEXT,
        duration BIGINT NOT NULL,
        children_count BIGINT NOT NULL,
        id_tariff BIGINT NOT NULL,
        week_days TEXT NOT NULL,
        "isActive" BOOLEAN DEFAULT FALSE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.schedule_road (
        id BIGSERIAL PRIMARY KEY,
        id_schedule BIGINT NOT NULL,
        week_day BIGINT NOT NULL,
        title TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        type_drive TEXT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.schedule_road_address (
        id BIGSERIAL PRIMARY KEY,
        id_schedule_road BIGINT NOT NULL,
        from_address TEXT NOT NULL,
        to_address TEXT NOT NULL,
        from_lon FLOAT NOT NULL,
        from_lat FLOAT NOT NULL,
        to_lon FLOAT NOT NULL,
        to_lat FLOAT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.schedule_road_driver (
        id BIGSERIAL PRIMARY KEY,
        id_schedule_road BIGINT NOT NULL,
        id_driver BIGINT NOT NULL,
        "isRepeat" BOOLEAN DEFAULT TRUE,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.schedule_road_contact (
        id BIGSERIAL PRIMARY KEY,
        id_schedule_road BIGINT NOT NULL,
        surname TEXT,
        name TEXT,
        patronymic TEXT,
        contact_phone TEXT,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.schedule_road_child (
        id BIGSERIAL PRIMARY KEY,
        id_schedule_road BIGINT NOT NULL,
        id_child BIGINT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.schedule_other_parametrs (
        id BIGSERIAL PRIMARY KEY,
        id_schedule BIGINT NOT NULL,
        id_other_parametr BIGINT NOT NULL,
        amount BIGINT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.user_balance (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        money DECIMAL(10, 2) NOT NULL DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.user_balance_history (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_task BIGINT,
        description TEXT,
        money DECIMAL(10, 2) NOT NULL,
        "isComplete" BOOLEAN,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.task_balance_history (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.debit_card (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        card_number TEXT NOT NULL,
        exp_date TEXT NOT NULL,
        name TEXT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.driver_mode (
        id BIGSERIAL PRIMARY KEY,
        id_driver BIGINT NOT NULL,
        latitude FLOAT NOT NULL,
        longitude FLOAT NOT NULL,
        websocket_token TEXT NOT NULL,
        "isActive" BOOLEAN DEFAULT FALSE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data.uploaded_file (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        files_path TEXT NOT NULL,
        datetime_create TIMESTAMP
    );
    """,
)


CHATS_TABLES: Sequence[str] = (
    """
    CREATE TABLE IF NOT EXISTS chats.chat (
        id BIGSERIAL PRIMARY KEY,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS chats.message (
        id BIGSERIAL PRIMARY KEY,
        id_chat BIGINT NOT NULL,
        id_sender BIGINT NOT NULL,
        msg TEXT NOT NULL,
        "msgType" INTEGER NOT NULL,
        timestamp_send BIGINT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS chats.chat_participant (
        id BIGSERIAL PRIMARY KEY,
        id_chat BIGINT NOT NULL,
        id_user BIGINT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS chats.chat_participant_token (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        token TEXT NOT NULL,
        datetime_create TIMESTAMP
    );
    """,
)


HISTORY_TABLES: Sequence[str] = (
    """
    CREATE TABLE IF NOT EXISTS history.old_token (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        fbid TEXT,
        token TEXT NOT NULL,
        datetime_create TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS history.request_payment (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_card BIGINT NOT NULL,
        id_history BIGINT NOT NULL,
        money DECIMAL(10, 2) NOT NULL,
        "isCashback" BOOLEAN DEFAULT FALSE,
        "isSuccess" BOOLEAN DEFAULT FALSE,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS history.payment_tink (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_payment TEXT,
        id_order TEXT,
        amount BIGINT,
        ip TEXT,
        token TEXT,
        card_data TEXT,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS history.notification (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        title TEXT,
        description TEXT,
        is_readed BOOLEAN DEFAULT FALSE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS history.chat_notification (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_chat BIGINT NOT NULL,
        id_msg BIGINT NOT NULL,
        is_readed BOOLEAN DEFAULT FALSE,
        datetime_create TIMESTAMP
    );
    """,
)


WAIT_DATA_TABLES: Sequence[str] = (
    """
    CREATE TABLE IF NOT EXISTS wait_data.verify_code (
        id BIGSERIAL PRIMARY KEY,
        phone TEXT NOT NULL,
        code TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS wait_data.verify_registration (
        id BIGSERIAL PRIMARY KEY,
        phone TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS wait_data.verify_driver (
        id BIGSERIAL PRIMARY KEY,
        id_driver BIGINT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS wait_data.schedule_road_drivers (
        id BIGSERIAL PRIMARY KEY,
        id_road BIGINT NOT NULL,
        id_schedule BIGINT NOT NULL,
        id_driver BIGINT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        full_time BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS wait_data.payment_tink_data (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_payment TEXT,
        id_order TEXT,
        amount BIGINT,
        ip TEXT,
        token TEXT,
        card_data TEXT,
        "TdsServerTransID" TEXT,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS wait_data.order_data (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_status BIGINT NOT NULL,
        id_type_order BIGINT NOT NULL,
        "isActive" BOOLEAN DEFAULT TRUE,
        datetime_create TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS wait_data.order_addresses_data (
        id BIGSERIAL PRIMARY KEY,
        id_order BIGINT NOT NULL,
        from_address TEXT NOT NULL,
        to_address TEXT NOT NULL,
        from_lon FLOAT NOT NULL,
        from_lat FLOAT NOT NULL,
        to_lon FLOAT NOT NULL,
        to_lat FLOAT NOT NULL,
        "isFinish" BOOLEAN DEFAULT FALSE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS wait_data.order_info_data (
        id BIGSERIAL PRIMARY KEY,
        id_order BIGINT NOT NULL,
        client_lon FLOAT,
        client_lat FLOAT,
        price DECIMAL(10, 2),
        distance BIGINT,
        duration BIGINT,
        description TEXT,
        id_tariff BIGINT NOT NULL,
        id_type_drive BIGINT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS wait_data.search_driver (
        id BIGSERIAL PRIMARY KEY,
        id_user BIGINT NOT NULL,
        id_order BIGINT NOT NULL,
        token TEXT NOT NULL
    );
    """,
)


ADMIN_TABLES: Sequence[str] = (
    """
    CREATE TABLE IF NOT EXISTS admin.mobile_settings (
        id BIGSERIAL PRIMARY KEY,
        biometry BOOLEAN NOT NULL DEFAULT FALSE
    );
    """,
)


TABLE_GROUPS: Sequence[tuple[str, Sequence[str]]] = (
    ("authentication", AUTHENTICATION_TABLES),
    ("users", USERS_TABLES),
    ("data", DATA_TABLES),
    ("chats", CHATS_TABLES),
    ("history", HISTORY_TABLES),
    ("wait_data", WAIT_DATA_TABLES),
    ("admin", ADMIN_TABLES),
)


async def execute_statements(conn: asyncpg.Connection, statements: Iterable[str]) -> None:
    for sql in statements:
        await conn.execute(sql)


async def create_schemas(conn: asyncpg.Connection) -> None:
    print("📁 Создание схем...")
    schemas = [
        "data",
        "users",
        "authentication",
        "chats",
        "history",
        "wait_data",
        "files",
        "drivers",
        "orders",
        "admin",
    ]
    for schema in schemas:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
    print(f"✅ Созданы схемы: {', '.join(schemas)}\n")


async def create_tables(conn: asyncpg.Connection) -> None:
    print("📊 Создание таблиц...")
    for schema_name, statements in TABLE_GROUPS:
        print(f"   ➤ {schema_name}")
        await execute_statements(conn, statements)
    print("✅ Все таблицы созданы\n")


async def get_or_create_id(
    conn: asyncpg.Connection,
    select_sql: str,
    select_params: Sequence,
    insert_sql: str,
    insert_params: Sequence,
) -> int:
    record_id = await conn.fetchval(select_sql, *select_params)
    if record_id is not None:
        return record_id
    return await conn.fetchval(insert_sql, *insert_params)


async def seed_reference_data(conn: asyncpg.Connection) -> None:
    print("📝 Заполнение справочников...")

    countries = ["Россия", "Беларусь", "Казахстан", "Армения", "Грузия"]
    for country in countries:
        await get_or_create_id(
            conn,
            "SELECT id FROM data.country WHERE title = $1",
            (country,),
            "INSERT INTO data.country (title) VALUES ($1) RETURNING id",
            (country,),
        )

    cities = [
        "Москва",
        "Санкт-Петербург",
        "Новосибирск",
        "Екатеринбург",
        "Казань",
        "Нижний Новгород",
        "Челябинск",
        "Самара",
        "Ростов-на-Дону",
        "Краснодар",
    ]
    for city in cities:
        await get_or_create_id(
            conn,
            "SELECT id FROM data.city WHERE title = $1",
            (city,),
            "INSERT INTO data.city (title) VALUES ($1) RETURNING id",
            (city,),
        )

    colors = ["Белый", "Черный", "Серый", "Серебристый", "Синий", "Красный", "Зеленый"]
    for color in colors:
        await get_or_create_id(
            conn,
            "SELECT id FROM data.color WHERE title = $1",
            (color,),
            "INSERT INTO data.color (title) VALUES ($1) RETURNING id",
            (color,),
        )

    car_data = {
        "Toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser"],
        "Volkswagen": ["Polo", "Tiguan", "Passat", "Golf"],
        "Kia": ["Rio", "Sportage", "Ceed", "Sorento"],
        "Hyundai": ["Solaris", "Creta", "Tucson", "Elantra"],
        "BMW": ["3 Series", "5 Series", "X5"],
    }
    for mark_title, models in car_data.items():
        mark_id = await get_or_create_id(
            conn,
            "SELECT id FROM data.car_mark WHERE title = $1",
            (mark_title,),
            "INSERT INTO data.car_mark (title) VALUES ($1) RETURNING id",
            (mark_title,),
        )
        for model_title in models:
            await get_or_create_id(
                conn,
                "SELECT id FROM data.car_model WHERE title = $1 AND id_car_mark = $2",
                (model_title, mark_id),
                'INSERT INTO data.car_model (title, id_car_mark, "releaseYear") VALUES ($1, $2, $3) RETURNING id',
                (model_title, mark_id, 2020),
            )

    account_types = (
        (1, "Родитель"),
        (2, "Водитель"),
        (3, "Оператор"),
        (4, "Менеджер"),
        (5, "Партнер"),
        (6, "Администратор франшизы"),
        (7, "Администратор"),
    )
    for type_id, title in account_types:
        await conn.execute(
            "INSERT INTO data.type_account (id, title) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title",
            type_id,
            title,
        )

    other_services = (
        ("Детское кресло", 200.00),
        ("Бустер", 150.00),
        ("Встреча с табличкой", 300.00),
        ("Багажник XL", 250.00),
        ("Услуга няни", 500.00),
    )
    for title, amount in other_services:
        await get_or_create_id(
            conn,
            "SELECT id FROM data.other_drive_parametr WHERE title = $1",
            (title,),
            'INSERT INTO data.other_drive_parametr (title, amount, "isActive") VALUES ($1, $2, TRUE) RETURNING id',
            (title, amount),
        )

    driving_statuses = (
        "Создан",
        "Поиск водителя",
        "Водитель назначен",
        "Водитель в пути",
        "Водитель прибыл",
        "В поездке",
        "Завершен",
        "Отменен",
    )
    for status in driving_statuses:
        await get_or_create_id(
            conn,
            "SELECT id FROM data.driving_status WHERE status = $1",
            (status,),
            "INSERT INTO data.driving_status (status) VALUES ($1) RETURNING id",
            (status,),
        )

    message_types = ("Текст", "Изображение", "Файл", "Системное")
    for msg_type in message_types:
        await get_or_create_id(
            conn,
            "SELECT id FROM data.message_type WHERE title = $1",
            (msg_type,),
            "INSERT INTO data.message_type (title) VALUES ($1) RETURNING id",
            (msg_type,),
        )

    balance_tasks = (
        "Пополнение",
        "Оплата поездки",
        "Возврат",
        "Вывод средств",
        "Бонус",
        "Штраф",
    )
    for task in balance_tasks:
        await get_or_create_id(
            conn,
            "SELECT id FROM data.task_balance_history WHERE title = $1",
            (task,),
            "INSERT INTO data.task_balance_history (title) VALUES ($1) RETURNING id",
            (task,),
        )

    await conn.execute(
        "INSERT INTO admin.mobile_settings (id, biometry) VALUES (1, FALSE) ON CONFLICT (id) DO NOTHING"
    )

    print("✅ Справочники заполнены\n")


async def seed_default_franchise(conn: asyncpg.Connection) -> int:
    print("🏢 Настройка франшизы по умолчанию...")
    franchise_id = settings.default_franchise_id
    existing_id = await conn.fetchval("SELECT id FROM users.franchise WHERE id = $1", franchise_id)
    if existing_id is None:
        existing_id = await conn.fetchval(
            'INSERT INTO users.franchise (id, title, description, "isActive", datetime_create) VALUES ($1, $2, $3, TRUE, $4) RETURNING id',
            franchise_id,
            settings.default_franchise_name,
            "Основная франшиза проекта АвтоНяня",
            datetime.now(),
        )
    else:
        await conn.execute(
            'UPDATE users.franchise SET title = $2, description = $3, "isActive" = TRUE WHERE id = $1',
            franchise_id,
            settings.default_franchise_name,
            "Основная франшиза проекта АвтоНяня",
        )

    moscow_id = await conn.fetchval("SELECT id FROM data.city WHERE title = 'Москва'")
    if moscow_id:
        await conn.execute(
            "INSERT INTO users.franchise_city (id_franchise, id_city) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            existing_id,
            moscow_id,
        )

    print(f"✅ Франшиза готова (ID: {existing_id})\n")
    return existing_id


async def seed_car_tariffs(conn: asyncpg.Connection, franchise_id: int) -> None:
    tariffs = (
        ("Эконом", "Экономичный тариф", 450, True, 0),
        ("Комфорт", "Комфортный тариф", 650, True, 0),
        ("График", "Регулярные поездки", 1500, False, 10),
    )
    for title, description, amount, one_time, percent in tariffs:
        tariff_id = await conn.fetchval(
            "SELECT id FROM data.car_tariff WHERE title = $1 AND id_franchise = $2",
            title,
            franchise_id,
        )

        if tariff_id is None:
            await conn.execute(
                'INSERT INTO data.car_tariff (title, description, amount, one_time, percent, id_franchise, "isActive", datetime_create) '
                'VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7)',
                title,
                description,
                amount,
                one_time,
                percent,
                franchise_id,
                datetime.now(),
            )
        else:
            await conn.execute(
                'UPDATE data.car_tariff SET description = $2, amount = $3, one_time = $4, percent = $5, "isActive" = TRUE WHERE id = $1',
                tariff_id,
                description,
                amount,
                one_time,
                percent,
            )


async def ensure_authorization(
    conn: asyncpg.Connection,
    user_id: int,
    login: str,
    password_hash: str,
    account_type: int,
) -> None:
    auth_id = await conn.fetchval(
        "SELECT id FROM authentication.authorization_data WHERE login = $1",
        login,
    )
    if auth_id is None:
        await conn.execute(
            "INSERT INTO authentication.authorization_data (login, password, id_user) VALUES ($1, $2, $3)",
            login,
            password_hash,
            user_id,
        )

    if await conn.fetchval(
        "SELECT id FROM authentication.user_account WHERE id_user = $1 AND id_type_account = $2",
        user_id,
        account_type,
    ) is None:
        await conn.execute(
            "INSERT INTO authentication.user_account (id_user, id_type_account) VALUES ($1, $2)",
            user_id,
            account_type,
        )

    if await conn.fetchval(
        "SELECT id FROM authentication.verify_account WHERE id_user = $1",
        user_id,
    ) is None:
        await conn.execute(
            "INSERT INTO authentication.verify_account (id_user) VALUES ($1)",
            user_id,
        )


async def seed_parent(conn: asyncpg.Connection, franchise_id: int, password_hash: str) -> None:
    phone = "+79991234567"
    user_row = await conn.fetchrow('SELECT id FROM users."user" WHERE phone = $1', phone)
    if user_row:
        user_id = user_row["id"]
        await conn.execute(
            'UPDATE users."user" SET surname = $2, name = $3, "isActive" = TRUE WHERE id = $1',
            user_id,
            "Иванов",
            "Иван",
        )
    else:
        user_id = await conn.fetchval(
            'INSERT INTO users."user" (surname, name, phone, "isActive", datetime_create) VALUES ($1, $2, $3, TRUE, $4) RETURNING id',
            "Иванов",
            "Иван",
            phone,
            datetime.now(),
        )

    await ensure_authorization(conn, user_id, phone, password_hash, 1)

    await conn.execute(
        "INSERT INTO users.franchise_user (id_user, id_franchise) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        user_id,
        franchise_id,
    )

    children = [
        ("Иванов", "Петр", "Иванович", 7),
        ("Иванова", "Мария", "Ивановна", 5),
    ]
    for surname, name, patronymic, age in children:
        exists = await conn.fetchval(
            "SELECT id FROM users.child WHERE id_user = $1 AND name = $2 AND surname = $3",
            user_id,
            name,
            surname,
        )
        if exists is None:
            await conn.execute(
                'INSERT INTO users.child (surname, name, patronymic, age, id_user, "isActive", datetime_create) VALUES ($1, $2, $3, $4, $5, TRUE, $6)',
                surname,
                name,
                patronymic,
                age,
                user_id,
                datetime.now(),
            )

    # Добавляем баланс для родителя
    balance_exists = await conn.fetchval(
        "SELECT id FROM data.user_balance WHERE id_user = $1",
        user_id,
    )
    if balance_exists is None:
        await conn.execute(
            "INSERT INTO data.user_balance (id_user, money) VALUES ($1, $2)",
            user_id,
            5000.00,  # Начальный баланс 5000 руб
        )

    print(f"✅ Родитель готов: {phone}")


async def seed_driver(conn: asyncpg.Connection, franchise_id: int, password_hash: str) -> None:
    phone = "+79997654321"
    driver_row = await conn.fetchrow('SELECT id FROM users."user" WHERE phone = $1', phone)
    if driver_row:
        driver_id = driver_row["id"]
        await conn.execute(
            'UPDATE users."user" SET surname = $2, name = $3, "isActive" = TRUE WHERE id = $1',
            driver_id,
            "Петров",
            "Петр",
        )
    else:
        driver_id = await conn.fetchval(
            'INSERT INTO users."user" (surname, name, phone, "isActive", datetime_create) VALUES ($1, $2, $3, TRUE, $4) RETURNING id',
            "Петров",
            "Петр",
            phone,
            datetime.now(),
        )

    await ensure_authorization(conn, driver_id, phone, password_hash, 2)

    await conn.execute(
        "INSERT INTO users.franchise_user (id_user, id_franchise) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        driver_id,
        franchise_id,
    )

    country_id = await conn.fetchval("SELECT id FROM data.country WHERE title = 'Россия'")
    driver_card_id = await get_or_create_id(
        conn,
        "SELECT id FROM users.driver_card WHERE license = $1",
        ("77 77 123456",),
        "INSERT INTO users.driver_card (id_country, license, date_of_issue) VALUES ($1, $2, $3) RETURNING id",
        (country_id, "77 77 123456", datetime(2015, 5, 20).date()),
    )

    driver_answer_id = await get_or_create_id(
        conn,
        "SELECT id FROM users.driver_answer WHERE first_answer = $1 AND second_answer = $2",
        ("Опыт 5 лет", "Есть личный автомобиль"),
        "INSERT INTO users.driver_answer (first_answer, second_answer, third_answer, four_answer, five_answer, six_answer, seven_answer) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id",
        (
            "Опыт 5 лет",
            "Есть личный автомобиль",
            "Готов работать по графику",
            "Не привлекался",
            "Имею справки",
            "Готов учиться",
            "Есть рекомендации",
        ),
    )

    mark_id = await conn.fetchval("SELECT id FROM data.car_mark WHERE title = 'Toyota'")
    model_id = await conn.fetchval("SELECT id FROM data.car_model WHERE title = 'Camry'")
    color_id = await conn.fetchval("SELECT id FROM data.color WHERE title = 'Белый'")
    car_id = await get_or_create_id(
        conn,
        "SELECT id FROM users.car WHERE state_number = $1",
        ("А123БВ777",),
        "INSERT INTO users.car (id_car_mark, id_car_model, id_color, year_create, state_number, ctc) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
        (mark_id, model_id, color_id, 2020, "А123БВ777", "99 99 123456"),
    )

    city_id = await conn.fetchval("SELECT id FROM data.city WHERE title = 'Москва'")
    driver_data_exists = await conn.fetchval(
        "SELECT id FROM users.driver_data WHERE id_driver = $1",
        driver_id,
    )
    if driver_data_exists is None:
        await conn.execute(
            'INSERT INTO users.driver_data (id_driver, id_city, description, age, video_url, id_driver_card, id_car, id_driver_answer, "isActive", inn, datetime_create) '
            'VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE, $9, $10)',
            driver_id,
            city_id,
            "Водитель с опытом работы в семейном такси",
            35,
            "https://example.com/video",
            driver_card_id,
            car_id,
            driver_answer_id,
            "771234567890",
            datetime.now(),
        )

    print(f"✅ Водитель готов: {phone}")


async def seed_admin(conn: asyncpg.Connection, password_hash: str) -> None:
    phone = "+79995555555"
    admin_row = await conn.fetchrow('SELECT id FROM users."user" WHERE phone = $1', phone)
    if admin_row:
        admin_id = admin_row["id"]
        await conn.execute(
            'UPDATE users."user" SET surname = $2, name = $3, "isActive" = TRUE WHERE id = $1',
            admin_id,
            "Админов",
            "Админ",
        )
    else:
        admin_id = await conn.fetchval(
            'INSERT INTO users."user" (surname, name, phone, "isActive", datetime_create) VALUES ($1, $2, $3, TRUE, $4) RETURNING id',
            "Админов",
            "Админ",
            phone,
            datetime.now(),
        )

    await ensure_authorization(conn, admin_id, phone, password_hash, 7)

    print(f"✅ Администратор готов: {phone}")


async def seed_test_users(conn: asyncpg.Connection, franchise_id: int) -> None:
    print("👥 Создание тестовых пользователей...")
    password_hash = hashlib.md5("password123".encode()).hexdigest()

    await seed_parent(conn, franchise_id, password_hash)
    await seed_driver(conn, franchise_id, password_hash)
    await seed_admin(conn, password_hash)

    print("✅ Тестовые учетные записи созданы\n")


async def seed_demo_entities(conn: asyncpg.Connection, franchise_id: int) -> None:
    print("📦 Создание демонстрационных данных...")

    parent_id = await conn.fetchval("SELECT id FROM users.user WHERE phone = '+79991234567'")
    driver_id = await conn.fetchval("SELECT id FROM users.user WHERE phone = '+79997654321'")
    tariff_id = await conn.fetchval("SELECT id FROM data.car_tariff WHERE title = 'Эконом' AND id_franchise = $1", franchise_id)
    status_id = await conn.fetchval("SELECT id FROM data.driving_status WHERE status = 'Поиск водителя'")

    existing_order = await conn.fetchval(
        "SELECT id FROM data.""order"" WHERE id_user = $1",
        parent_id,
    )

    if existing_order is None:
        order_id = await conn.fetchval(
            'INSERT INTO data."order" (id_user, id_driver, id_status, id_type_order, type_drive, "isActive", datetime_create) '
            'VALUES ($1, $2, $3, $4, $5, TRUE, $6) RETURNING id',
            parent_id,
            driver_id,
            status_id,
            tariff_id,
            "0",
            datetime.now(),
        )

        await conn.execute(
            'INSERT INTO data.order_addresses (id_order, from_address, to_address, from_lon, from_lat, to_lon, to_lat, "isFinish") '
            'VALUES ($1, $2, $3, $4, $5, $6, $7, FALSE)',
            order_id,
            "Москва, ул. Тверская, 1",
            "Москва, ул. Арбат, 10",
            37.613,
            55.757,
            37.597,
            55.752,
        )

        await conn.execute(
            'INSERT INTO data.order_info (id_order, client_lon, client_lat, price, distance, duration, description, id_tariff) '
            'VALUES ($1, $2, $3, $4, $5, $6, $7, $8)',
            order_id,
            37.613,
            55.757,
            750.00,
            5600,
            1800,
            "Поездка в школу",
            tariff_id,
        )

    # Демонстрация графика
    schedule_exists = await conn.fetchval(
        "SELECT id FROM data.schedule WHERE id_user = $1",
        parent_id,
    )
    if schedule_exists is None:
        schedule_id = await conn.fetchval(
            'INSERT INTO data.schedule (id_user, title, description, duration, children_count, id_tariff, week_days, "isActive", datetime_create) '
            'VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, $8) RETURNING id',
            parent_id,
            "Утренняя школа",
            "Регулярная доставка в школу",
            60,
            1,
            tariff_id,
            "1,2,3,4,5",
            datetime.now(),
        )

        road_id = await conn.fetchval(
            'INSERT INTO data.schedule_road (id_schedule, week_day, title, start_time, end_time, type_drive, amount, "isActive", datetime_create) '
            'VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, $8) RETURNING id',
            schedule_id,
            1,
            "Утренний маршрут",
            "07:30",
            "08:10",
            "0",
            750.00,
            datetime.now(),
        )

        await conn.execute(
            'INSERT INTO data.schedule_road_address (id_schedule_road, from_address, to_address, from_lon, from_lat, to_lon, to_lat) '
            'VALUES ($1, $2, $3, $4, $5, $6, $7)',
            road_id,
            "Москва, ул. Тверская, 1",
            "Москва, ул. Арбат, 10",
            37.613,
            55.757,
            37.597,
            55.752,
        )

        await conn.execute(
            'INSERT INTO data.schedule_road_driver (id_schedule_road, id_driver, "isRepeat", "isActive", datetime_create) '
            'VALUES ($1, $2, TRUE, TRUE, $3)',
            road_id,
            driver_id,
            datetime.now(),
        )

    print("✅ Демонстрационные данные готовы\n")


async def seed_child_data(conn: asyncpg.Connection) -> None:
    """Заполнение медицинской информации и экстренных контактов для детей"""
    print("🏥 Создание медицинских данных и экстренных контактов...")
    
    # Получаем ID родителя
    parent_id = await conn.fetchval("SELECT id FROM users.user WHERE phone = '+79991234567'")
    if not parent_id:
        print("⚠️  Родитель не найден, пропускаем заполнение")
        return
    
    # Получаем детей родителя
    children = await conn.fetch(
        "SELECT id, name, surname FROM users.child WHERE id_user = $1",
        parent_id
    )
    
    if not children:
        print("⚠️  Дети не найдены, пропускаем заполнение")
        return
    
    for child in children:
        child_id = child["id"]
        child_name = f"{child['name']} {child['surname']}"
        
        # Добавляем медицинскую информацию
        medical_exists = await conn.fetchval(
            "SELECT id FROM users.child_medical_info WHERE id_child = $1 AND \"isActive\" = TRUE",
            child_id,
        )
        
        if medical_exists is None:
            if child["name"] == "Петр":
                # Для Петра - астма и аллергии
                await conn.execute(
                    'INSERT INTO users.child_medical_info (id_child, allergies, chronic_diseases, medications, '
                    'medical_policy_number, blood_type, special_needs, doctor_notes, "isActive", datetime_create) '
                    'VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE, $9)',
                    child_id,
                    "Аллергия на пыльцу березы, орехи (арахис, фундук)",
                    "Бронхиальная астма легкой степени",
                    "Ингалятор Вентолин (по необходимости), Антигистаминные при обострении аллергии",
                    "1234567890123456",
                    "A+",
                    "Требуется ингалятор при физических нагрузках. Избегать контакта с аллергенами.",
                    "Рекомендован регулярный контроль астмы. Избегать пыльных помещений в период цветения.",
                    datetime.now(),
                )
                print(f"   ✓ Медицинская информация для {child_name} (астма, аллергии)")
            else:
                # Для Марии - без серьезных проблем
                await conn.execute(
                    'INSERT INTO users.child_medical_info (id_child, blood_type, medical_policy_number, '
                    '"isActive", datetime_create) '
                    'VALUES ($1, $2, $3, TRUE, $4)',
                    child_id,
                    "B+",
                    "9876543210987654",
                    datetime.now(),
                )
                print(f"   ✓ Медицинская информация для {child_name} (без особенностей)")
        
        # Добавляем экстренные контакты
        contacts_exist = await conn.fetchval(
            "SELECT COUNT(*) FROM users.child_emergency_contact WHERE id_child = $1 AND \"isActive\" = TRUE",
            child_id,
        )
        
        if contacts_exist == 0:
            # Контакт 1: Мама
            await conn.execute(
                'INSERT INTO users.child_emergency_contact (id_child, name, relationship, phone, priority, '
                'notes, "isActive", datetime_create) '
                'VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7)',
                child_id,
                "Иванова Мария Петровна",
                "Мама",
                "+7 (999) 111 22 33",
                1,
                "Основной контакт, всегда на связи",
                datetime.now(),
            )
            
            # Контакт 2: Бабушка
            await conn.execute(
                'INSERT INTO users.child_emergency_contact (id_child, name, relationship, phone, priority, '
                'notes, "isActive", datetime_create) '
                'VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7)',
                child_id,
                "Иванова Анна Сергеевна",
                "Бабушка",
                "+7 (999) 444 55 66",
                2,
                "Живет рядом, может забрать ребенка в любое время",
                datetime.now(),
            )
            
            # Контакт 3: Папа
            await conn.execute(
                'INSERT INTO users.child_emergency_contact (id_child, name, relationship, phone, priority, '
                '"isActive", datetime_create) '
                'VALUES ($1, $2, $3, $4, $5, TRUE, $6)',
                child_id,
                "Иванов Иван Иванович",
                "Папа",
                "+7 (999) 123 45 67",
                3,
                datetime.now(),
            )
            
            print(f"   ✓ Экстренные контакты для {child_name} (3 контакта)")
    
    print("✅ Медицинские данные и экстренные контакты созданы\n")


async def main() -> None:
    print("🚀 Полная инициализация БД AutoNanny\n")
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
    )

    try:
        await create_schemas(conn)
        await create_tables(conn)
        await seed_reference_data(conn)
        franchise_id = await seed_default_franchise(conn)
        await seed_car_tariffs(conn, franchise_id)
        await seed_test_users(conn, franchise_id)
        await seed_demo_entities(conn, franchise_id)
        await seed_child_data(conn)

        print("=" * 60)
        print("✅ База данных успешно инициализирована и заполнена!")
        print("=" * 60)
        print("\n📝 Тестовые учетные записи:")
        print("1️⃣ Родитель     : +79991234567 / password123")
        print("2️⃣ Водитель     : +79997654321 / password123")
        print("3️⃣ Администратор: +79995555555 / password123")
        print("\n👶 Тестовые дети:")
        print("• Петр Иванов (7 лет) - с медицинской информацией (астма, аллергии)")
        print("• Мария Иванова (5 лет) - без особенностей")
        print("\n🏥 Медицинские данные:")
        print("• Медицинская информация для обоих детей")
        print("• 3 экстренных контакта для каждого ребенка")
        print("\n💰 Финансы:")
        print("• Баланс родителя: 5000 руб")
        print("• Демо-заказ и график созданы\n")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=".env")
load_dotenv(dotenv_path="../.env")
load_dotenv(dotenv_path="../../.env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application Settings
    app_name: str = "AutoNanny"
    port: int = 8000
    log_level: str = "info"
    ssl_certfile: str = "fullchain.pem"
    ssl_keyfile: str = "privkey.pem"
    report_file_path: str = "./"

    # Database
    database_url: str = "postgres://api_auto_nanny:password@localhost:5432/api_nanny"

    # Security
    secret_key: str = "change-this-secret-key-in-production"

    # Google Maps API
    google_maps_api_key: str = ""

    # Firebase Configuration
    firebase_client_credentials: str = "fb_client.json"
    firebase_driver_credentials: str = "fb_driver.json"
    firebase_dynamic_links_api_key: str = ""
    firebase_dynamic_links_domain: str = "https://nyago.page.link"

    # SMS Aero
    sms_aero_email: str = ""
    sms_aero_api_key: str = ""

    # Yandex OAuth
    yandex_client_id: str = ""
    yandex_client_secret: str = ""

    # Tinkoff Payment Configuration
    tinkoff_terminal_key: str = ""
    tinkoff_secret_key: str = ""
    tinkoff_api_url: str = "https://securepay.tinkoff.ru/v2"

    # Test Credentials
    test_admin_login: str = ""
    test_admin_password: str = ""
    test_franchise_admin_login: str = ""
    test_franchise_admin_password: str = ""
    test_driver_login: str = ""
    test_driver_password: str = ""

    # Franchise Settings (MVP: single franchise)
    default_franchise_id: int = 1
    default_franchise_name: str = "АвтоНяня Москва"


settings = Settings()
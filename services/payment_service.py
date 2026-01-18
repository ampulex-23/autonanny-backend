"""
Сервисный слой для работы с платежами (Tinkoff API).
BE-MVP-004: Рефакторинг users.py
"""
import hashlib
import uuid
from typing import Dict, Optional, Tuple
from decimal import Decimal
import requests

from config import settings
from models.users_db import DataUserBalance, DataUserBalanceHistory
from common.logger import logger


class PaymentService:
    """Сервис для работы с платежами через Tinkoff API"""
    
    MIN_PAYMENT_AMOUNT = 100  # Минимальная сумма платежа (руб)
    
    @staticmethod
    def generate_tinkoff_token(amount: int, payment_id: str) -> str:
        """
        Генерирует токен для запросов к Tinkoff API.
        
        Args:
            amount: Сумма платежа в копейках
            payment_id: ID платежа
            
        Returns:
            str: SHA256 хеш токена
        """
        token_string = f"{amount}{settings.tinkoff_secret_key}{payment_id}{settings.tinkoff_terminal_key}"
        return hashlib.sha256(token_string.encode()).hexdigest()
    
    @staticmethod
    def validate_payment_amount(amount: float) -> Tuple[bool, Optional[str]]:
        """
        Валидирует сумму платежа.
        
        Args:
            amount: Сумма в рублях
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if amount < PaymentService.MIN_PAYMENT_AMOUNT:
            return False, f"Минимальная сумма пополнения: {PaymentService.MIN_PAYMENT_AMOUNT} руб"
        
        if amount > 75000:  # Максимум для одного платежа
            return False, "Максимальная сумма пополнения: 75000 руб"
        
        return True, None
    
    @staticmethod
    async def init_sbp_payment(
        user_id: int,
        amount: float,
        description: str = "Пополнение баланса"
    ) -> Dict:
        """
        Инициирует платеж через СБП (Система Быстрых Платежей).
        
        Args:
            user_id: ID пользователя
            amount: Сумма в рублях
            description: Описание платежа
            
        Returns:
            Dict: Ответ от Tinkoff API с QR-кодом и ссылкой
        """
        # Валидация суммы
        is_valid, error = PaymentService.validate_payment_amount(amount)
        if not is_valid:
            raise ValueError(error)
        
        # Генерация ID платежа
        payment_id = str(uuid.uuid4())
        amount_kopecks = int(amount * 100)
        
        # Генерация токена
        token = PaymentService.generate_tinkoff_token(amount_kopecks, payment_id)
        
        # Подготовка данных для API
        payload = {
            "TerminalKey": settings.tinkoff_terminal_key,
            "Amount": amount_kopecks,
            "OrderId": payment_id,
            "Description": description,
            "Token": token,
            "DATA": {
                "QR": "true"
            }
        }
        
        logger.info(
            f"Initiating SBP payment for user {user_id}",
            extra={
                "user_id": user_id,
                "amount": amount,
                "payment_id": payment_id
            }
        )
        
        # Запрос к Tinkoff API
        try:
            response = requests.post(
                f"{settings.tinkoff_api_url}/Init",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(
                f"SBP payment initiated successfully",
                extra={
                    "user_id": user_id,
                    "payment_id": payment_id,
                    "tinkoff_payment_id": result.get("PaymentId")
                }
            )
            
            return result
            
        except requests.RequestException as e:
            logger.error(
                f"Failed to initiate SBP payment",
                extra={
                    "user_id": user_id,
                    "payment_id": payment_id,
                    "error": str(e)
                }
            )
            raise
    
    @staticmethod
    async def init_card_payment(
        user_id: int,
        amount: float,
        description: str = "Пополнение баланса",
        return_url: Optional[str] = None
    ) -> Dict:
        """
        Инициирует платеж банковской картой.
        
        Args:
            user_id: ID пользователя
            amount: Сумма в рублях
            description: Описание платежа
            return_url: URL для возврата после оплаты
            
        Returns:
            Dict: Ответ от Tinkoff API с URL для оплаты
        """
        # Валидация суммы
        is_valid, error = PaymentService.validate_payment_amount(amount)
        if not is_valid:
            raise ValueError(error)
        
        # Генерация ID платежа
        payment_id = str(uuid.uuid4())
        amount_kopecks = int(amount * 100)
        
        # Генерация токена
        token = PaymentService.generate_tinkoff_token(amount_kopecks, payment_id)
        
        # Подготовка данных для API
        payload = {
            "TerminalKey": settings.tinkoff_terminal_key,
            "Amount": amount_kopecks,
            "OrderId": payment_id,
            "Description": description,
            "Token": token
        }
        
        if return_url:
            payload["SuccessURL"] = return_url
            payload["FailURL"] = return_url
        
        logger.info(
            f"Initiating card payment for user {user_id}",
            extra={
                "user_id": user_id,
                "amount": amount,
                "payment_id": payment_id
            }
        )
        
        # Запрос к Tinkoff API
        try:
            response = requests.post(
                f"{settings.tinkoff_api_url}/Init",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(
                f"Card payment initiated successfully",
                extra={
                    "user_id": user_id,
                    "payment_id": payment_id,
                    "tinkoff_payment_id": result.get("PaymentId")
                }
            )
            
            return result
            
        except requests.RequestException as e:
            logger.error(
                f"Failed to initiate card payment",
                extra={
                    "user_id": user_id,
                    "payment_id": payment_id,
                    "error": str(e)
                }
            )
            raise
    
    @staticmethod
    async def check_payment_status(payment_id: str) -> Dict:
        """
        Проверяет статус платежа в Tinkoff.
        
        Args:
            payment_id: ID платежа в системе Tinkoff
            
        Returns:
            Dict: Статус платежа
        """
        payload = {
            "TerminalKey": settings.tinkoff_terminal_key,
            "PaymentId": payment_id
        }
        
        try:
            response = requests.post(
                f"{settings.tinkoff_api_url}/GetState",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(
                f"Failed to check payment status",
                extra={"payment_id": payment_id, "error": str(e)}
            )
            raise
    
    @staticmethod
    async def add_money_to_balance(
        user_id: int,
        amount: float,
        payment_id: str,
        description: str = "Пополнение баланса"
    ) -> bool:
        """
        Добавляет деньги на баланс пользователя.
        
        Args:
            user_id: ID пользователя
            amount: Сумма в рублях
            payment_id: ID платежа
            description: Описание операции
            
        Returns:
            bool: True если операция успешна
        """
        try:
            # Получаем или создаем баланс
            balance = await DataUserBalance.filter(id_user=user_id).first()
            
            if not balance:
                balance = await DataUserBalance.create(
                    id_user=user_id,
                    amount=Decimal(0)
                )
            
            # Обновляем баланс
            new_amount = balance.amount + Decimal(amount)
            await DataUserBalance.filter(id_user=user_id).update(amount=new_amount)
            
            # Записываем в историю
            await DataUserBalanceHistory.create(
                id_user=user_id,
                amount=Decimal(amount),
                description=description,
                payment_id=payment_id,
                operation_type="deposit"
            )
            
            logger.info(
                f"Money added to balance",
                extra={
                    "user_id": user_id,
                    "amount": amount,
                    "new_balance": float(new_amount),
                    "payment_id": payment_id
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to add money to balance",
                extra={
                    "user_id": user_id,
                    "amount": amount,
                    "payment_id": payment_id,
                    "error": str(e)
                }
            )
            raise
    
    @staticmethod
    async def get_balance(user_id: int) -> Decimal:
        """
        Получает текущий баланс пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Decimal: Баланс в рублях
        """
        balance = await DataUserBalance.filter(id_user=user_id).first()
        return balance.amount if balance else Decimal(0)
    
    @staticmethod
    async def get_balance_history(
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> list:
        """
        Получает историю операций по балансу.
        
        Args:
            user_id: ID пользователя
            limit: Количество записей
            offset: Смещение
            
        Returns:
            list: История операций
        """
        history = await DataUserBalanceHistory.filter(
            id_user=user_id
        ).order_by("-datetime_create").offset(offset).limit(limit).all().values()
        
        return history

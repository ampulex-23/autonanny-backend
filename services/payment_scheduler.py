"""
BE-MVP-009: Автоматическое еженедельное списание средств
Cron-job для списания средств с карт родителей за активные контракты
"""

import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Any

from models.users_db import (
    WeeklyPaymentSchedule, 
    WeeklyPaymentHistory,
    DataDebitCard,
    DataUserBalance,
    DataUserBalanceHistory,
    UsersUser
)
from models.orders_db import DataSchedule
from services.payment_service import PaymentService
from defs import sendPush

logger = logging.getLogger(__name__)


class PaymentScheduler:
    """Сервис для автоматического еженедельного списания средств"""
    
    @staticmethod
    async def process_weekly_payments() -> Dict[str, Any]:
        """
        Основная функция для обработки еженедельных платежей.
        Вызывается cron-job каждый день.
        
        Returns:
            Dict с результатами обработки
        """
        logger.info("Starting weekly payments processing", extra={"event_type": "weekly_payments_start"})
        
        today = date.today()
        results = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "suspended": 0,
            "errors": []
        }
        
        try:
            # Получаем все активные расписания, где дата списания сегодня или раньше
            schedules = await WeeklyPaymentSchedule.filter(
                isActive=True,
                status='active',
                next_payment_date__lte=today
            ).all()
            
            logger.info(
                f"Found {len(schedules)} schedules for processing",
                extra={
                    "count": len(schedules),
                    "date": str(today),
                    "event_type": "weekly_payments_schedules_found"
                }
            )
            
            for schedule in schedules:
                results["processed"] += 1
                
                try:
                    success = await PaymentScheduler._process_single_payment(schedule)
                    
                    if success:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        
                        # Проверяем количество неудачных попыток
                        if schedule.failed_attempts >= 3:
                            await PaymentScheduler._suspend_contract(schedule)
                            results["suspended"] += 1
                            
                except Exception as e:
                    logger.error(
                        f"Error processing schedule {schedule.id}: {str(e)}",
                        extra={
                            "schedule_id": schedule.id,
                            "user_id": schedule.id_user,
                            "error": str(e),
                            "event_type": "weekly_payment_processing_error"
                        }
                    )
                    results["errors"].append({
                        "schedule_id": schedule.id,
                        "error": str(e)
                    })
            
            logger.info(
                "Weekly payments processing completed",
                extra={
                    "results": results,
                    "event_type": "weekly_payments_completed"
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(
                f"Critical error in weekly payments processing: {str(e)}",
                extra={
                    "error": str(e),
                    "event_type": "weekly_payments_critical_error"
                }
            )
            raise
    
    @staticmethod
    async def _process_single_payment(schedule: WeeklyPaymentSchedule) -> bool:
        """
        Обработка одного платежа.
        
        Args:
            schedule: Расписание платежа
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Получаем карту пользователя
            card = await DataDebitCard.filter(
                id=schedule.id_card,
                isActive=True
            ).first()
            
            if not card:
                # Пытаемся найти любую активную карту пользователя
                card = await DataDebitCard.filter(
                    id_user=schedule.id_user,
                    isActive=True
                ).first()
                
                if not card:
                    await PaymentScheduler._log_payment_failure(
                        schedule,
                        "Не найдена активная карта для списания"
                    )
                    return False
            
            # Попытка списания через Tinkoff
            payment_result = await PaymentService.charge_card(
                card_id=card.id,
                amount=float(schedule.amount),
                description=f"Еженедельная оплата контракта #{schedule.id_schedule}"
            )
            
            if payment_result.get("success"):
                # Успешное списание
                await PaymentScheduler._log_payment_success(schedule, payment_result)
                await PaymentScheduler._update_schedule_after_success(schedule)
                await PaymentScheduler._notify_payment_success(schedule)
                return True
            else:
                # Неудачное списание
                error_msg = payment_result.get("error", "Неизвестная ошибка")
                await PaymentScheduler._log_payment_failure(schedule, error_msg)
                await PaymentScheduler._update_schedule_after_failure(schedule, error_msg)
                await PaymentScheduler._notify_payment_failure(schedule, error_msg)
                return False
                
        except Exception as e:
            logger.error(
                f"Error processing payment for schedule {schedule.id}: {str(e)}",
                extra={
                    "schedule_id": schedule.id,
                    "user_id": schedule.id_user,
                    "error": str(e),
                    "event_type": "single_payment_error"
                }
            )
            await PaymentScheduler._log_payment_failure(schedule, str(e))
            return False
    
    @staticmethod
    async def _log_payment_success(schedule: WeeklyPaymentSchedule, payment_result: Dict):
        """Логирование успешного платежа"""
        await WeeklyPaymentHistory.create(
            id_schedule_payment=schedule.id,
            id_user=schedule.id_user,
            id_schedule=schedule.id_schedule,
            amount=schedule.amount,
            id_card=schedule.id_card,
            status='success',
            payment_id=payment_result.get("payment_id"),
            datetime_create=datetime.now()
        )
        
        logger.info(
            f"Payment successful for schedule {schedule.id}",
            extra={
                "schedule_id": schedule.id,
                "user_id": schedule.id_user,
                "amount": float(schedule.amount),
                "event_type": "weekly_payment_success"
            }
        )
    
    @staticmethod
    async def _log_payment_failure(schedule: WeeklyPaymentSchedule, error_msg: str):
        """Логирование неудачного платежа"""
        await WeeklyPaymentHistory.create(
            id_schedule_payment=schedule.id,
            id_user=schedule.id_user,
            id_schedule=schedule.id_schedule,
            amount=schedule.amount,
            id_card=schedule.id_card,
            status='failed',
            error_message=error_msg,
            datetime_create=datetime.now()
        )
        
        logger.warning(
            f"Payment failed for schedule {schedule.id}: {error_msg}",
            extra={
                "schedule_id": schedule.id,
                "user_id": schedule.id_user,
                "amount": float(schedule.amount),
                "error": error_msg,
                "event_type": "weekly_payment_failed"
            }
        )
    
    @staticmethod
    async def _update_schedule_after_success(schedule: WeeklyPaymentSchedule):
        """Обновление расписания после успешного платежа"""
        next_date = schedule.next_payment_date + timedelta(days=7)
        
        await WeeklyPaymentSchedule.filter(id=schedule.id).update(
            last_payment_date=schedule.next_payment_date,
            next_payment_date=next_date,
            failed_attempts=0,
            last_error=None,
            datetime_update=datetime.now()
        )
    
    @staticmethod
    async def _update_schedule_after_failure(schedule: WeeklyPaymentSchedule, error_msg: str):
        """Обновление расписания после неудачного платежа"""
        await WeeklyPaymentSchedule.filter(id=schedule.id).update(
            failed_attempts=schedule.failed_attempts + 1,
            last_error=error_msg,
            datetime_update=datetime.now()
        )
    
    @staticmethod
    async def _suspend_contract(schedule: WeeklyPaymentSchedule):
        """
        Приостановка контракта после 3 неудачных попыток.
        """
        # Обновляем статус расписания
        await WeeklyPaymentSchedule.filter(id=schedule.id).update(
            status='suspended',
            datetime_update=datetime.now()
        )
        
        # Деактивируем контракт
        await DataSchedule.filter(id=schedule.id_schedule).update(
            isActive=False
        )
        
        logger.warning(
            f"Contract suspended due to payment failures",
            extra={
                "schedule_id": schedule.id,
                "user_id": schedule.id_user,
                "contract_id": schedule.id_schedule,
                "failed_attempts": schedule.failed_attempts,
                "event_type": "contract_suspended"
            }
        )
        
        # Уведомляем пользователя
        await PaymentScheduler._notify_contract_suspended(schedule)
    
    @staticmethod
    async def _notify_payment_success(schedule: WeeklyPaymentSchedule):
        """Уведомление об успешном списании"""
        try:
            user = await UsersUser.filter(id=schedule.id_user).first()
            if user:
                await sendPush(
                    user_id=schedule.id_user,
                    title="Списание выполнено",
                    body=f"Успешно списано {schedule.amount} ₽ за контракт",
                    data={"type": "weekly_payment_success", "schedule_id": schedule.id}
                )
        except Exception as e:
            logger.error(f"Error sending success notification: {str(e)}")
    
    @staticmethod
    async def _notify_payment_failure(schedule: WeeklyPaymentSchedule, error_msg: str):
        """Уведомление о неудачном списании"""
        try:
            user = await UsersUser.filter(id=schedule.id_user).first()
            if user:
                await sendPush(
                    user_id=schedule.id_user,
                    title="Ошибка списания",
                    body=f"Не удалось списать {schedule.amount} ₽. Проверьте карту.",
                    data={
                        "type": "weekly_payment_failed",
                        "schedule_id": schedule.id,
                        "error": error_msg
                    }
                )
        except Exception as e:
            logger.error(f"Error sending failure notification: {str(e)}")
    
    @staticmethod
    async def _notify_contract_suspended(schedule: WeeklyPaymentSchedule):
        """Уведомление о приостановке контракта"""
        try:
            user = await UsersUser.filter(id=schedule.id_user).first()
            if user:
                await sendPush(
                    user_id=schedule.id_user,
                    title="Контракт приостановлен",
                    body=f"Контракт приостановлен из-за неудачных попыток оплаты. Пополните баланс.",
                    data={
                        "type": "contract_suspended",
                        "schedule_id": schedule.id,
                        "contract_id": schedule.id_schedule
                    }
                )
        except Exception as e:
            logger.error(f"Error sending suspension notification: {str(e)}")
    
    @staticmethod
    async def create_payment_schedule(
        user_id: int,
        schedule_id: int,
        amount: Decimal,
        card_id: int = None,
        start_date: date = None
    ) -> WeeklyPaymentSchedule:
        """
        Создание расписания еженедельных платежей для нового контракта.
        
        Args:
            user_id: ID пользователя
            schedule_id: ID контракта
            amount: Сумма еженедельного платежа
            card_id: ID карты (опционально)
            start_date: Дата первого платежа (по умолчанию через 7 дней)
            
        Returns:
            Созданное расписание
        """
        if start_date is None:
            start_date = date.today() + timedelta(days=7)
        
        schedule = await WeeklyPaymentSchedule.create(
            id_user=user_id,
            id_schedule=schedule_id,
            amount=amount,
            id_card=card_id,
            next_payment_date=start_date,
            status='active',
            datetime_create=datetime.now()
        )
        
        logger.info(
            f"Created payment schedule for contract {schedule_id}",
            extra={
                "schedule_id": schedule.id,
                "user_id": user_id,
                "contract_id": schedule_id,
                "amount": float(amount),
                "next_payment_date": str(start_date),
                "event_type": "payment_schedule_created"
            }
        )
        
        return schedule

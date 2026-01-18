"""
Сервисный слой для работы с расписаниями/графиками/контрактами.
BE-MVP-003: Рефакторинг orders.py
"""
from typing import Optional, Tuple
from decimal import Decimal
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from models.orders_db import (
    DataSchedule, DataScheduleRoad, DataScheduleOtherParametrs,
    DataScheduleRoadAddress
)
from models.static_data_db import DataCarTariff, DataOtherDriveParametr
from models.users_db import DataUserBalance
from const.cost_formulas import get_total_cost_of_the_trip
from sevice.google_maps_api import get_lat_lon, get_distance_and_duration
from common.logger import logger


class ScheduleService:
    """Сервис для работы с расписаниями"""
    
    MIN_BALANCE_REQUIRED = 100  # Минимальный баланс для создания расписания (руб)
    
    @staticmethod
    async def validate_user_balance(user_id: int) -> Tuple[bool, Optional[JSONResponse]]:
        """
        Проверяет, достаточно ли средств на балансе пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple[bool, Optional[JSONResponse]]: 
                - True, None если баланс достаточен
                - False, JSONResponse с ошибкой если недостаточно
        """
        balance_record = await DataUserBalance.filter(id_user=user_id).first()
        current_balance = balance_record.amount if balance_record else 0
        
        if not balance_record or current_balance < ScheduleService.MIN_BALANCE_REQUIRED:
            logger.warning(
                f"Insufficient balance for user {user_id}",
                extra={
                    "user_id": user_id,
                    "current_balance": float(current_balance),
                    "required_balance": ScheduleService.MIN_BALANCE_REQUIRED
                }
            )
            return False, JSONResponse(
                {
                    "status": False,
                    "message": f"Недостаточно средств на балансе. Минимальный баланс для создания расписания - {ScheduleService.MIN_BALANCE_REQUIRED} руб.",
                    "required_amount": ScheduleService.MIN_BALANCE_REQUIRED,
                    "current_balance": float(current_balance),
                },
                402,
            )
        
        return True, None
    
    @staticmethod
    async def validate_tariff(tariff_id: int) -> bool:
        """
        Проверяет существование и активность тарифа.
        
        Args:
            tariff_id: ID тарифа
            
        Returns:
            bool: True если тариф существует и активен
        """
        return await DataCarTariff.filter(isActive=True, id=tariff_id).count() > 0
    
    @staticmethod
    async def get_tariff_amount(tariff_id: int) -> Optional[int]:
        """
        Получает стоимость тарифа за километр.
        
        Args:
            tariff_id: ID тарифа
            
        Returns:
            Optional[int]: Стоимость в рублях за км или None если тариф не найден
        """
        tariff_dict = await DataCarTariff.filter(id=tariff_id).first().values("amount")
        return tariff_dict["amount"] if tariff_dict else None
    
    @staticmethod
    async def calculate_route_price(addresses: list, tariff_amount: int) -> Tuple[float, list]:
        """
        Рассчитывает стоимость маршрута по адресам.
        
        Args:
            addresses: Список адресов маршрута
            tariff_amount: Стоимость тарифа за км
            
        Returns:
            Tuple[float, list]: Общая стоимость и список адресов с координатами
        """
        total_price = 0.0
        all_addresses = []
        
        for address in addresses:
            # Получаем координаты
            from_lat = address.from_address.location.latitude
            from_lon = address.from_address.location.longitude
            to_lat = address.to_address.location.latitude
            to_lon = address.to_address.location.longitude
            
            # Геокодирование если координаты нулевые
            if from_lon == 0 and from_lat == 0:
                from_lat, from_lon = await get_lat_lon(address.from_address.address)
            if to_lon == 0 and to_lat == 0:
                to_lat, to_lon = await get_lat_lon(address.to_address.address)
            
            # Расчет расстояния и времени
            distance, duration = await get_distance_and_duration(
                from_address={"lat": from_lat, "lng": from_lon},
                to_address={"lat": to_lat, "lng": to_lon},
            )
            
            # Расчет стоимости
            price = get_total_cost_of_the_trip(
                M=tariff_amount, 
                S2=distance, 
                To=duration
            )
            total_price += price
            
            all_addresses.append({
                "from_address": address.from_address.address,
                "to_address": address.to_address.address,
                "from_lat": from_lat,
                "from_lon": from_lon,
                "to_lat": to_lat,
                "to_lon": to_lon,
                "distance": distance,
                "duration": duration,
                "price": price
            })
        
        return total_price, all_addresses
    
    @staticmethod
    async def create_schedule_with_roads(user_id: int, schedule_data: dict, roads_data: list, other_params: list) -> DataSchedule:
        """
        Создает расписание с маршрутами.
        
        Args:
            user_id: ID пользователя
            schedule_data: Данные расписания
            roads_data: Список маршрутов
            other_params: Дополнительные параметры
            
        Returns:
            DataSchedule: Созданное расписание
        """
        # Создаем расписание
        schedule = await DataSchedule.create(
            id_user=user_id,
            **schedule_data
        )
        
        logger.info(
            f"Schedule created: {schedule.id}",
            extra={"user_id": user_id, "schedule_id": schedule.id}
        )
        
        # Добавляем дополнительные параметры
        for params in other_params:
            if await DataOtherDriveParametr.filter(id=params.parametr, isActive=True).count() == 0:
                continue
            await DataScheduleOtherParametrs.create(
                id_schedule=schedule.id,
                id_other_parametr=params.parametr,
                amount=params.count,
            )
        
        return schedule
    
    @staticmethod
    async def update_schedule_fields(schedule_id: int, user_id: int, update_data: dict) -> bool:
        """
        Обновляет поля расписания.
        
        Args:
            schedule_id: ID расписания
            user_id: ID пользователя (для проверки доступа)
            update_data: Словарь с полями для обновления
            
        Returns:
            bool: True если обновление успешно
        """
        schedule = await DataSchedule.filter(id=schedule_id, id_user=user_id).first()
        if not schedule:
            return False
        
        # Фильтруем None значения
        filtered_data = {k: v for k, v in update_data.items() if v is not None}
        
        if filtered_data:
            await DataSchedule.filter(id=schedule_id).update(**filtered_data)
            logger.info(
                f"Schedule updated: {schedule_id}",
                extra={"user_id": user_id, "schedule_id": schedule_id, "fields": list(filtered_data.keys())}
            )
        
        return True
    
    @staticmethod
    async def delete_schedule(schedule_id: int, user_id: int) -> bool:
        """
        Удаляет (деактивирует) расписание.
        
        Args:
            schedule_id: ID расписания
            user_id: ID пользователя (для проверки доступа)
            
        Returns:
            bool: True если удаление успешно
        """
        schedule = await DataSchedule.filter(id=schedule_id, id_user=user_id).first()
        if not schedule:
            return False
        
        await DataSchedule.filter(id=schedule_id).update(isActive=None)
        
        logger.info(
            f"Schedule deleted: {schedule_id}",
            extra={"user_id": user_id, "schedule_id": schedule_id}
        )
        
        return True

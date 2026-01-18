"""
Сервисный слой для работы с заказами и ответами водителей.
BE-MVP-003: Рефакторинг orders.py
"""
from typing import List, Dict, Optional
from datetime import datetime
import pytz

from models.orders_db import (
    DataSchedule, DataScheduleRoad, DataScheduleRoadDriver,
    DataOrder, DataOrderInfo
)
from models.users_db import UsersUser, UsersUserPhoto
from models.drivers_db import UsersDriverData, UsersCar
from models.static_data_db import DataCarMark, DataCarModel, DataColor
from common.logger import logger


class OrderService:
    """Сервис для работы с заказами"""
    
    @staticmethod
    async def get_user_active_orders(user_id: int) -> List[Dict]:
        """
        Получает все активные заказы пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[Dict]: Список активных заказов с деталями
        """
        user = await UsersUser.filter(id=user_id).first()
        if not user:
            return []
        
        # Определяем роль пользователя
        user_account = await user.account.all().values("id_type_account")
        is_driver = any(acc["id_type_account"] == 2 for acc in user_account)
        is_parent = any(acc["id_type_account"] == 1 for acc in user_account)
        
        orders = []
        
        if is_parent:
            # Получаем заказы родителя
            parent_orders = await OrderService._get_parent_orders(user_id)
            orders.extend(parent_orders)
        
        if is_driver:
            # Получаем заказы водителя
            driver_orders = await OrderService._get_driver_orders(user_id)
            orders.extend(driver_orders)
        
        logger.info(
            f"Retrieved {len(orders)} active orders for user {user_id}",
            extra={"user_id": user_id, "orders_count": len(orders)}
        )
        
        return orders
    
    @staticmethod
    async def _get_parent_orders(user_id: int) -> List[Dict]:
        """Получает заказы родителя"""
        schedules = await DataSchedule.filter(
            id_user=user_id,
            isActive=True
        ).all().values()
        
        orders = []
        for schedule in schedules:
            roads = await DataScheduleRoad.filter(
                id_schedule=schedule["id"],
                isActive=True
            ).all().values()
            
            for road in roads:
                # Проверяем наличие водителя
                driver_link = await DataScheduleRoadDriver.filter(
                    id_schedule_road=road["id"],
                    isActive=True
                ).first()
                
                if driver_link:
                    driver_info = await OrderService._get_driver_info(driver_link.id_driver)
                    orders.append({
                        "schedule": schedule,
                        "road": road,
                        "driver": driver_info,
                        "role": "parent"
                    })
        
        return orders
    
    @staticmethod
    async def _get_driver_orders(user_id: int) -> List[Dict]:
        """Получает заказы водителя"""
        driver_roads = await DataScheduleRoadDriver.filter(
            id_driver=user_id,
            isActive=True
        ).all().values()
        
        orders = []
        for driver_road in driver_roads:
            road = await DataScheduleRoad.filter(
                id=driver_road["id_schedule_road"],
                isActive=True
            ).first().values()
            
            if road:
                schedule = await DataSchedule.filter(
                    id=road["id_schedule"],
                    isActive=True
                ).first().values()
                
                if schedule:
                    parent_info = await OrderService._get_parent_info(schedule["id_user"])
                    orders.append({
                        "schedule": schedule,
                        "road": road,
                        "parent": parent_info,
                        "role": "driver"
                    })
        
        return orders
    
    @staticmethod
    async def _get_driver_info(driver_id: int) -> Optional[Dict]:
        """Получает информацию о водителе"""
        driver = await UsersUser.filter(id=driver_id).first()
        if not driver:
            return None
        
        driver_data = await UsersDriverData.filter(id_driver=driver_id).first()
        car = await UsersCar.filter(id_driver=driver_id).first()
        
        photo = await UsersUserPhoto.filter(id_user=driver_id).first()
        photo_path = photo.path if photo else None
        
        car_info = None
        if car:
            mark = await DataCarMark.filter(id=car.id_car_mark).first()
            model = await DataCarModel.filter(id=car.id_car_model).first()
            color = await DataColor.filter(id=car.id_color).first()
            
            car_info = {
                "mark": mark.title if mark else None,
                "model": model.title if model else None,
                "color": color.title if color else None,
                "number": car.number
            }
        
        return {
            "id": driver.id,
            "name": driver.name,
            "surname": driver.surname,
            "patronymic": driver.patronymic,
            "phone": driver.phone,
            "photo": photo_path,
            "rating": driver_data.rating if driver_data else None,
            "car": car_info
        }
    
    @staticmethod
    async def _get_parent_info(parent_id: int) -> Optional[Dict]:
        """Получает информацию о родителе"""
        parent = await UsersUser.filter(id=parent_id).first()
        if not parent:
            return None
        
        photo = await UsersUserPhoto.filter(id_user=parent_id).first()
        photo_path = photo.path if photo else None
        
        return {
            "id": parent.id,
            "name": parent.name,
            "surname": parent.surname,
            "patronymic": parent.patronymic,
            "phone": parent.phone,
            "photo": photo_path
        }
    
    @staticmethod
    async def get_schedule_responses(user_id: int) -> List[Dict]:
        """
        Получает ответы водителей на расписания пользователя.
        
        Args:
            user_id: ID пользователя (родителя)
            
        Returns:
            List[Dict]: Список ответов водителей
        """
        # Получаем все расписания пользователя
        my_schedules = await DataSchedule.filter(
            id_user=user_id,
            isActive__in=[True, False]
        ).all().values("id")
        
        schedule_ids = [s["id"] for s in my_schedules]
        
        if not schedule_ids:
            return []
        
        # Получаем все маршруты этих расписаний
        roads = await DataScheduleRoad.filter(
            id_schedule__in=schedule_ids,
            isActive=True
        ).all().values()
        
        road_ids = [r["id"] for r in roads]
        
        if not road_ids:
            return []
        
        # Получаем ответы водителей
        driver_responses = await DataScheduleRoadDriver.filter(
            id_schedule_road__in=road_ids,
            isActive__in=[True, False, None]
        ).all().values()
        
        # Обогащаем данными
        enriched_responses = []
        for response in driver_responses:
            driver_info = await OrderService._get_driver_info(response["id_driver"])
            road = next((r for r in roads if r["id"] == response["id_schedule_road"]), None)
            
            if driver_info and road:
                enriched_responses.append({
                    "response": response,
                    "driver": driver_info,
                    "road": road
                })
        
        logger.info(
            f"Retrieved {len(enriched_responses)} schedule responses for user {user_id}",
            extra={"user_id": user_id, "responses_count": len(enriched_responses)}
        )
        
        return enriched_responses
    
    @staticmethod
    async def answer_schedule_response(
        user_id: int,
        driver_road_id: int,
        is_accepted: bool
    ) -> bool:
        """
        Отвечает на заявку водителя (принять/отклонить).
        
        Args:
            user_id: ID пользователя (родителя)
            driver_road_id: ID связи водитель-маршрут
            is_accepted: True если принять, False если отклонить
            
        Returns:
            bool: True если операция успешна
        """
        # Проверяем доступ
        driver_road = await DataScheduleRoadDriver.filter(id=driver_road_id).first()
        if not driver_road:
            return False
        
        road = await DataScheduleRoad.filter(id=driver_road.id_schedule_road).first()
        if not road:
            return False
        
        schedule = await DataSchedule.filter(id=road.id_schedule, id_user=user_id).first()
        if not schedule:
            return False
        
        # Обновляем статус
        if is_accepted:
            await DataScheduleRoadDriver.filter(id=driver_road_id).update(isActive=True)
            logger.info(
                f"Driver {driver_road.id_driver} accepted for road {road.id}",
                extra={
                    "user_id": user_id,
                    "driver_id": driver_road.id_driver,
                    "road_id": road.id
                }
            )
        else:
            await DataScheduleRoadDriver.filter(id=driver_road_id).update(isActive=False)
            logger.info(
                f"Driver {driver_road.id_driver} rejected for road {road.id}",
                extra={
                    "user_id": user_id,
                    "driver_id": driver_road.id_driver,
                    "road_id": road.id
                }
            )
        
        return True

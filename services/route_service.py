"""
Сервисный слой для работы с маршрутами расписаний.
BE-MVP-003: Рефакторинг orders.py
"""
from typing import Optional, List, Dict, Tuple
from fastapi.responses import JSONResponse

from models.orders_db import (
    DataSchedule, DataScheduleRoad, DataScheduleRoadAddress,
    DataScheduleRoadChild, DataScheduleRoadContact, DataScheduleRoadDriver
)
from models.static_data_db import DataCarTariff
from const.cost_formulas import get_total_cost_of_the_trip
from sevice.google_maps_api import get_lat_lon, get_distance_and_duration
from common.logger import logger


class RouteService:
    """Сервис для работы с маршрутами расписаний"""
    
    @staticmethod
    async def validate_schedule_access(schedule_id: int, user_id: int) -> bool:
        """
        Проверяет доступ пользователя к расписанию.
        
        Args:
            schedule_id: ID расписания
            user_id: ID пользователя
            
        Returns:
            bool: True если доступ разрешен
        """
        count = await DataSchedule.filter(
            id=schedule_id, 
            id_user=user_id,
            isActive__in=[True, False]
        ).count()
        return count > 0
    
    @staticmethod
    async def create_route(
        schedule_id: int, 
        route_data: dict,
        children_ids: Optional[List[int]] = None,
        contact_data: Optional[Dict] = None
    ) -> DataScheduleRoad:
        """
        Создает новый маршрут для расписания.
        
        Args:
            schedule_id: ID расписания
            route_data: Данные маршрута (week_day, title, start_time, end_time, type_drive)
            children_ids: Список ID детей
            contact_data: Данные контактного лица
            
        Returns:
            DataScheduleRoad: Созданный маршрут
        """
        # Создаем маршрут
        new_road = await DataScheduleRoad.create(
            id_schedule=schedule_id,
            **route_data
        )
        
        logger.info(
            f"Route created: {new_road.id} for schedule {schedule_id}",
            extra={"schedule_id": schedule_id, "route_id": new_road.id}
        )
        
        # Добавляем детей
        if children_ids:
            for child_id in children_ids:
                await DataScheduleRoadChild.create(
                    id_schedule_road=new_road.id,
                    id_child=child_id,
                )
        
        # Добавляем контактное лицо
        if contact_data:
            await DataScheduleRoadContact.create(
                id_schedule_road=new_road.id,
                surname=contact_data.get("surname"),
                name=contact_data.get("name"),
                patronymic=contact_data.get("patronymic"),
                contact_phone=contact_data.get("phone"),
            )
        
        return new_road
    
    @staticmethod
    async def update_route(
        route_id: int,
        update_data: dict,
        children_ids: Optional[List[int]] = None,
        contact_data: Optional[Dict] = None
    ) -> bool:
        """
        Обновляет маршрут.
        
        Args:
            route_id: ID маршрута
            update_data: Данные для обновления
            children_ids: Новый список ID детей (если нужно обновить)
            contact_data: Новые данные контактного лица (если нужно обновить)
            
        Returns:
            bool: True если обновление успешно
        """
        route = await DataScheduleRoad.filter(id=route_id, isActive=True).first()
        if not route:
            return False
        
        # Обновляем основные данные
        filtered_data = {k: v for k, v in update_data.items() if v is not None}
        if filtered_data:
            await DataScheduleRoad.filter(id=route_id).update(**filtered_data)
        
        # Обновляем детей
        if children_ids is not None:
            # Деактивируем старые связи
            await DataScheduleRoadChild.filter(id_schedule_road=route_id).update(isActive=False)
            # Создаем новые
            for child_id in children_ids:
                await DataScheduleRoadChild.create(
                    id_schedule_road=route_id,
                    id_child=child_id,
                )
        
        # Обновляем контакт
        if contact_data is not None:
            # Деактивируем старый контакт
            await DataScheduleRoadContact.filter(id_schedule_road=route_id).update(isActive=False)
            # Создаем новый
            await DataScheduleRoadContact.create(
                id_schedule_road=route_id,
                surname=contact_data.get("surname"),
                name=contact_data.get("name"),
                patronymic=contact_data.get("patronymic"),
                contact_phone=contact_data.get("phone"),
            )
        
        logger.info(
            f"Route updated: {route_id}",
            extra={"route_id": route_id, "fields": list(filtered_data.keys())}
        )
        
        return True
    
    @staticmethod
    async def delete_route(route_id: int) -> bool:
        """
        Удаляет (деактивирует) маршрут и все связанные данные.
        
        Args:
            route_id: ID маршрута
            
        Returns:
            bool: True если удаление успешно
        """
        route = await DataScheduleRoad.filter(id=route_id, isActive=True).first()
        if not route:
            return False
        
        # Деактивируем маршрут
        await DataScheduleRoad.filter(id=route_id).update(isActive=False)
        
        # Деактивируем связанные данные
        await DataScheduleRoadChild.filter(id_schedule_road=route_id).update(isActive=False)
        await DataScheduleRoadContact.filter(id_schedule_road=route_id).update(isActive=False)
        await DataScheduleRoadDriver.filter(id_schedule_road=route_id).update(isActive=False)
        await DataScheduleRoadAddress.filter(id_schedule_road=route_id).update(isActive=False)
        
        logger.info(
            f"Route deleted: {route_id}",
            extra={"route_id": route_id}
        )
        
        return True
    
    @staticmethod
    async def save_route_addresses(
        route_id: int, 
        addresses_data: List[Dict]
    ) -> List[DataScheduleRoadAddress]:
        """
        Сохраняет адреса для маршрута.
        
        Args:
            route_id: ID маршрута
            addresses_data: Список адресов с координатами и ценами
            
        Returns:
            List[DataScheduleRoadAddress]: Список созданных адресов
        """
        created_addresses = []
        
        for addr_data in addresses_data:
            address = await DataScheduleRoadAddress.create(
                id_schedule_road=route_id,
                from_address=addr_data["from_address"],
                to_address=addr_data["to_address"],
                from_lat=addr_data["from_lat"],
                from_lon=addr_data["from_lon"],
                to_lat=addr_data["to_lat"],
                to_lon=addr_data["to_lon"],
                distance=addr_data["distance"],
                duration=addr_data["duration"],
                price=addr_data["price"]
            )
            created_addresses.append(address)
        
        return created_addresses
    
    @staticmethod
    async def calculate_route_total_price(
        addresses: list,
        tariff_amount: int
    ) -> Tuple[float, List[Dict]]:
        """
        Рассчитывает общую стоимость маршрута по адресам.
        
        Args:
            addresses: Список адресов с координатами
            tariff_amount: Стоимость тарифа за км
            
        Returns:
            Tuple[float, List[Dict]]: Общая стоимость и список адресов с расчетами
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
    async def get_route_with_details(route_id: int) -> Optional[Dict]:
        """
        Получает маршрут со всеми деталями (дети, контакты, адреса).
        
        Args:
            route_id: ID маршрута
            
        Returns:
            Optional[Dict]: Данные маршрута или None если не найден
        """
        route = await DataScheduleRoad.filter(id=route_id, isActive=True).first().values()
        if not route:
            return None
        
        # Получаем детей
        children_records = await DataScheduleRoadChild.filter(
            id_schedule_road=route_id,
            isActive=True
        ).all().values("id_child")
        route["children"] = [rec["id_child"] for rec in children_records]
        
        # Получаем контакт
        contact_exists = await DataScheduleRoadContact.filter(
            id_schedule_road=route_id,
            isActive=True
        ).count() > 0
        
        if contact_exists:
            contact = await DataScheduleRoadContact.filter(
                id_schedule_road=route_id,
                isActive=True
            ).first().values("surname", "name", "patronymic", "contact_phone")
            route["contact"] = {
                "surname": contact["surname"],
                "name": contact["name"],
                "patronymic": contact["patronymic"],
                "phone": contact["contact_phone"]
            }
        else:
            route["contact"] = None
        
        # Получаем адреса
        addresses = await DataScheduleRoadAddress.filter(
            id_schedule_road=route_id,
            isActive=True
        ).all().values()
        route["addresses"] = addresses
        
        return route

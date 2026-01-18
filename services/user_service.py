"""
Сервисный слой для работы с пользователями и их профилями.
BE-MVP-004: Рефакторинг users.py
"""
from typing import Optional, Dict, List
from datetime import datetime

from models.users_db import (
    UsersUser, UsersUserPhoto, UsersChild,
    DataUserBalance
)
from models.authentication_db import UsersUserAccount
from models.drivers_db import UsersDriverData, UsersCar
from models.static_data_db import DataCarMark, DataCarModel, DataColor
from common.logger import logger


class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    async def get_user_profile(user_id: int) -> Optional[Dict]:
        """
        Получает профиль пользователя со всеми данными.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[Dict]: Данные пользователя или None
        """
        user = await UsersUser.filter(id=user_id).first()
        if not user:
            return None
        
        # Получаем типы аккаунта
        accounts = await UsersUserAccount.filter(id_user=user_id).all().values()
        account_types = [acc["id_type_account"] for acc in accounts]
        
        # Получаем фото
        photo = await UsersUserPhoto.filter(id_user=user_id).first()
        photo_path = photo.path if photo else None
        
        # Получаем баланс
        balance = await DataUserBalance.filter(id_user=user_id).first()
        balance_amount = float(balance.amount) if balance else 0.0
        
        profile = {
            "id": user.id,
            "name": user.name,
            "surname": user.surname,
            "patronymic": user.patronymic,
            "phone": user.phone,
            "email": user.email,
            "birthday": user.birthday.isoformat() if user.birthday else None,
            "account_types": account_types,
            "photo": photo_path,
            "balance": balance_amount
        }
        
        # Если водитель - добавляем данные водителя
        if 2 in account_types:
            driver_data = await UserService._get_driver_data(user_id)
            profile["driver"] = driver_data
        
        # Если родитель - добавляем детей
        if 1 in account_types:
            children = await UserService.get_user_children(user_id)
            profile["children"] = children
        
        return profile
    
    @staticmethod
    async def _get_driver_data(driver_id: int) -> Optional[Dict]:
        """Получает данные водителя"""
        driver_data = await UsersDriverData.filter(id_driver=driver_id).first()
        if not driver_data:
            return None
        
        car = await UsersCar.filter(id_driver=driver_id).first()
        car_info = None
        
        if car:
            mark = await DataCarMark.filter(id=car.id_car_mark).first()
            model = await DataCarModel.filter(id=car.id_car_model).first()
            color = await DataColor.filter(id=car.id_color).first()
            
            car_info = {
                "mark": mark.title if mark else None,
                "model": model.title if model else None,
                "color": color.title if color else None,
                "number": car.number,
                "year": car.year
            }
        
        return {
            "rating": driver_data.rating,
            "experience_years": driver_data.experience_years,
            "car": car_info
        }
    
    @staticmethod
    async def update_user_profile(user_id: int, update_data: Dict) -> bool:
        """
        Обновляет профиль пользователя.
        
        Args:
            user_id: ID пользователя
            update_data: Данные для обновления
            
        Returns:
            bool: True если обновление успешно
        """
        user = await UsersUser.filter(id=user_id).first()
        if not user:
            return False
        
        # Фильтруем None значения
        filtered_data = {k: v for k, v in update_data.items() if v is not None}
        
        if filtered_data:
            await UsersUser.filter(id=user_id).update(**filtered_data)
            
            logger.info(
                f"User profile updated",
                extra={
                    "user_id": user_id,
                    "fields": list(filtered_data.keys())
                }
            )
        
        return True
    
    @staticmethod
    async def get_user_children(user_id: int) -> List[Dict]:
        """
        Получает список детей пользователя.
        BE-MVP-016: Расширенный профиль ребенка
        
        Args:
            user_id: ID пользователя (родителя)
            
        Returns:
            List[Dict]: Список детей с полной информацией
        """
        children = await UsersChild.filter(
            id_user=user_id,
            isActive=True
        ).all().values()
        
        return [
            {
                "id": child["id"],
                "name": child["name"],
                "surname": child["surname"],
                "patronymic": child["patronymic"],
                "age": child.get("age"),
                "birthday": child["birthday"].isoformat() if child.get("birthday") else None,
                "gender": child.get("gender"),
                "photo_path": child.get("photo_path"),
                "school_class": child.get("school_class"),
                "character_notes": child.get("character_notes"),
                "child_phone": child.get("child_phone"),
                "id_user": child["id_user"],
                "isActive": child.get("isActive", True),
                "datetime_create": child.get("datetime_create").isoformat() if child.get("datetime_create") else None
            }
            for child in children
        ]
    
    @staticmethod
    async def add_child(user_id: int, child_data: Dict) -> Optional[int]:
        """
        Добавляет ребенка к профилю пользователя.
        
        Args:
            user_id: ID пользователя (родителя)
            child_data: Данные ребенка
            
        Returns:
            Optional[int]: ID созданного ребенка или None
        """
        # Проверяем, что пользователь - родитель
        accounts = await UsersUserAccount.filter(id_user=user_id).all().values()
        account_types = [acc["id_type_account"] for acc in accounts]
        
        if 1 not in account_types:  # 1 = родитель
            logger.warning(
                f"User {user_id} tried to add child but is not a parent",
                extra={"user_id": user_id}
            )
            return None
        
        # Создаем ребенка
        child = await UsersChild.create(
            id_user=user_id,
            **child_data
        )
        
        logger.info(
            f"Child added to user profile",
            extra={
                "user_id": user_id,
                "child_id": child.id,
                "child_name": child_data.get("name")
            }
        )
        
        return child.id
    
    @staticmethod
    async def update_child(user_id: int, child_id: int, update_data: Dict) -> bool:
        """
        Обновляет данные ребенка.
        
        Args:
            user_id: ID пользователя (родителя)
            child_id: ID ребенка
            update_data: Данные для обновления
            
        Returns:
            bool: True если обновление успешно
        """
        # Проверяем доступ
        child = await UsersChild.filter(
            id=child_id,
            id_user=user_id,
            isActive=True
        ).first()
        
        if not child:
            logger.warning(
                f"Child not found or access denied",
                extra={"user_id": user_id, "child_id": child_id}
            )
            return False
        
        # Обновляем только переданные поля
        filtered_data = {k: v for k, v in update_data.items() if v is not None}
        
        if filtered_data:
            await UsersChild.filter(id=child_id).update(**filtered_data)
            
            logger.info(
                f"Child profile updated",
                extra={
                    "user_id": user_id,
                    "child_id": child_id,
                    "fields": list(filtered_data.keys())
                }
            )
        
        return True
    
    @staticmethod
    async def delete_child(user_id: int, child_id: int) -> bool:
        """
        Удаляет (деактивирует) ребенка.
        
        Args:
            user_id: ID пользователя (родителя)
            child_id: ID ребенка
            
        Returns:
            bool: True если удаление успешно
        """
        # Проверяем доступ
        child = await UsersChild.filter(
            id=child_id,
            id_user=user_id,
            isActive=True
        ).first()
        
        if not child:
            logger.warning(
                f"Child not found or access denied",
                extra={"user_id": user_id, "child_id": child_id}
            )
            return False
        
        # Деактивируем
        await UsersChild.filter(id=child_id).update(isActive=False)
        
        logger.info(
            f"Child deleted",
            extra={"user_id": user_id, "child_id": child_id}
        )
        
        return True
    
    @staticmethod
    async def check_user_role(user_id: int, role_id: int) -> bool:
        """
        Проверяет, имеет ли пользователь определенную роль.
        
        Args:
            user_id: ID пользователя
            role_id: ID роли (1=родитель, 2=водитель, 6=франшиза и т.д.)
            
        Returns:
            bool: True если роль есть
        """
        count = await UsersUserAccount.filter(
            id_user=user_id,
            id_type_account=role_id
        ).count()
        
        return count > 0
    
    @staticmethod
    async def get_extended_user_info(user_id: int) -> Optional[Dict]:
        """
        Получает расширенную информацию о пользователе.
        Включает профиль, детей, баланс, историю и т.д.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[Dict]: Расширенная информация
        """
        # Базовый профиль
        profile = await UserService.get_user_profile(user_id)
        if not profile:
            return None
        
        # Дополнительная информация
        is_parent = await UserService.check_user_role(user_id, 1)
        is_driver = await UserService.check_user_role(user_id, 2)
        
        extended_info = {
            **profile,
            "roles": {
                "is_parent": is_parent,
                "is_driver": is_driver
            }
        }
        
        return extended_info

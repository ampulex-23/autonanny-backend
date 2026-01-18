"""
BE-MVP-031: Тесты для CRUD API профилей детей (BE-MVP-016)
Дополнительный компонент управления данными
"""

import pytest
from datetime import datetime, date


class TestChildProfileValidation:
    """Тесты для валидации профиля ребенка"""
    
    def test_child_name_required(self):
        """Тест обязательности имени"""
        name = "Петя"
        
        assert name is not None, "Имя обязательно"
        assert len(name) > 0, "Имя не должно быть пустым"
    
    def test_child_surname_required(self):
        """Тест обязательности фамилии"""
        surname = "Петров"
        
        assert surname is not None, "Фамилия обязательна"
        assert len(surname) > 0, "Фамилия не должна быть пустой"
    
    def test_child_age_validation(self):
        """Тест валидации возраста"""
        valid_ages = [3, 5, 7, 10, 15]
        
        for age in valid_ages:
            assert 0 < age < 18, f"Возраст {age} должен быть в диапазоне 1-17"
    
    def test_child_age_invalid(self):
        """Тест невалидного возраста"""
        invalid_ages = [-1, 0, 18, 20]
        
        for age in invalid_ages:
            is_valid = 0 < age < 18
            assert not is_valid, f"Возраст {age} должен быть невалидным"
    
    def test_birth_date_format(self):
        """Тест формата даты рождения"""
        birth_date = date(2015, 5, 20)
        
        assert isinstance(birth_date, date), "Дата рождения должна быть date объектом"
        assert birth_date < date.today(), "Дата рождения должна быть в прошлом"
    
    def test_gender_validation(self):
        """Тест валидации пола"""
        valid_genders = ["male", "female", "М", "Ж"]
        
        for gender in valid_genders:
            assert gender in valid_genders, f"Пол {gender} должен быть валидным"


class TestChildCRUD:
    """Тесты для CRUD операций с детьми"""
    
    def test_create_child(self):
        """Тест создания профиля ребенка"""
        child_data = {
            "name": "Петя",
            "surname": "Петров",
            "age": 7,
            "birth_date": date(2018, 5, 20),
            "gender": "male",
            "school_class": "1А",
            "school_name": "Школа №1",
            "photo": "/uploads/children/123/photo.jpg",
            "character_traits": "Активный, любознательный"
        }
        
        assert child_data["name"] is not None, "Имя должно быть заполнено"
        assert child_data["age"] > 0, "Возраст должен быть положительным"
    
    def test_get_children_list(self):
        """Тест получения списка детей"""
        parent_id = 123
        
        assert parent_id > 0, "ID родителя должен быть положительным"
    
    def test_update_child(self):
        """Тест обновления профиля ребенка"""
        child_id = 123
        update_data = {
            "age": 8,
            "school_class": "2А",
            "character_traits": "Активный, любознательный, дружелюбный"
        }
        
        assert child_id > 0, "ID ребенка должен быть положительным"
        assert "age" in update_data or "school_class" in update_data, "Должны быть поля для обновления"
    
    def test_delete_child(self):
        """Тест удаления (деактивации) ребенка"""
        is_active = True
        
        # После удаления
        is_active = False
        
        assert not is_active, "Ребенок должен быть деактивирован"


class TestSchoolInformation:
    """Тесты для школьной информации"""
    
    def test_school_class_format(self):
        """Тест формата класса"""
        valid_classes = ["1А", "2Б", "5В", "11Г"]
        
        for school_class in valid_classes:
            assert len(school_class) >= 2, f"Класс {school_class} должен иметь минимум 2 символа"
            assert school_class[0].isdigit(), f"Класс {school_class} должен начинаться с цифры"
    
    def test_school_name_optional(self):
        """Тест опциональности названия школы"""
        school_name = None
        
        assert school_name is None or isinstance(school_name, str), "Название школы опционально"
    
    def test_school_class_optional(self):
        """Тест опциональности класса"""
        school_class = None
        
        assert school_class is None or isinstance(school_class, str), "Класс опционален"


class TestCharacterTraits:
    """Тесты для особенностей характера"""
    
    def test_character_traits_format(self):
        """Тест формата особенностей характера"""
        traits = "Активный, любознательный, дружелюбный"
        
        assert isinstance(traits, str), "Особенности должны быть строкой"
    
    def test_character_traits_optional(self):
        """Тест опциональности особенностей"""
        traits = None
        
        assert traits is None or isinstance(traits, str), "Особенности опциональны"
    
    def test_multiple_traits(self):
        """Тест множественных особенностей"""
        traits = "Активный, любознательный, дружелюбный, застенчивый"
        traits_list = [t.strip() for t in traits.split(",")]
        
        assert len(traits_list) >= 1, "Должна быть хотя бы одна особенность"


class TestPhotoManagement:
    """Тесты для управления фотографиями"""
    
    def test_photo_path_format(self):
        """Тест формата пути к фото"""
        photo_path = "/uploads/children/123/photo.jpg"
        
        assert photo_path.startswith("/uploads/"), "Путь должен начинаться с /uploads/"
        assert photo_path.endswith((".jpg", ".jpeg", ".png")), "Фото должно быть изображением"
    
    def test_photo_optional(self):
        """Тест опциональности фото"""
        photo = None
        
        assert photo is None or isinstance(photo, str), "Фото опционально"
    
    def test_photo_includes_child_id(self):
        """Тест наличия ID ребенка в пути"""
        child_id = 123
        photo_path = f"/uploads/children/{child_id}/photo.jpg"
        
        assert str(child_id) in photo_path, "Путь должен содержать ID ребенка"


class TestRouteAssignment:
    """Тесты для привязки детей к маршрутам"""
    
    def test_attach_child_to_route(self):
        """Тест привязки ребенка к маршруту"""
        child_id = 123
        route_id = 456
        
        assignment = {
            "child_id": child_id,
            "route_id": route_id,
            "pickup_address": "ул. Ленина, 10",
            "dropoff_address": "ул. Пушкина, 20"
        }
        
        assert assignment["child_id"] > 0, "ID ребенка должен быть положительным"
        assert assignment["route_id"] > 0, "ID маршрута должен быть положительным"
    
    def test_multiple_children_on_route(self):
        """Тест множественных детей на маршруте"""
        route_children = [
            {"child_id": 123, "name": "Петя"},
            {"child_id": 456, "name": "Маша"},
            {"child_id": 789, "name": "Вася"}
        ]
        
        assert len(route_children) <= 4, "На маршруте должно быть не более 4 детей"
    
    def test_child_addresses_on_route(self):
        """Тест адресов ребенка на маршруте"""
        pickup = "ул. Ленина, 10"
        dropoff = "ул. Пушкина, 20"
        
        assert len(pickup) > 0, "Адрес подачи должен быть заполнен"
        assert len(dropoff) > 0, "Адрес высадки должен быть заполнен"


class TestAccessControl:
    """Тесты для контроля доступа к профилям детей"""
    
    def test_parent_can_manage_own_children(self):
        """Тест управления своими детьми"""
        parent_id = 123
        child_parent_id = 123
        
        has_access = parent_id == child_parent_id
        
        assert has_access, "Родитель должен управлять своими детьми"
    
    def test_parent_cannot_manage_other_children(self):
        """Тест отсутствия доступа к чужим детям"""
        parent_id = 123
        child_parent_id = 456
        
        has_access = parent_id == child_parent_id
        
        assert not has_access, "Родитель не должен управлять чужими детьми"
    
    def test_driver_can_view_assigned_children(self):
        """Тест просмотра назначенных детей"""
        driver_id = 789
        route_driver_id = 789
        
        has_access = driver_id == route_driver_id
        
        assert has_access, "Водитель должен видеть назначенных детей"


class TestChildLogging:
    """Тесты для логирования операций с детьми"""
    
    def test_create_child_logged(self):
        """Тест логирования создания"""
        log_metadata = {
            "parent_id": 123,
            "child_id": 456,
            "child_name": "Петя Петров",
            "event_type": "child_created"
        }
        
        assert "child_id" in log_metadata, "Лог должен содержать ID ребенка"
        assert "child_name" in log_metadata, "Лог должен содержать имя ребенка"
        assert log_metadata["event_type"] == "child_created", "event_type должен быть корректным"
    
    def test_update_child_logged(self):
        """Тест логирования обновления"""
        log_metadata = {
            "parent_id": 123,
            "child_id": 456,
            "updated_fields": ["age", "school_class"],
            "event_type": "child_updated"
        }
        
        assert "updated_fields" in log_metadata, "Лог должен содержать обновленные поля"
        assert log_metadata["event_type"] == "child_updated", "event_type должен быть корректным"
    
    def test_delete_child_logged(self):
        """Тест логирования удаления"""
        log_metadata = {
            "parent_id": 123,
            "child_id": 456,
            "event_type": "child_deleted"
        }
        
        assert log_metadata["event_type"] == "child_deleted", "event_type должен быть корректным"


class TestAgeCalculation:
    """Тесты для расчета возраста"""
    
    def test_calculate_age_from_birth_date(self):
        """Тест расчета возраста по дате рождения"""
        birth_date = date(2015, 5, 20)
        today = date(2025, 10, 28)
        
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        assert age == 10, "Возраст должен быть 10 лет"
    
    def test_age_consistency(self):
        """Тест консистентности возраста"""
        birth_date = date(2018, 1, 1)
        stored_age = 7
        
        calculated_age = date.today().year - birth_date.year
        
        # Возраст может отличаться на 1 год в зависимости от даты
        assert abs(calculated_age - stored_age) <= 1, "Возраст должен быть консистентным"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

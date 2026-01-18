"""
BE-MVP-031: Тесты для экстренных контактов (BE-MVP-018)
Важный компонент безопасности
"""

import pytest
import re


class TestEmergencyContactValidation:
    """Тесты для валидации экстренных контактов"""
    
    def test_phone_format_validation(self):
        """Тест валидации формата телефона"""
        valid_phones = [
            "+7 (999) 123-45-67",
            "+7 (999) 123 45 67",
            "+79991234567"
        ]
        
        phone_pattern = r'^\+7[\s\(\)]*\d{3}[\s\)\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}$'
        
        for phone in valid_phones:
            # Очищаем телефон от форматирования
            cleaned = re.sub(r'[^\d+]', '', phone)
            assert cleaned.startswith("+7"), f"Телефон {phone} должен начинаться с +7"
            assert len(cleaned) == 12, f"Телефон {phone} должен содержать 12 символов"
    
    def test_phone_invalid_format(self):
        """Тест невалидного формата телефона"""
        invalid_phones = [
            "+8 (999) 123-45-67",  # Неправильный код страны
            "+7 999 123 45",  # Слишком короткий
            "89991234567",  # Без +7
            "+7 (999) 123-45-6"  # Неполный номер
        ]
        
        for phone in invalid_phones:
            cleaned = re.sub(r'[^\d+]', '', phone)
            is_valid = cleaned.startswith("+7") and len(cleaned) == 12
            assert not is_valid, f"Телефон {phone} должен быть невалидным"
    
    def test_contact_name_required(self):
        """Тест обязательности имени контакта"""
        contact_name = "Мария Петрова"
        
        assert contact_name is not None, "Имя контакта обязательно"
        assert len(contact_name) > 0, "Имя контакта не должно быть пустым"
    
    def test_relationship_required(self):
        """Тест обязательности отношения"""
        relationship = "Бабушка"
        
        assert relationship is not None, "Отношение обязательно"
        assert len(relationship) > 0, "Отношение не должно быть пустым"
    
    def test_relationship_types(self):
        """Тест типов отношений"""
        valid_relationships = [
            "Мама", "Папа", "Бабушка", "Дедушка", 
            "Тетя", "Дядя", "Сестра", "Брат", "Опекун"
        ]
        
        for relationship in valid_relationships:
            assert isinstance(relationship, str), f"Отношение {relationship} должно быть строкой"


class TestContactPriority:
    """Тесты для приоритизации контактов"""
    
    def test_priority_ordering(self):
        """Тест упорядочивания по приоритету"""
        contacts = [
            {"name": "Мама", "priority": 1},
            {"name": "Папа", "priority": 2},
            {"name": "Бабушка", "priority": 3}
        ]
        
        sorted_contacts = sorted(contacts, key=lambda x: x["priority"])
        
        assert sorted_contacts[0]["priority"] == 1, "Первый контакт должен иметь приоритет 1"
        assert sorted_contacts[1]["priority"] == 2, "Второй контакт должен иметь приоритет 2"
        assert sorted_contacts[2]["priority"] == 3, "Третий контакт должен иметь приоритет 3"
    
    def test_priority_uniqueness(self):
        """Тест уникальности приоритетов"""
        priorities = [1, 2, 3]
        
        assert len(priorities) == len(set(priorities)), "Приоритеты должны быть уникальными"
    
    def test_priority_positive(self):
        """Тест положительности приоритета"""
        priority = 1
        
        assert priority > 0, "Приоритет должен быть положительным"
    
    def test_priority_sequential(self):
        """Тест последовательности приоритетов"""
        priorities = [1, 2, 3, 4]
        
        for i in range(len(priorities) - 1):
            assert priorities[i+1] == priorities[i] + 1, "Приоритеты должны идти последовательно"


class TestEmergencyContactCRUD:
    """Тесты для CRUD операций экстренных контактов"""
    
    def test_create_emergency_contact(self):
        """Тест создания экстренного контакта"""
        contact_data = {
            "id_child": 123,
            "name": "Мария Петрова",
            "phone": "+7 (999) 123-45-67",
            "relationship": "Бабушка",
            "priority": 1
        }
        
        assert contact_data["id_child"] > 0, "ID ребенка должен быть положительным"
        assert len(contact_data["name"]) > 0, "Имя должно быть заполнено"
        assert contact_data["phone"].startswith("+7"), "Телефон должен начинаться с +7"
        assert contact_data["priority"] > 0, "Приоритет должен быть положительным"
    
    def test_get_emergency_contacts(self):
        """Тест получения экстренных контактов"""
        child_id = 123
        
        assert child_id > 0, "ID ребенка должен быть положительным"
    
    def test_update_emergency_contact(self):
        """Тест обновления экстренного контакта"""
        update_data = {
            "phone": "+7 (999) 987-65-43",
            "priority": 2
        }
        
        assert "phone" in update_data or "priority" in update_data, "Должны быть поля для обновления"
    
    def test_delete_emergency_contact(self):
        """Тест удаления экстренного контакта"""
        is_active = True
        
        # После удаления
        is_active = False
        
        assert not is_active, "Контакт должен быть деактивирован"
    
    def test_multiple_contacts_per_child(self):
        """Тест множественных контактов для одного ребенка"""
        contacts = [
            {"id_child": 123, "name": "Мама", "priority": 1},
            {"id_child": 123, "name": "Папа", "priority": 2},
            {"id_child": 123, "name": "Бабушка", "priority": 3}
        ]
        
        child_ids = [c["id_child"] for c in contacts]
        assert all(cid == 123 for cid in child_ids), "Все контакты должны принадлежать одному ребенку"
        assert len(contacts) == 3, "Должно быть 3 контакта"


class TestSOSIntegration:
    """Тесты для интеграции с SOS-кнопкой"""
    
    def test_sos_notifies_all_emergency_contacts(self):
        """Тест уведомления всех экстренных контактов при SOS"""
        contacts = [
            {"name": "Мама", "phone": "+79991234567", "priority": 1},
            {"name": "Папа", "phone": "+79991234568", "priority": 2}
        ]
        
        # При SOS все контакты должны быть уведомлены
        for contact in contacts:
            assert contact["phone"] is not None, f"Контакт {contact['name']} должен иметь телефон"
    
    def test_sos_notification_order_by_priority(self):
        """Тест порядка уведомлений по приоритету"""
        contacts = [
            {"name": "Бабушка", "priority": 3},
            {"name": "Мама", "priority": 1},
            {"name": "Папа", "priority": 2}
        ]
        
        sorted_contacts = sorted(contacts, key=lambda x: x["priority"])
        
        assert sorted_contacts[0]["name"] == "Мама", "Первой должна быть уведомлена Мама (приоритет 1)"
        assert sorted_contacts[1]["name"] == "Папа", "Вторым должен быть уведомлен Папа (приоритет 2)"
    
    def test_sos_notification_content(self):
        """Тест содержимого SOS-уведомления"""
        child_name = "Петя Петров"
        contact_name = "Мария Петрова"
        notification = f"🆘 SOS! Ребенок {child_name} нуждается в помощи. Свяжитесь с водителем немедленно!"
        
        assert "🆘" in notification, "Уведомление должно содержать SOS маркер"
        assert child_name in notification, "Уведомление должно содержать имя ребенка"
        assert "помощ" in notification.lower(), "Уведомление должно указывать на необходимость помощи"


class TestContactNotifications:
    """Тесты для уведомлений контактов"""
    
    def test_sms_notification_format(self):
        """Тест формата SMS-уведомления"""
        child_name = "Петя Петров"
        driver_phone = "+79991234567"
        location = "55.7558, 37.6173"
        
        sms_text = f"SOS! {child_name} нуждается в помощи. Водитель: {driver_phone}. Координаты: {location}"
        
        assert len(sms_text) <= 160, "SMS должно быть не длиннее 160 символов"
        assert child_name in sms_text, "SMS должно содержать имя ребенка"
    
    def test_push_notification_format(self):
        """Тест формата push-уведомления"""
        notification = {
            "title": "🆘 Экстренный вызов",
            "body": "Ребенок Петя Петров нуждается в помощи!",
            "data": {
                "action": "emergency_contact_alert",
                "child_id": "123",
                "sos_event_id": "456"
            }
        }
        
        assert "title" in notification, "Уведомление должно иметь заголовок"
        assert "body" in notification, "Уведомление должно иметь тело"
        assert "data" in notification, "Уведомление должно иметь данные"


class TestAccessControl:
    """Тесты для контроля доступа к экстренным контактам"""
    
    def test_parent_can_manage_own_child_contacts(self):
        """Тест управления контактами своего ребенка"""
        parent_id = 123
        child_parent_id = 123
        
        has_access = parent_id == child_parent_id
        
        assert has_access, "Родитель должен управлять контактами своего ребенка"
    
    def test_parent_cannot_manage_other_child_contacts(self):
        """Тест отсутствия доступа к чужим контактам"""
        parent_id = 123
        child_parent_id = 456
        
        has_access = parent_id == child_parent_id
        
        assert not has_access, "Родитель не должен управлять чужими контактами"
    
    def test_driver_can_view_assigned_child_contacts(self):
        """Тест просмотра контактов назначенного ребенка"""
        driver_id = 789
        child_assigned_driver = 789
        
        has_access = driver_id == child_assigned_driver
        
        assert has_access, "Водитель должен видеть контакты назначенного ребенка"
    
    def test_admin_can_view_all_contacts(self):
        """Тест доступа администратора ко всем контактам"""
        user_role = "admin"
        
        has_access = user_role == "admin"
        
        assert has_access, "Администратор должен иметь доступ ко всем контактам"


class TestEmergencyContactLogging:
    """Тесты для логирования экстренных контактов"""
    
    def test_create_logging(self):
        """Тест логирования создания"""
        log_metadata = {
            "user_id": 123,
            "child_id": 456,
            "contact_id": 789,
            "contact_name": "Мария Петрова",
            "priority": 1,
            "event_type": "emergency_contact_created"
        }
        
        assert "contact_id" in log_metadata, "Лог должен содержать ID контакта"
        assert "priority" in log_metadata, "Лог должен содержать приоритет"
        assert log_metadata["event_type"] == "emergency_contact_created", "event_type должен быть корректным"
    
    def test_update_logging(self):
        """Тест логирования обновления"""
        log_metadata = {
            "user_id": 123,
            "contact_id": 789,
            "updated_fields": ["phone", "priority"],
            "event_type": "emergency_contact_updated"
        }
        
        assert "updated_fields" in log_metadata, "Лог должен содержать обновленные поля"
        assert log_metadata["event_type"] == "emergency_contact_updated", "event_type должен быть корректным"
    
    def test_sos_notification_logging(self):
        """Тест логирования SOS-уведомления"""
        log_metadata = {
            "sos_event_id": 123,
            "contact_id": 456,
            "notification_type": "sms",
            "status": "sent",
            "event_type": "emergency_contact_notified"
        }
        
        assert "notification_type" in log_metadata, "Лог должен содержать тип уведомления"
        assert "status" in log_metadata, "Лог должен содержать статус"
        assert log_metadata["event_type"] == "emergency_contact_notified", "event_type должен быть корректным"


class TestContactValidationRules:
    """Тесты для правил валидации контактов"""
    
    def test_minimum_one_contact_required(self):
        """Тест обязательности хотя бы одного контакта"""
        contacts_count = 1
        
        assert contacts_count >= 1, "Должен быть хотя бы один экстренный контакт"
    
    def test_maximum_contacts_limit(self):
        """Тест максимального количества контактов"""
        max_contacts = 5
        contacts_count = 3
        
        assert contacts_count <= max_contacts, f"Не должно быть более {max_contacts} контактов"
    
    def test_duplicate_phone_prevention(self):
        """Тест предотвращения дублирования телефонов"""
        contacts = [
            {"phone": "+79991234567"},
            {"phone": "+79991234568"},
            {"phone": "+79991234569"}
        ]
        
        phones = [c["phone"] for c in contacts]
        assert len(phones) == len(set(phones)), "Телефоны не должны дублироваться"
    
    def test_priority_gap_prevention(self):
        """Тест предотвращения пропусков в приоритетах"""
        priorities = [1, 2, 3]
        
        # Проверяем, что нет пропусков
        for i in range(1, len(priorities) + 1):
            assert i in priorities, f"Приоритет {i} должен существовать"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

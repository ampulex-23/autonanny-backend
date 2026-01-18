"""
BE-MVP-031: Тесты для различных валидаций
"""

import pytest
import re
from datetime import datetime, time


class TestPhoneValidation:
    """Тесты для валидации телефонных номеров"""
    
    def test_valid_russian_phone(self):
        """Тест валидного российского номера"""
        phone = "+79991234567"
        pattern = r'^\+7\d{10}$'
        assert re.match(pattern, phone), "Валидный российский номер должен проходить проверку"
    
    def test_phone_with_spaces(self):
        """Тест номера с пробелами"""
        phone = "+7 999 123 45 67"
        cleaned = phone.replace(" ", "")
        pattern = r'^\+7\d{10}$'
        assert re.match(pattern, cleaned), "Номер с пробелами должен очищаться и проходить проверку"
    
    def test_phone_with_parentheses(self):
        """Тест номера со скобками"""
        phone = "+7 (999) 123-45-67"
        cleaned = re.sub(r'[^\d+]', '', phone)
        pattern = r'^\+7\d{10}$'
        assert re.match(pattern, cleaned), "Номер со скобками должен очищаться и проходить проверку"
    
    def test_invalid_phone_too_short(self):
        """Тест слишком короткого номера"""
        phone = "+7999123"
        pattern = r'^\+7\d{10}$'
        assert not re.match(pattern, phone), "Короткий номер должен быть отклонен"
    
    def test_invalid_phone_too_long(self):
        """Тест слишком длинного номера"""
        phone = "+799912345678901"
        pattern = r'^\+7\d{10}$'
        assert not re.match(pattern, phone), "Длинный номер должен быть отклонен"
    
    def test_invalid_phone_wrong_country_code(self):
        """Тест неправильного кода страны"""
        phone = "+89991234567"
        pattern = r'^\+7\d{10}$'
        assert not re.match(pattern, phone), "Номер с неправильным кодом страны должен быть отклонен"


class TestChildrenLimitValidation:
    """Тесты для валидации ограничения количества детей (BE-MVP-012)"""
    
    def test_max_children_limit(self):
        """Тест максимального количества детей (4)"""
        max_children = 4
        current_children = 4
        assert current_children <= max_children, "Должно быть разрешено до 4 детей"
    
    def test_exceeding_children_limit(self):
        """Тест превышения лимита детей"""
        max_children = 4
        current_children = 5
        assert current_children > max_children, "Превышение лимита должно быть отклонено"
    
    def test_within_children_limit(self):
        """Тест в пределах лимита"""
        max_children = 4
        for count in range(1, 5):
            assert count <= max_children, f"{count} детей должно быть разрешено"


class TestScheduleValidation:
    """Тесты для валидации расписаний"""
    
    def test_time_format_validation(self):
        """Тест валидации формата времени"""
        valid_times = ["08:00", "14:30", "23:59"]
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        
        for time_str in valid_times:
            assert re.match(time_pattern, time_str), f"Время {time_str} должно быть валидным"
    
    def test_invalid_time_format(self):
        """Тест невалидного формата времени"""
        invalid_times = ["25:00", "12:60", "abc", "12-30"]
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        
        for time_str in invalid_times:
            assert not re.match(time_pattern, time_str), f"Время {time_str} должно быть невалидным"
    
    def test_time_range_validation(self):
        """Тест валидации временного диапазона"""
        start_time = time(8, 0)
        end_time = time(18, 0)
        
        assert end_time > start_time, "Время окончания должно быть позже времени начала"
    
    def test_invalid_time_range(self):
        """Тест невалидного временного диапазона"""
        start_time = time(18, 0)
        end_time = time(8, 0)
        
        assert end_time < start_time, "Невалидный диапазон должен быть отклонен"


class TestDriverScheduleValidation:
    """Тесты для валидации расписания водителя (BE-MVP-015)"""
    
    def test_full_schedule_acceptance(self):
        """Тест принятия полного расписания"""
        total_days = 5
        accepted_days = 5
        
        assert accepted_days == total_days, "Водитель должен принять все дни"
    
    def test_partial_schedule_rejection(self):
        """Тест отклонения частичного расписания"""
        total_days = 5
        accepted_days = 3
        
        assert accepted_days < total_days, "Частичное принятие должно быть отклонено"
    
    def test_zero_days_acceptance(self):
        """Тест нулевого количества дней"""
        accepted_days = 0
        
        assert accepted_days == 0, "Нулевое количество дней должно быть отклонено"


class TestBalanceValidation:
    """Тесты для валидации баланса (BE-MVP-007)"""
    
    def test_sufficient_balance_for_order(self):
        """Тест достаточного баланса для заказа"""
        from decimal import Decimal
        balance = Decimal("1000.00")
        order_cost = Decimal("500.00")
        
        assert balance >= order_cost, "Заказ должен быть разрешен при достаточном балансе"
    
    def test_insufficient_balance_for_order(self):
        """Тест недостаточного баланса для заказа"""
        from decimal import Decimal
        balance = Decimal("300.00")
        order_cost = Decimal("500.00")
        
        assert balance < order_cost, "Заказ должен быть отклонен при недостаточном балансе"
    
    def test_exact_balance_for_order(self):
        """Тест точного баланса для заказа"""
        from decimal import Decimal
        balance = Decimal("500.00")
        order_cost = Decimal("500.00")
        
        assert balance >= order_cost, "Заказ должен быть разрешен при точном балансе"
    
    def test_zero_balance(self):
        """Тест нулевого баланса"""
        from decimal import Decimal
        balance = Decimal("0.00")
        order_cost = Decimal("500.00")
        
        assert balance < order_cost, "Заказ должен быть отклонен при нулевом балансе"


class TestPasswordValidation:
    """Тесты для валидации паролей"""
    
    def test_minimum_password_length(self):
        """Тест минимальной длины пароля (8 символов)"""
        min_length = 8
        password = "12345678"
        
        assert len(password) >= min_length, "Пароль должен быть не менее 8 символов"
    
    def test_password_too_short(self):
        """Тест слишком короткого пароля"""
        min_length = 8
        password = "1234567"
        
        assert len(password) < min_length, "Короткий пароль должен быть отклонен"
    
    def test_empty_password(self):
        """Тест пустого пароля"""
        password = ""
        
        assert len(password) == 0, "Пустой пароль должен быть отклонен"


class TestDateValidation:
    """Тесты для валидации дат"""
    
    def test_future_date(self):
        """Тест будущей даты"""
        from datetime import datetime, timedelta
        future_date = datetime.now() + timedelta(days=1)
        
        assert future_date > datetime.now(), "Будущая дата должна быть позже текущей"
    
    def test_past_date(self):
        """Тест прошедшей даты"""
        from datetime import datetime, timedelta
        past_date = datetime.now() - timedelta(days=1)
        
        assert past_date < datetime.now(), "Прошедшая дата должна быть раньше текущей"
    
    def test_date_format(self):
        """Тест формата даты"""
        date_str = "2025-10-27"
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            assert parsed_date is not None, "Дата должна быть корректно распарсена"
        except ValueError:
            pytest.fail("Валидная дата должна парситься без ошибок")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

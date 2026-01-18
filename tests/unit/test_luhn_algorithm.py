"""
BE-MVP-031: Тесты для алгоритма Луна (BE-MVP-010)
"""

import pytest
from utils.luhn_algorithm import validate_card_number


class TestLuhnAlgorithm:
    """Тесты для валидации номеров карт по алгоритму Луна"""
    
    def test_valid_card_numbers(self):
        """Тест валидных номеров карт"""
        # Известные валидные тестовые номера карт
        valid_cards = [
            "4532015112830366",  # Visa
            "5425233430109903",  # Mastercard
            "374245455400126",   # American Express
            "6011111111111117",  # Discover
        ]
        
        for card in valid_cards:
            assert validate_card_number(card), f"Карта {card} должна быть валидной"
    
    def test_invalid_card_numbers(self):
        """Тест невалидных номеров карт"""
        invalid_cards = [
            "4532015112830367",  # Неправильная контрольная сумма
            "1234567890123456",  # Случайные цифры
            "0000000000000000",  # Все нули
            "9999999999999999",  # Все девятки
        ]
        
        for card in invalid_cards:
            assert not validate_card_number(card), f"Карта {card} должна быть невалидной"
    
    def test_card_with_spaces(self):
        """Тест номера карты с пробелами"""
        card_with_spaces = "4532 0151 1283 0366"
        assert validate_card_number(card_with_spaces), "Карта с пробелами должна быть валидной"
    
    def test_card_with_dashes(self):
        """Тест номера карты с дефисами"""
        card_with_dashes = "4532-0151-1283-0366"
        assert validate_card_number(card_with_dashes), "Карта с дефисами должна быть валидной"
    
    def test_short_card_number(self):
        """Тест слишком короткого номера"""
        assert not validate_card_number("123"), "Короткий номер должен быть невалидным"
    
    def test_long_card_number(self):
        """Тест слишком длинного номера"""
        assert not validate_card_number("12345678901234567890"), "Длинный номер должен быть невалидным"
    
    def test_empty_string(self):
        """Тест пустой строки"""
        assert not validate_card_number(""), "Пустая строка должна быть невалидной"
    
    def test_non_numeric_characters(self):
        """Тест номера с буквами"""
        assert not validate_card_number("4532ABC112830366"), "Номер с буквами должен быть невалидным"
    
    def test_none_value(self):
        """Тест None"""
        assert not validate_card_number(None), "None должен быть невалидным"
    
    def test_amex_format(self):
        """Тест формата American Express (15 цифр)"""
        amex_card = "374245455400126"
        assert validate_card_number(amex_card), "American Express карта должна быть валидной"
    
    def test_visa_format(self):
        """Тест формата Visa (16 цифр, начинается с 4)"""
        visa_card = "4532015112830366"
        assert validate_card_number(visa_card), "Visa карта должна быть валидной"
    
    def test_mastercard_format(self):
        """Тест формата Mastercard (16 цифр, начинается с 5)"""
        mastercard = "5425233430109903"
        assert validate_card_number(mastercard), "Mastercard должна быть валидной"
    
    def test_single_digit_error(self):
        """Тест обнаружения ошибки в одной цифре"""
        valid_card = "4532015112830366"
        # Изменяем одну цифру
        invalid_card = "4532015112830367"
        
        assert validate_card_number(valid_card), "Оригинальная карта должна быть валидной"
        assert not validate_card_number(invalid_card), "Карта с ошибкой должна быть невалидной"
    
    def test_transposition_error(self):
        """Тест обнаружения ошибки транспозиции (перестановки соседних цифр)"""
        valid_card = "4532015112830366"
        # Меняем местами две соседние цифры
        invalid_card = "4532015112830636"  # 36 -> 63
        
        assert validate_card_number(valid_card), "Оригинальная карта должна быть валидной"
        # Алгоритм Луна должен обнаружить большинство транспозиций
        assert not validate_card_number(invalid_card), "Карта с транспозицией должна быть невалидной"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

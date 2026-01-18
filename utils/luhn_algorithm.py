"""
BE-MVP-010: Алгоритм Луна для валидации номеров банковских карт
"""


def validate_card_number(card_number: str) -> bool:
    """
    Валидация номера банковской карты по алгоритму Луна.
    
    Args:
        card_number: Номер карты (может содержать пробелы и дефисы)
        
    Returns:
        bool: True если номер валиден, False иначе
    """
    if not card_number:
        return False
    
    # Удаляем пробелы и дефисы
    card_number = card_number.replace(" ", "").replace("-", "")
    
    # Проверяем, что остались только цифры
    if not card_number.isdigit():
        return False
    
    # Проверяем длину (обычно 13-19 цифр, но чаще 15-16)
    if len(card_number) < 13 or len(card_number) > 19:
        return False
    
    # Проверяем, что карта не состоит только из нулей или одинаковых цифр
    if len(set(card_number)) == 1:
        return False
    
    # Алгоритм Луна
    def luhn_checksum(card_num):
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_num)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        
        return checksum % 10
    
    return luhn_checksum(card_number) == 0

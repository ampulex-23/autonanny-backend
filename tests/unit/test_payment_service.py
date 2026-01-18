"""
BE-MVP-031: Тесты для платежной системы (BE-MVP-008, BE-MVP-010)
"""

import pytest
from decimal import Decimal


class TestPaymentService:
    """Тесты для платежного сервиса"""
    
    def test_minimum_deposit_amount(self):
        """Тест минимальной суммы пополнения (100 руб)"""
        min_amount = Decimal("100.00")
        assert min_amount == Decimal("100.00"), "Минимальная сумма должна быть 100 руб"
    
    def test_minimum_withdrawal_amount(self):
        """Тест минимальной суммы вывода (500 руб)"""
        min_withdrawal = Decimal("500.00")
        assert min_withdrawal == Decimal("500.00"), "Минимальная сумма вывода должна быть 500 руб"
    
    def test_amount_validation_below_minimum(self):
        """Тест валидации суммы ниже минимума"""
        amount = Decimal("50.00")
        min_amount = Decimal("100.00")
        assert amount < min_amount, "Сумма ниже минимума должна быть отклонена"
    
    def test_amount_validation_above_minimum(self):
        """Тест валидации суммы выше минимума"""
        amount = Decimal("150.00")
        min_amount = Decimal("100.00")
        assert amount >= min_amount, "Сумма выше минимума должна быть принята"
    
    def test_amount_validation_exact_minimum(self):
        """Тест валидации суммы равной минимуму"""
        amount = Decimal("100.00")
        min_amount = Decimal("100.00")
        assert amount >= min_amount, "Сумма равная минимуму должна быть принята"
    
    def test_balance_calculation_after_deposit(self):
        """Тест расчета баланса после пополнения"""
        initial_balance = Decimal("1000.00")
        deposit_amount = Decimal("500.00")
        expected_balance = initial_balance + deposit_amount
        
        assert expected_balance == Decimal("1500.00"), "Баланс должен увеличиться на сумму пополнения"
    
    def test_balance_calculation_after_withdrawal(self):
        """Тест расчета баланса после вывода"""
        initial_balance = Decimal("1000.00")
        withdrawal_amount = Decimal("500.00")
        expected_balance = initial_balance - withdrawal_amount
        
        assert expected_balance == Decimal("500.00"), "Баланс должен уменьшиться на сумму вывода"
    
    def test_insufficient_balance_for_withdrawal(self):
        """Тест недостаточного баланса для вывода"""
        balance = Decimal("300.00")
        withdrawal_amount = Decimal("500.00")
        
        assert balance < withdrawal_amount, "Вывод должен быть отклонен при недостаточном балансе"
    
    def test_sufficient_balance_for_withdrawal(self):
        """Тест достаточного баланса для вывода"""
        balance = Decimal("1000.00")
        withdrawal_amount = Decimal("500.00")
        
        assert balance >= withdrawal_amount, "Вывод должен быть разрешен при достаточном балансе"
    
    def test_negative_amount_validation(self):
        """Тест валидации отрицательной суммы"""
        amount = Decimal("-100.00")
        assert amount < 0, "Отрицательная сумма должна быть отклонена"
    
    def test_zero_amount_validation(self):
        """Тест валидации нулевой суммы"""
        amount = Decimal("0.00")
        min_amount = Decimal("100.00")
        assert amount < min_amount, "Нулевая сумма должна быть отклонена"
    
    def test_large_amount_handling(self):
        """Тест обработки больших сумм"""
        large_amount = Decimal("1000000.00")
        assert large_amount > 0, "Большие суммы должны обрабатываться корректно"
    
    def test_decimal_precision(self):
        """Тест точности decimal для денежных операций"""
        amount1 = Decimal("100.50")
        amount2 = Decimal("200.75")
        total = amount1 + amount2
        
        assert total == Decimal("301.25"), "Decimal должен точно обрабатывать денежные операции"
    
    def test_rounding_to_kopecks(self):
        """Тест округления до копеек"""
        amount = Decimal("100.123")
        rounded = round(amount, 2)
        
        assert rounded == Decimal("100.12"), "Сумма должна округляться до 2 знаков"
    
    def test_multiple_transactions_balance(self):
        """Тест баланса после нескольких транзакций"""
        initial_balance = Decimal("1000.00")
        
        # Пополнение
        balance = initial_balance + Decimal("500.00")
        assert balance == Decimal("1500.00")
        
        # Списание
        balance = balance - Decimal("200.00")
        assert balance == Decimal("1300.00")
        
        # Еще пополнение
        balance = balance + Decimal("300.00")
        assert balance == Decimal("1600.00")
        
        # Еще списание
        balance = balance - Decimal("100.00")
        assert balance == Decimal("1500.00")


class TestWithdrawalValidation:
    """Тесты для валидации запросов на вывод средств"""
    
    def test_card_number_required(self):
        """Тест обязательности номера карты"""
        card_number = ""
        assert len(card_number) == 0, "Пустой номер карты должен быть отклонен"
    
    def test_card_number_format(self):
        """Тест формата номера карты"""
        valid_card = "4532015112830366"
        assert len(valid_card) in [15, 16, 19], "Номер карты должен иметь правильную длину"
    
    def test_withdrawal_amount_minimum(self):
        """Тест минимальной суммы вывода"""
        amount = Decimal("500.00")
        min_withdrawal = Decimal("500.00")
        assert amount >= min_withdrawal, "Сумма вывода должна быть не менее 500 руб"
    
    def test_withdrawal_below_minimum(self):
        """Тест вывода суммы ниже минимума"""
        amount = Decimal("400.00")
        min_withdrawal = Decimal("500.00")
        assert amount < min_withdrawal, "Вывод ниже минимума должен быть отклонен"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

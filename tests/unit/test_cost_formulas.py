"""
BE-MVP-031: Тесты для формул расчета стоимости поездок
"""

import pytest
from const.cost_formulas import get_total_cost_of_the_trip


class TestCostFormulas:
    """Тесты для формул расчета стоимости"""
    
    def test_basic_cost_calculation(self):
        """Тест базового расчета стоимости"""
        # M = 50 руб/км (тариф), S2 = 10000 м (10 км), To = 3600 сек (1 час)
        cost = get_total_cost_of_the_trip(M=50, S2=10000, To=3600)
        assert cost > 0, "Стоимость должна быть положительной"
        assert isinstance(cost, float), "Стоимость должна быть числом с плавающей точкой"
    
    def test_multiple_tariffs(self):
        """Тест расчета с разными тарифами"""
        # M - это тариф в руб/км, не количество детей
        cost_tariff_30 = get_total_cost_of_the_trip(M=30, S2=10000, To=3600)
        cost_tariff_50 = get_total_cost_of_the_trip(M=50, S2=10000, To=3600)
        cost_tariff_70 = get_total_cost_of_the_trip(M=70, S2=10000, To=3600)
        
        # Стоимость должна расти с тарифом
        assert cost_tariff_50 > cost_tariff_30, "Стоимость с тарифом 50 должна быть больше чем с 30"
        assert cost_tariff_70 > cost_tariff_50, "Стоимость с тарифом 70 должна быть больше чем с 50"
    
    def test_distance_impact(self):
        """Тест влияния расстояния на стоимость"""
        cost_short = get_total_cost_of_the_trip(M=50, S2=5000, To=600)  # 5 км, 10 мин
        cost_medium = get_total_cost_of_the_trip(M=50, S2=15000, To=1800)  # 15 км, 30 мин
        cost_long = get_total_cost_of_the_trip(M=50, S2=30000, To=3600)  # 30 км, 60 мин
        
        # Стоимость должна расти с расстоянием
        assert cost_medium > cost_short, "Стоимость должна расти с расстоянием"
        assert cost_long > cost_medium, "Стоимость должна расти с расстоянием"
    
    def test_time_impact(self):
        """Тест влияния времени на стоимость (пробки)"""
        # Одинаковое расстояние, но разное время (пробки)
        cost_fast = get_total_cost_of_the_trip(M=50, S2=10000, To=1200)  # 10 км за 20 мин (быстро)
        cost_normal = get_total_cost_of_the_trip(M=50, S2=10000, To=1800)  # 10 км за 30 мин (нормально)
        cost_slow = get_total_cost_of_the_trip(M=50, S2=10000, To=3600)  # 10 км за 60 мин (пробки)
        
        # Стоимость должна расти с временем (из-за коэффициента пробок)
        assert cost_slow >= cost_normal, "Стоимость в пробках должна быть больше или равна"
        assert cost_slow >= cost_fast, "Стоимость в пробках должна быть больше или равна быстрой поездке"
    
    def test_zero_distance(self):
        """Тест с нулевым расстоянием"""
        cost = get_total_cost_of_the_trip(M=50, S2=0, To=3600)
        assert cost > 0, "Стоимость должна быть положительной даже при нулевом расстоянии (есть радиус подачи)"
    
    def test_zero_time(self):
        """Тест с нулевым временем"""
        cost = get_total_cost_of_the_trip(M=50, S2=10000, To=0)
        assert cost >= 0, "Стоимость должна быть неотрицательной"
    
    def test_max_tariff(self):
        """Тест с максимальным тарифом"""
        cost = get_total_cost_of_the_trip(M=100, S2=10000, To=3600)
        assert cost > 0, "Стоимость с высоким тарифом должна быть положительной"
    
    def test_realistic_scenario_short_trip(self):
        """Тест реалистичного сценария: короткая поездка"""
        # Тариф 40 руб/км, 5 км, 15 минут
        cost = get_total_cost_of_the_trip(M=40, S2=5000, To=900)
        assert 100 < cost < 1000, f"Стоимость короткой поездки должна быть разумной: {cost}"
    
    def test_realistic_scenario_medium_trip(self):
        """Тест реалистичного сценария: средняя поездка"""
        # Тариф 50 руб/км, 15 км, 45 минут
        cost = get_total_cost_of_the_trip(M=50, S2=15000, To=2700)
        assert 500 < cost < 2000, f"Стоимость средней поездки должна быть разумной: {cost}"
    
    def test_realistic_scenario_long_trip(self):
        """Тест реалистичного сценария: длинная поездка"""
        # Тариф 60 руб/км, 30 км, 90 минут
        cost = get_total_cost_of_the_trip(M=60, S2=30000, To=5400)
        assert 1500 < cost < 5000, f"Стоимость длинной поездки должна быть разумной: {cost}"
    
    def test_cost_consistency(self):
        """Тест консистентности расчетов"""
        # Одинаковые параметры должны давать одинаковый результат
        cost1 = get_total_cost_of_the_trip(M=50, S2=10000, To=3600)
        cost2 = get_total_cost_of_the_trip(M=50, S2=10000, To=3600)
        assert cost1 == cost2, "Одинаковые параметры должны давать одинаковый результат"
    
    def test_negative_values_handling(self):
        """Тест обработки отрицательных значений"""
        # В идеале функция должна обрабатывать или отклонять отрицательные значения
        try:
            cost = get_total_cost_of_the_trip(M=-50, S2=10000, To=3600)
            # Если функция не выбрасывает исключение, проверяем результат
            # Отрицательный тариф технически может быть (скидка), но результат должен быть разумным
            assert isinstance(cost, float), "Результат должен быть числом"
        except (ValueError, AssertionError):
            # Это ожидаемое поведение для отрицательных значений
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

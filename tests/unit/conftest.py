"""
BE-MVP-031: Конфигурация для unit-тестов
Простые unit-тесты не требуют запуска приложения
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH для импортов
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

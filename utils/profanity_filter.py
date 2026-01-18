"""
BE-MVP-026: Фильтрация нецензурных слов
Утилита для модерации текстового контента
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Список нецензурных слов (базовый набор для демонстрации)
# В production следует использовать более полный список
PROFANITY_WORDS_RU = [
    # Добавьте русские нецензурные слова
    "блять", "бля", "хуй", "пизд", "ебать", "ебан", "сука", "хер", "нахер",
    "говно", "дерьмо", "жопа", "срать", "ссать", "мудак", "дебил"
]

PROFANITY_WORDS_EN = [
    # Добавьте английские нецензурные слова
    "fuck", "shit", "bitch", "ass", "damn", "crap", "dick", "pussy",
    "bastard", "asshole", "motherfucker"
]

# Объединяем все слова
ALL_PROFANITY_WORDS = PROFANITY_WORDS_RU + PROFANITY_WORDS_EN


def contains_profanity(text: str) -> bool:
    """
    Проверяет, содержит ли текст нецензурные слова.
    
    Args:
        text: Текст для проверки
        
    Returns:
        True если найдены нецензурные слова, False иначе
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    for word in ALL_PROFANITY_WORDS:
        # Используем границы слов для точного поиска
        pattern = r'\b' + re.escape(word) + r'\w*\b'
        if re.search(pattern, text_lower):
            return True
    
    return False


def filter_profanity(text: str, replacement: str = "***") -> Tuple[str, bool]:
    """
    Фильтрует нецензурные слова в тексте, заменяя их на указанную строку.
    
    Args:
        text: Текст для фильтрации
        replacement: Строка для замены (по умолчанию "***")
        
    Returns:
        Tuple[str, bool]: (отфильтрованный текст, был ли текст изменен)
    """
    if not text:
        return text, False
    
    filtered_text = text
    was_filtered = False
    found_words = []
    
    for word in ALL_PROFANITY_WORDS:
        # Используем границы слов для точного поиска
        pattern = r'\b' + re.escape(word) + r'\w*\b'
        
        # Проверяем наличие слова
        matches = re.finditer(pattern, filtered_text, re.IGNORECASE)
        for match in matches:
            found_words.append(match.group())
            was_filtered = True
        
        # Заменяем все вхождения
        filtered_text = re.sub(pattern, replacement, filtered_text, flags=re.IGNORECASE)
    
    # Логируем если были найдены нецензурные слова
    if was_filtered:
        logger.warning(
            f"Profanity detected and filtered",
            extra={
                "found_words_count": len(found_words),
                "original_length": len(text),
                "filtered_length": len(filtered_text),
                "event_type": "profanity_filtered"
            }
        )
    
    return filtered_text, was_filtered


def get_profanity_stats(text: str) -> dict:
    """
    Получает статистику по нецензурным словам в тексте.
    
    Args:
        text: Текст для анализа
        
    Returns:
        dict: Статистика (количество найденных слов, список слов)
    """
    if not text:
        return {"count": 0, "words": []}
    
    text_lower = text.lower()
    found_words = []
    
    for word in ALL_PROFANITY_WORDS:
        pattern = r'\b' + re.escape(word) + r'\w*\b'
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            found_words.append(match.group())
    
    return {
        "count": len(found_words),
        "words": found_words,
        "contains_profanity": len(found_words) > 0
    }

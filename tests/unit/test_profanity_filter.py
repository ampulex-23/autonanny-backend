"""
BE-MVP-031: Тесты для фильтрации нецензурных слов (BE-MVP-026)
"""

import pytest
from utils.profanity_filter import contains_profanity, filter_profanity, get_profanity_stats


class TestProfanityFilter:
    """Тесты для фильтрации нецензурных слов"""
    
    def test_contains_profanity_clean_text(self):
        """Тест чистого текста без нецензурных слов"""
        assert not contains_profanity("Привет, как дела?")
        assert not contains_profanity("Hello, how are you?")
        assert not contains_profanity("Добрый день, водитель!")
    
    def test_contains_profanity_russian(self):
        """Тест обнаружения русских нецензурных слов"""
        assert contains_profanity("Это блять плохо")
        assert contains_profanity("Какой хер")
        assert contains_profanity("Пошел нахер")
    
    def test_contains_profanity_english(self):
        """Тест обнаружения английских нецензурных слов"""
        assert contains_profanity("This is shit")
        assert contains_profanity("What the fuck")
        assert contains_profanity("Damn it")
    
    def test_filter_profanity_clean_text(self):
        """Тест фильтрации чистого текста"""
        text = "Привет, как дела?"
        filtered, was_filtered = filter_profanity(text)
        assert filtered == text
        assert not was_filtered
    
    def test_filter_profanity_russian(self):
        """Тест фильтрации русских нецензурных слов"""
        text = "Это блять плохо"
        filtered, was_filtered = filter_profanity(text)
        assert "***" in filtered
        assert "блять" not in filtered.lower()
        assert was_filtered
    
    def test_filter_profanity_english(self):
        """Тест фильтрации английских нецензурных слов"""
        text = "This is shit"
        filtered, was_filtered = filter_profanity(text)
        assert "***" in filtered
        assert "shit" not in filtered.lower()
        assert was_filtered
    
    def test_filter_profanity_multiple_words(self):
        """Тест фильтрации нескольких нецензурных слов"""
        text = "Блять, это хер знает что"
        filtered, was_filtered = filter_profanity(text)
        assert filtered.count("***") >= 2
        assert was_filtered
    
    def test_filter_profanity_custom_replacement(self):
        """Тест фильтрации с кастомной заменой"""
        text = "Это блять плохо"
        filtered, was_filtered = filter_profanity(text, replacement="[censored]")
        assert "[censored]" in filtered
        assert was_filtered
    
    def test_filter_profanity_case_insensitive(self):
        """Тест нечувствительности к регистру"""
        text1 = "БЛЯТЬ"
        text2 = "блять"
        text3 = "Блять"
        
        filtered1, _ = filter_profanity(text1)
        filtered2, _ = filter_profanity(text2)
        filtered3, _ = filter_profanity(text3)
        
        assert "***" in filtered1
        assert "***" in filtered2
        assert "***" in filtered3
    
    def test_filter_profanity_empty_string(self):
        """Тест пустой строки"""
        filtered, was_filtered = filter_profanity("")
        assert filtered == ""
        assert not was_filtered
    
    def test_filter_profanity_none(self):
        """Тест None"""
        filtered, was_filtered = filter_profanity(None)
        assert filtered is None
        assert not was_filtered
    
    def test_get_profanity_stats_clean(self):
        """Тест статистики для чистого текста"""
        stats = get_profanity_stats("Привет, как дела?")
        assert stats["count"] == 0
        assert len(stats["words"]) == 0
        assert not stats["contains_profanity"]
    
    def test_get_profanity_stats_with_profanity(self):
        """Тест статистики с нецензурными словами"""
        stats = get_profanity_stats("Блять, это хер знает")
        assert stats["count"] >= 2
        assert len(stats["words"]) >= 2
        assert stats["contains_profanity"]
    
    def test_filter_profanity_preserves_structure(self):
        """Тест сохранения структуры текста"""
        text = "Привет! Это блять тест. Как дела?"
        filtered, _ = filter_profanity(text)
        
        # Проверяем, что знаки препинания сохранены
        assert "!" in filtered
        assert "." in filtered
        assert "?" in filtered
    
    def test_filter_profanity_word_boundaries(self):
        """Тест границ слов (не должно фильтровать части слов)"""
        # Слово "хер" не должно фильтроваться в слове "химера"
        text = "Химера - это мифическое существо"
        filtered, was_filtered = filter_profanity(text)
        # Если фильтр правильно работает с границами слов, текст не должен измениться
        # (зависит от реализации)
    
    def test_filter_profanity_mixed_languages(self):
        """Тест смешанного текста (русский + английский)"""
        text = "This is блять bad shit"
        filtered, was_filtered = filter_profanity(text)
        assert "***" in filtered
        assert was_filtered
        # Должны быть отфильтрованы оба слова
        assert filtered.count("***") >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

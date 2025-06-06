import pytest
from utils import detect_platform

# Функция increment_download_count была удалена, так как логика перенесена в БД
# Поэтому соответствующий тест также удалён.

def test_detect_platform():
    # Тесты для TikTok
    assert detect_platform("https://www.tiktok.com/@user/video/123") == "tiktok"
    assert detect_platform("http://tiktok.com/some/video") == "tiktok"
    
    # Тесты для Instagram
    assert detect_platform("https://instagram.com/p/abcd") == "instagram"
    assert detect_platform("https://www.instagram.com/reel/Cxyz/") == "instagram"
    
    # Тесты для YouTube
    assert detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
    assert detect_platform("https://youtu.be/dQw4w9WgXcQ") == "youtube"
    
    # Тесты для неподдерживаемых ссылок
    assert detect_platform("https://example.com/video") is None
    assert detect_platform("https://twitter.com/user/status/123") is None
    
    # Тест нахождения ссылки в тексте
    assert detect_platform("Посмотри это: https://www.youtube.com/watch?v=12345") == "youtube"
import pytest
from utils import detect_platform, increment_download_count
from datetime import datetime, timedelta

def test_detect_platform():
    assert detect_platform("https://www.tiktok.com/@user/video/123") == "tiktok"
    assert detect_platform("https://instagram.com/p/abcd") == "instagram"
    assert detect_platform("https://youtu.be/xyz") == "youtube"
    assert detect_platform("https://example.com/video") is None

def test_increment_download_count():
    user = {"download_count": 0, "last_reset": datetime.utcnow() - timedelta(days=2)}
    assert increment_download_count(user, 5) is True
    assert user["download_count"] == 1
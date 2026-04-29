import os
from app.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key-123")
    monkeypatch.setenv("BASE_URL", "https://test.example.com")
    settings = Settings()
    assert settings.api_key == "test-key-123"
    assert str(settings.base_url) == "https://test.example.com/"


def test_settings_default_port():
    settings = Settings()
    assert settings.app_port == 8888

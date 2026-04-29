from pydantic_settings import BaseSettings
from pydantic import HttpUrl


class Settings(BaseSettings):
    # AI
    base_url: HttpUrl = "https://api.openai.com"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    hook_url: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///db/getjobs.db"

    # App
    app_port: int = 8888
    app_host: str = "0.0.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

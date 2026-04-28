from typing import Optional
from pydantic_settings import BaseSettings
from tortoise import Tortoise
from app.utils.auto_routing import get_apps_structure


class Settings(BaseSettings):
    DEBUG: bool = True
    APP_NAME: str = "FastAPI App"
    MEDIA_DIR: str = "media/"
    MEDIA_ROOT: str = "media/"
    CREATE_DUMMY_DATA: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int =10
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_HOST_USER: str = "lookuparchitecture@gmail.com"
    EMAIL_HOST_PASSWORD: str = "ihuciytlvdymggol"
    DEFAULT_FROM_EMAIL: str = "lookuparchitecture@gmail.com"

    DB_HOST: str = "localhost"
    DB_NAME: str = "db.sqlite3"
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_ROOT_PASSWORD: str = ""
    DB_PORT: int = 5432
    DB_ENGINE: str = "postgres"

    DATABASE_URL: Optional[str] = None

    SECRET_KEY: Optional[str] = None
    GOOGLE_CLIENT_IDS: str = ""
    APPLE_CLIENT_IDS: str = ""
    BASE_URL: str = "http://localhost:8000/"
    RADIS_URL: str = "redis://localhost:6379/0"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    AI_PROVIDER: str = "gemini"  # "gemini" or "openai"

    def model_post_init(self, __context):
        if self.DB_ENGINE == "sqlite":
            self.DATABASE_URL = f"sqlite:///{self.DB_NAME}"
        else:
            self.DATABASE_URL = (
                f"{self.DB_ENGINE}://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

TORTOISE_ORM = {
    "connections": {
        "default": settings.DATABASE_URL,
    },
    "apps": get_apps_structure("applications"),
    "use_tz": True,
    "timezone": "Asia/Dhaka",
}
import json
print(json.dumps(TORTOISE_ORM, indent=4))

async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    if settings.DEBUG:
        await Tortoise.generate_schemas()
    else:
        print("Skipping schema generation in production.")


async def close_db():
    await Tortoise.close_connections()

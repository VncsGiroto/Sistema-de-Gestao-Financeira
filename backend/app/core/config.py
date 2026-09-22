from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FinanceWay API"
    database_url: str = "postgresql+asyncpg://finance:finance@db:5432/financeway"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-env"
    jwt_alg: str = "HS256"
    access_ttl: int = 900
    refresh_ttl: int = 2592000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

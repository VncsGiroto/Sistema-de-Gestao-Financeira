from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FinanceWay API"
    database_url: str = "postgresql+asyncpg://finance:finance@db:5432/financeway"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-env"
    jwt_alg: str = "HS256"
    access_ttl: int = 900
    refresh_ttl: int = 2592000
    ofx_dir: str = "/data/ofx"
    ofx_max_bytes: int = 10 * 1024 * 1024
    dedup_window_days: int = 2


settings = Settings()

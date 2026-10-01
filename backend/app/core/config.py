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
    # hardening (6.1)
    env: str = "dev"  # dev | prod (prod = fail-closed no Redis + cookie Secure)
    login_rate_limit: int = 10  # anti-bruteforce no login (req/min/IP); E2E/CI eleva via env
    cors_origins: str = "http://localhost:8080,http://localhost:5173"
    cookie_secure: bool = False  # True atrás de HTTPS em prod

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://rohobot:rohobot@localhost:5432/rohobot"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    frontend_base_url: str = "http://localhost:3000"
    public_api_url: str = "http://localhost:8000"
    environment: str = "development"
    session_ttl_hours: int = 12
    db_pool_size: int = 5
    db_max_overflow: int = 5
    payment_provider: str = "disabled"
    chapa_api_url: str = "https://api.chapa.co/v1"
    chapa_secret_key: str = ""
    chapa_webhook_secret: str = ""
    payment_timeout_seconds: float = 8.0
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: float = 8.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

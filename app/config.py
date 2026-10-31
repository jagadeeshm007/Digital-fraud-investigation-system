from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    masking_hmac_key: str  # 64-char hex = 32 bytes
    serve_frontend: bool = False
    max_upload_size_mb: int = 50
    log_level: str = "INFO"


settings = Settings()

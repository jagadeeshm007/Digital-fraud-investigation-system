from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    masking_hmac_key: str  # 64-char hex = 32 bytes
    serve_frontend: bool = False
    max_upload_size_mb: int = 50
    log_level: str = "INFO"

    # AI review (Groq — migrate to OpenRouter later)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"  # override with GROQ_MODEL env
    fake_llm: bool = False  # FAKE_LLM=1 in CI


settings = Settings()

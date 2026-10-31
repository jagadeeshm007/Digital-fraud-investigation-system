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
    groq_model: str = "openai/gpt-oss-120b"  # override with GROQ_MODEL env
    fake_llm: bool = False  # FAKE_LLM=1 in CI
    ai_budget_usd: float = 10.0  # hard cap on estimated AI spend (NFR8)
    ai_review_batch: int = 25  # alerts reviewed in the background after each detection run
    mcp_stateless: bool = False  # MCP_STATELESS=1 on serverless hosts (Vercel): no in-memory sessions
    mcp_allowed_hosts: str = ""  # extra Host headers for /mcp, e.g. "dfis.onrender.com"


settings = Settings()

import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

_INSECURE_DEFAULTS = {"change-this-secret", "secret", "dev", "test"}


class Settings(BaseSettings):
    secret_key: str = Field(default="change-this-secret", alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    database_url: str = Field(default="sqlite:///./inventory.db", alias="DATABASE_URL")
    poc_id: str = Field(default="POC-07", alias="POC_ID")
    phase: int = Field(default=1, alias="PHASE")
    associate_id: str = Field(default="unknown", alias="ASSOCIATE_ID")
    cors_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="CORS_ORIGINS",
    )
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    langchain_api_key: str | None = Field(default=None, alias="LANGCHAIN_API_KEY")
    langchain_tracing_v2: str | None = Field(default="true", alias="LANGCHAIN_TRACING_V2")
    langchain_project: str | None = Field(default="AI-Readiness-POC-07-P2", alias="LANGCHAIN_PROJECT")
    dev_user_email: str = Field(default="manager@poc07.com", alias="DEV_USER_EMAIL")
    dev_user_password: str = Field(default="Password@123", alias="DEV_USER_PASSWORD")
    seed_dev_user: bool = Field(default=True, alias="SEED_DEV_USER")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("secret_key")
    @classmethod
    def warn_insecure_secret(cls, v: str) -> str:
        if v.lower() in _INSECURE_DEFAULTS:
            import warnings
            warnings.warn(
                "SECRET_KEY is set to an insecure default. Set a strong random value in .env.",
                stacklevel=2,
            )
        return v


settings = Settings()


def _export_phase2_env() -> None:
    if settings.ollama_base_url:
        os.environ.setdefault("OLLAMA_BASE_URL", settings.ollama_base_url)
    if settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    if settings.langchain_tracing_v2:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", str(settings.langchain_tracing_v2))
    if settings.langchain_project:
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)


_export_phase2_env()

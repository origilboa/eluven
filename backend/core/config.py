"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # AWS
    aws_region: str = "us-east-1"
    s3_documents_bucket: str
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v1"
    document_chunk_size_tokens: int = 512
    document_chunk_overlap_tokens: int = 50
    thread_document_full_text_token_threshold: int = 4000
    embed_batch_size: int = 10
    s3_presigned_url_expiry_seconds: int = 3600
    document_processing_queue_url: str = ""

    # Auth
    nextauth_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # App
    environment: str = "development"
    log_level: str = "INFO"
    api_version: str = "v1"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed CORS allowed origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def async_database_url(self) -> str:
        """Database URL for SQLAlchemy async engine (asyncpg driver)."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()

"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str

    # AWS
    aws_region: str = "us-east-1"
    s3_documents_bucket: str

    # Auth
    nextauth_secret: str

    # App
    environment: str = "development"
    log_level: str = "INFO"
    api_version: str = "v1"

    class Config:
        env_file = ".env"


settings = Settings()

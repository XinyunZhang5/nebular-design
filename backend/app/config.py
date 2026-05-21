from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://nebular:nebular@localhost:5432/nebulardb"
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = 10080  # 7 days

    anthropic_api_key: str = ""

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "nebular-design-uploads"
    use_s3: bool = False

    enable_depth_estimation: bool = True
    depth_model: str = "depth-anything/Depth-Anything-V2-Small-hf"

    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()

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

    # Comma-separated list of allowed frontend origins
    frontend_url: str = "http://localhost:3000"

    port: int = 8000

    class Config:
        env_file = ".env"

    @property
    def async_database_url(self) -> str:
        # Railway provides postgresql:// — convert to asyncpg dialect
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def allowed_origins(self) -> list[str]:
        origins = [o.strip() for o in self.frontend_url.split(",") if o.strip()]
        # Always allow localhost for local dev
        for port in (3000, 3001):
            for host in ("localhost", "127.0.0.1"):
                origins.append(f"http://{host}:{port}")
        return list(dict.fromkeys(origins))  # deduplicate, preserve order


@lru_cache
def get_settings() -> Settings:
    return Settings()

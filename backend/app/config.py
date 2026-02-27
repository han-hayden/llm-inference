from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    PROXY_PORT: int = 8081

    # Data Storage
    DATA_DIR: Path = Path("/data/results")
    MAX_RECORDS_PER_FILE: int = 1000
    FLUSH_INTERVAL: int = 5
    FLUSH_BATCH: int = 10

    # Database
    DATABASE_URL: str = ""

    # Auth
    SECRET_KEY: str = "aicp-perf-tool-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "changeme"

    # Proxy
    PROXY_TIMEOUT: int = 300
    PROXY_MAX_CONNECTIONS: int = 500

    model_config = {"env_file": ".env", "env_prefix": "AICP_"}

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        db_path = self.DATA_DIR / "tasks.db"
        return f"sqlite:///{db_path}"


settings = Settings()

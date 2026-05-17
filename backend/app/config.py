import os
from pathlib import Path

# Load .env file if present (for local development).
# This must happen before reading any env vars below.
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                k = key.strip()
                v = value.strip()
                # Strip surrounding quotes if present
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                    v = v[1:-1]
                if v:
                    os.environ[k] = v


class Settings:
    """Application settings read from environment variables at access time."""

    @property
    def CMS_PASSWORD_HASH(self) -> str:
        return os.environ.get("CMS_PASSWORD_HASH", "")

    @property
    def JWT_SECRET(self) -> str:
        return os.environ.get("JWT_SECRET", "")

    @property
    def AWS_ACCESS_KEY_ID(self) -> str:
        return os.environ.get("AWS_ACCESS_KEY_ID", "")

    @property
    def AWS_SECRET_ACCESS_KEY(self) -> str:
        return os.environ.get("AWS_SECRET_ACCESS_KEY", "")

    @property
    def AWS_REGION(self) -> str:
        return os.environ.get("AWS_REGION", "")

    @property
    def S3_BUCKET(self) -> str:
        return os.environ.get("S3_BUCKET", "")

    @property
    def CLOUDFRONT_DOMAIN(self) -> str:
        return os.environ.get("CLOUDFRONT_DOMAIN", "")

    @property
    def CORS_ORIGINS(self) -> list[str]:
        raw = os.environ.get("CORS_ORIGINS", "*")
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic_settings import BaseSettings


class SecurityConfig(BaseSettings):
    """Security configuration settings."""

    API_KEY: str
    API_KEY_NAME: str = "X-API-Key"

    class Config:
        env_file = ".env"


# Initialize settings
security_config = SecurityConfig(API_KEY="")

# API key header instance
api_key_header = APIKeyHeader(name=security_config.API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> None:
    """Verify the API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key header is missing",
            headers={"WWW-Authenticate": security_config.API_KEY_NAME},
        )

    if api_key != security_config.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": security_config.API_KEY_NAME},
        )

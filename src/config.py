"""
Configuration management for hr-pilot.

Loads environment variables from .env file and provides a settings object
with all application configuration (Telegram tokens, ADP credentials, etc.).
"""

from typing import List, Union

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram
    telegram_bot_token: str
    telegram_allowed_user_ids: List[int]

    # ADP Credentials
    adp_username: str
    adp_password: SecretStr
    adp_login_url: str = (
        "https://online.adp.com/signin/v1/"
        "?APPID=WFNPortal&productId=80e309c3-7085-bae1-e053-3505430b5495"
        "&returnURL=https://workforcenow.adp.com/&callingAppId=WFN"
    )

    # App Settings
    headless: bool = True
    screenshot_dir: str = "screenshots"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("telegram_allowed_user_ids", mode="before")
    @classmethod
    def parse_allowed_user_ids(cls, v: Union[str, int, List[int]]) -> List[int]:
        """Parse comma-separated string of user IDs into list of integers."""
        if isinstance(v, str):
            return [int(user_id.strip()) for user_id in v.split(",")]
        elif isinstance(v, int):
            return [v]
        return v


settings = Settings()

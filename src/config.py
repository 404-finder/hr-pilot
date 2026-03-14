"""
Configuration management for hr-pilot.

Loads environment variables from .env file and provides a settings object
with all application configuration (Telegram tokens, ADP credentials, etc.).
"""

import os
from dataclasses import dataclass
from typing import Dict, List

from dotenv import dotenv_values
from pydantic import PrivateAttr, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass
class AdpCredentials:
    """ADP credentials for a specific Telegram user."""

    username: str
    password: SecretStr


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram
    telegram_bot_token: str
    telegram_allowed_user_ids: str  # raw CSV string; use allowed_user_ids property for List[int]

    # ADP shared settings
    adp_login_url: str = (
        "https://online.adp.com/signin/v1/"
        "?APPID=WFNPortal&productId=80e309c3-7085-bae1-e053-3505430b5495"
        "&returnURL=https://workforcenow.adp.com/&callingAppId=WFN"
    )

    # App Settings
    headless: bool = True
    screenshot_dir: str = "screenshots"
    log_level: str = "INFO"

    # Private: populated by model_validator after init
    _adp_credentials: Dict[int, AdpCredentials] = PrivateAttr(default_factory=dict)

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    @property
    def allowed_user_ids(self) -> List[int]:
        """Parse telegram_allowed_user_ids CSV string into a list of ints."""
        return [int(uid.strip()) for uid in self.telegram_allowed_user_ids.split(",")]

    @model_validator(mode="after")
    def parse_adp_credentials(self) -> "Settings":
        """Parse numbered ADP_USERNAME_N/ADP_PASSWORD_N/TELEGRAM_USER_ID_N env vars.

        Reads from .env file first, then os.environ overrides, matching pydantic-settings
        precedence. Looks for ADP_USERNAME_1, ADP_USERNAME_2, ... until a set is missing.
        """
        env_file = self.model_config.get("env_file", ".env")
        env = {**dotenv_values(env_file), **os.environ}

        credentials: Dict[int, AdpCredentials] = {}
        n = 1
        while True:
            username = env.get(f"ADP_USERNAME_{n}")
            password = env.get(f"ADP_PASSWORD_{n}")
            user_id = env.get(f"TELEGRAM_USER_ID_{n}")
            if not username or not password or not user_id:
                break
            credentials[int(user_id)] = AdpCredentials(
                username=username,
                password=SecretStr(password),
            )
            n += 1
        self._adp_credentials = credentials
        return self

    def get_adp_credentials(self, telegram_user_id: int) -> AdpCredentials:
        """Get ADP credentials mapped to a Telegram user ID.

        Args:
            telegram_user_id: Telegram user ID to look up.

        Returns:
            AdpCredentials with username and password.

        Raises:
            ValueError: If no credentials configured for the user.
        """
        if telegram_user_id not in self._adp_credentials:
            raise ValueError(
                f"No ADP credentials configured for Telegram user {telegram_user_id}. "
                "Check ADP_USERNAME_N, ADP_PASSWORD_N, TELEGRAM_USER_ID_N in .env."
            )
        return self._adp_credentials[telegram_user_id]


settings = Settings()

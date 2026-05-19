"""Application configuration loaded from environment variables.

Uses pydantic-settings to load config from a .env file.
Import `settings` from this module wherever config is needed.

Example:
    from extractly.config import settings
    print(settings.gemini_api_key)
"""

import logging
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for Extractly.

    All values can be overridden via environment variables or a .env file.
    """

    # Required
    gemini_api_key: str = ""

    # Optional with sensible defaults
    gemini_model: str = "gemini-2.5-flash"
    input_dir: Path = Path("./input_docs")
    output_dir: Path = Path("./output")

    # Batch polling
    batch_poll_interval_seconds: int = 30
    batch_timeout_seconds: int = 86400  # 24 hours

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def validate_api_key(self) -> None:
        """Raise ValueError if the API key is not set."""
        if not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Set it in your .env file or as an environment variable."
            )


def get_settings() -> Settings:
    """Create and return a Settings instance.

    Returns:
        A validated Settings object loaded from environment.
    """
    return Settings()


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with a consistent format.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

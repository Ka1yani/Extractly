"""Tests for extractly.config module."""

import os
from pathlib import Path

import pytest

from extractly.config import Settings, get_settings, setup_logging


class TestSettings:
    """Tests for the Settings configuration class."""

    def test_default_values(self) -> None:
        """Settings should have sensible defaults for optional fields."""
        settings = Settings(gemini_api_key="test-key")

        assert settings.gemini_model == "gemini-2.5-flash"
        assert settings.input_dir == Path("./input_docs")
        assert settings.output_dir == Path("./output")
        assert settings.batch_poll_interval_seconds == 30
        assert settings.batch_timeout_seconds == 86400
        assert settings.log_level == "INFO"

    def test_api_key_stored(self) -> None:
        """API key should be stored from constructor."""
        settings = Settings(gemini_api_key="my-secret-key")
        assert settings.gemini_api_key == "my-secret-key"

    def test_empty_api_key_default(self) -> None:
        """API key defaults to empty string when not provided."""
        settings = Settings()
        assert settings.gemini_api_key == ""

    def test_validate_api_key_raises_when_empty(self) -> None:
        """validate_api_key should raise ValueError when key is empty."""
        settings = Settings(gemini_api_key="")
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
            settings.validate_api_key()

    def test_validate_api_key_passes_when_set(self) -> None:
        """validate_api_key should not raise when key is provided."""
        settings = Settings(gemini_api_key="valid-key")
        settings.validate_api_key()  # Should not raise

    def test_custom_paths(self) -> None:
        """Custom input/output paths should be accepted."""
        settings = Settings(
            gemini_api_key="key",
            input_dir=Path("/custom/input"),
            output_dir=Path("/custom/output"),
        )
        assert settings.input_dir == Path("/custom/input")
        assert settings.output_dir == Path("/custom/output")

    def test_custom_model(self) -> None:
        """Custom model name should be accepted."""
        settings = Settings(gemini_api_key="key", gemini_model="gemini-2.0-pro")
        assert settings.gemini_model == "gemini-2.0-pro"

    def test_loads_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings should load values from environment variables."""
        monkeypatch.setenv("GEMINI_API_KEY", "env-key-123")
        monkeypatch.setenv("GEMINI_MODEL", "gemini-custom")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        settings = Settings()

        assert settings.gemini_api_key == "env-key-123"
        assert settings.gemini_model == "gemini-custom"
        assert settings.log_level == "DEBUG"

    def test_loads_from_env_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings should load values from a .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("GEMINI_API_KEY=file-key-456\nGEMINI_MODEL=gemini-file\n")

        # Change to tmp directory so .env is found
        monkeypatch.chdir(tmp_path)

        settings = Settings(_env_file=env_file)
        assert settings.gemini_api_key == "file-key-456"


class TestGetSettings:
    """Tests for the get_settings factory function."""

    def test_returns_settings_instance(self) -> None:
        """get_settings should return a Settings object."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_each_call_returns_fresh_instance(self) -> None:
        """get_settings should return a new instance each time (not cached)."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is not s2


class TestSetupLogging:
    """Tests for the setup_logging helper."""

    def test_setup_logging_does_not_raise(self) -> None:
        """setup_logging should configure logging without errors."""
        setup_logging("DEBUG")  # Should not raise

    def test_setup_logging_with_info(self) -> None:
        """setup_logging should accept INFO level."""
        setup_logging("INFO")  # Should not raise

    def test_setup_logging_case_insensitive(self) -> None:
        """setup_logging should handle mixed-case level strings."""
        setup_logging("warning")  # Should not raise

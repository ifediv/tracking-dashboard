"""Configuration management for the trading analytics system."""

from pathlib import Path
from typing import Any, Dict, List
import yaml
from dotenv import load_dotenv
import os


class Config:
    """Centralized configuration management.

    Loads settings from:
    - .env file (environment variables, secrets)
    - config/settings.yaml (application settings)

    Usage:
        >>> config = Config()
        >>> print(config.database_url)
        >>> print(config.strategy_types)
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure one config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize configuration."""
        if self._initialized:
            return

        # Load environment variables from .env file
        load_dotenv()

        # Load YAML settings
        self.settings = self._load_yaml()

        self._initialized = True

    def _load_yaml(self) -> Dict[str, Any]:
        """Load settings from YAML file.

        Returns:
            Dictionary of settings

        Raises:
            FileNotFoundError: If settings.yaml doesn't exist
        """
        # Get path relative to this file
        config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    # Environment Variables (from .env)

    @property
    def database_url(self) -> str:
        """Get database URL from environment."""
        return os.getenv("DATABASE_URL", "sqlite:///data/trading_analytics.db")

    @property
    def environment(self) -> str:
        """Get environment (development, production)."""
        return os.getenv("ENVIRONMENT", "development")

    @property
    def debug(self) -> bool:
        """Get debug flag."""
        return os.getenv("DEBUG", "false").lower() == "true"

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def market_timezone(self) -> str:
        """Get market timezone."""
        return os.getenv("MARKET_TIMEZONE", "America/New_York")

    @property
    def polygon_api_key(self) -> str:
        """Get Polygon API key (for Phase 2)."""
        return os.getenv("POLYGON_API_KEY", "")

    # YAML Settings

    @property
    def strategy_types(self) -> List[str]:
        """Get list of valid strategy types."""
        return self.settings.get('strategy_types', [])

    @property
    def timeframes(self) -> List[int]:
        """Get list of analysis timeframes (in minutes)."""
        return self.settings.get('timeframes', [])

    @property
    def validation_rules(self) -> Dict[str, Any]:
        """Get validation rules."""
        return self.settings.get('validation', {})

    @property
    def csv_import_settings(self) -> Dict[str, Any]:
        """Get CSV import settings."""
        return self.settings.get('csv_import', {})

    # Convenience methods

    def is_valid_strategy(self, strategy_type: str) -> bool:
        """Check if strategy type is valid.

        Args:
            strategy_type: Strategy to validate

        Returns:
            True if valid, False otherwise
        """
        return strategy_type in self.strategy_types

    def is_valid_timeframe(self, timeframe_minutes: int) -> bool:
        """Check if timeframe is valid.

        Args:
            timeframe_minutes: Timeframe to validate

        Returns:
            True if valid, False otherwise
        """
        return timeframe_minutes in self.timeframes


# Global config instance
config = Config()

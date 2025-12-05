"""Configuration management using environment variables."""

import os

from dotenv import load_dotenv

# Load environment variables from .env file (CLAUDE.md requirement)
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Alpaca API Configuration
    ALPACA_API_KEY: str
    ALPACA_SECRET_KEY: str

    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Optional Market Data APIs
    TWELVEDATA_API_KEY: str | None
    ALPHA_VANTAGE_API_KEY: str | None

    # LLM Configuration (OpenRouter)
    OPENROUTER_API_KEY: str | None
    OPENROUTER_BASE_URL: str
    OPENROUTER_MODEL: str
    OPENROUTER_MODEL: str
    ENABLE_LLM_FEATURES: bool

    # News & LLM Configuration
    NEWS_API_KEY: str | None
    FINNHUB_API_KEY: str | None
    ANTHROPIC_API_KEY: str | None

    # Trading Strategy Configuration
    ENABLE_NEWS_VERIFICATION: bool
    ENABLE_NEWS_SIGNALS: bool
    DEFENSIVE_ALLOCATION_PCT: float

    # Environment Settings
    ENVIRONMENT: str
    LOG_LEVEL: str

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        # Required variables
        self.ALPACA_API_KEY = self._get_required("ALPACA_API_KEY")
        self.ALPACA_SECRET_KEY = self._get_required("ALPACA_SECRET_KEY")
        self.SUPABASE_URL = self._get_required("SUPABASE_URL")
        self.SUPABASE_KEY = self._get_required("SUPABASE_KEY")

        # Optional variables
        self.TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
        self.ALPHA_VANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

        # LLM Configuration
        self.OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
        self.OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        self.OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        self.ENABLE_LLM_FEATURES = os.getenv("ENABLE_LLM_FEATURES", "false").lower() == "true"

        # News & LLM Configuration
        # News & LLM Configuration
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY")
        self.FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

        # Trading Strategy Configuration (NEW)
        # Controls for simplified trading approach
        self.ENABLE_NEWS_VERIFICATION = os.getenv("ENABLE_NEWS_VERIFICATION", "false").lower() == "true"
        self.ENABLE_NEWS_SIGNALS = os.getenv("ENABLE_NEWS_SIGNALS", "true").lower() == "true"
        self.DEFENSIVE_ALLOCATION_PCT = float(os.getenv("DEFENSIVE_ALLOCATION_PCT", "0.30"))

        # Environment settings with defaults
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    def _get_required(self, key: str) -> str:
        """Get a required environment variable or raise an error.

        Args:
            key: Environment variable name

        Returns:
            Value of the environment variable

        Raises:
            ValueError: If the environment variable is not set
        """
        value = os.getenv(key)
        if value is None or value == "":
            raise ValueError(
                f"Required environment variable '{key}' is not set. "
                f"Please check your .env file or environment configuration."
            )
        return value

    def validate(self) -> None:
        """Validate that all required configuration is present.

        Raises:
            ValueError: If any required configuration is missing
        """
        # Required fields validation (already checked in __init__)
        required_fields = [
            "ALPACA_API_KEY",
            "ALPACA_SECRET_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
        ]

        for field in required_fields:
            value = getattr(self, field, None)
            if not value:
                raise ValueError(f"Configuration field '{field}' is missing or empty")

        # Validate URL format for Supabase
        if not self.SUPABASE_URL.startswith("https://"):
            raise ValueError("SUPABASE_URL must start with 'https://'")


# Global configuration instance
config = Config()
config.validate()

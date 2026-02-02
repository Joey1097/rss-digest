"""
Configuration management for Auto-RSS-Digest.
Loads all settings from environment variables.
"""
import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class Config:
    """Application configuration loaded from environment variables."""
    
    # LLM Settings
    llm_provider: Literal["gemini", "deepseek"] = "gemini"
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    
    # Time Settings
    timezone: str = "Asia/Singapore"
    time_window_hours: int = 24
    
    # Content Settings
    max_content_length: int = 15000
    api_delay_seconds: float = 2.0
    
    # Paths
    opml_path: str = "feeds.opml"
    archives_dir: str = "archives"
    readme_path: str = "README.md"
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "gemini").lower(),  # type: ignore
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            timezone=os.getenv("TZ", "Asia/Singapore"),
            time_window_hours=int(os.getenv("TIME_WINDOW_HOURS", "24")),
            max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "15000")),
            api_delay_seconds=float(os.getenv("API_DELAY_SECONDS", "2.0")),
            opml_path=os.getenv("OPML_PATH", "feeds.opml"),
            archives_dir=os.getenv("ARCHIVES_DIR", "archives"),
            readme_path=os.getenv("README_PATH", "README.md"),
        )
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            errors.append("GEMINI_API_KEY is required when LLM_PROVIDER is 'gemini'")
        
        if self.llm_provider == "deepseek" and not self.deepseek_api_key:
            errors.append("DEEPSEEK_API_KEY is required when LLM_PROVIDER is 'deepseek'")
        
        if self.time_window_hours < 1:
            errors.append("TIME_WINDOW_HOURS must be at least 1")
        
        return errors


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config() -> None:
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None

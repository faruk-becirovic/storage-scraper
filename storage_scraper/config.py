import json
import os
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel
from loguru import logger

class Config(BaseModel):
    """Configuration model for Storage Scraper."""
    ollama_model: str = "gemma3n:e4b"
    ollama_base_url: str = "http://localhost:11434"
    max_retries: int = 3
    timeout_seconds: int = 3600
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

class ConfigManager:
    """Manages configuration loading and saving."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(Path.home(), ".storage_scraper_config.json")
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Config:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded config from {self.config_path}")
                return Config(**data)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}. Using defaults.")

        # Create default config
        config = Config()
        self._save_config(config)
        return config

    def _save_config(self, config: Config):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config.model_dump(), f, indent=2)
            logger.info(f"Saved config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get_config(self) -> Config:
        """Get current configuration."""
        return self.config

    def update_config(self, **kwargs):
        """Update configuration with new values."""
        data = self.config.model_dump()
        data.update(kwargs)
        self.config = Config(**data)
        self._save_config(self.config)

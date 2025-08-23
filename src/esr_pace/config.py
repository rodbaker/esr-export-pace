"""Configuration management for ESR Export Pace tracker."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CommodityConfig:
    """Individual commodity configuration"""
    code: int
    name: str
    enabled: bool
    unit_id: int

@dataclass
class AppConfig:
    """Main application configuration"""
    commodities: List[CommodityConfig]
    base_url: str
    log_level: str
    max_retries: int
    retry_delay: float
    request_timeout: int

class ConfigManager:
    """Load and manage application configuration"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config: Optional[AppConfig] = None
    
    def load_config(self) -> AppConfig:
        """Load configuration from YAML files and environment variables"""
        if self._config is None:
            # Load commodities
            commodities_data = self._load_yaml("commodities.yaml")
            commodities = [
                CommodityConfig(**c) for c in commodities_data.get("commodities", [])
            ]
            
            # Load environment variables with defaults
            base_url = os.getenv("BASE_URL", "https://api.fas.usda.gov")
            log_level = os.getenv("LOG_LEVEL", "INFO")
            max_retries = int(os.getenv("MAX_RETRIES", "3"))
            retry_delay = float(os.getenv("RETRY_DELAY", "1.0"))
            request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
            
            self._config = AppConfig(
                commodities=commodities,
                base_url=base_url,
                log_level=log_level,
                max_retries=max_retries,
                retry_delay=retry_delay,
                request_timeout=request_timeout
            )
        
        return self._config
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file"""
        file_path = self.config_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_enabled_commodities(self) -> List[CommodityConfig]:
        """Get list of enabled commodities"""
        config = self.load_config()
        return [c for c in config.commodities if c.enabled]

# Global config instance
config_manager = ConfigManager()

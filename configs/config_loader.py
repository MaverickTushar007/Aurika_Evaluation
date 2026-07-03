# configs/config_loader.py
"""
Central configuration loader for the Restaurant Analytics system.
Loads development, benchmark, and production YAML profiles.
"""

import os
import yaml

class ConfigLoader:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigLoader, cls).__new__(cls, *args, **kwargs)
            cls._instance.config = {}
        return cls._instance

    def load_config(self, profile_name: str = "production"):
        """Loads configuration from YAML file based on profile name."""
        possible_paths = [
            f"configs/{profile_name}.yaml",
            os.path.join(os.path.dirname(__file__), f"{profile_name}.yaml"),
            os.path.join(os.path.dirname(__file__), "..", "configs", f"{profile_name}.yaml")
        ]
        
        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
                
        if not config_path:
            raise FileNotFoundError(f"Configuration profile '{profile_name}' not found at any of {possible_paths}")
            
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        return self.config

    def get(self, key: str, default=None):
        """Retrieves a top-level key from loaded configuration."""
        return self.config.get(key, default)

    def get_nested(self, section: str, key: str, default=None):
        """Retrieves nested configurations (e.g. tracker parameters)."""
        section_data = self.config.get(section)
        if isinstance(section_data, dict):
            return section_data.get(key, default)
        return default

from pydantic_settings import BaseSettings
from typing import Dict, Any
import yaml
import os

class Settings(BaseSettings):
    gemini_api_key: str
    database_url: str
    redis_url: str
    ar_assets_path: str
    
    class Config:
        env_file = ".env"

def load_config(config_path: str = "config/development.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    # Replace environment variables
    for key, value in config.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                if isinstance(subvalue, str) and subvalue.startswith("${") and subvalue.endswith("}"):
                    env_var = subvalue[2:-1]
                    config[key][subkey] = os.getenv(env_var, "")
    
    return config

settings = Settings()
config = load_config()

from typing import List, Optional
import yaml
from pydantic import BaseModel, Field


class ConnectionConfig(BaseModel):
    hosts: List[str] = Field(default=["localhost"])
    port: int = Field(default=9200)
    use_ssl: bool = Field(default=True)
    verify_certs: bool = Field(default=True)


class AuthConfig(BaseModel):
    type: str = Field(default="basic")
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None


class AppSettings(BaseModel):
    history_dir: str = Field(default="history_dsl")
    app_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    json_logs: bool = Field(default=False)


class Settings(BaseModel):
    connection: ConnectionConfig = Field(default_factory=ConnectionConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    settings: AppSettings = Field(default_factory=AppSettings)


_settings_instance: Optional[Settings] = None


def load_settings(config_path: str = "user-config.yaml") -> Settings:
    global _settings_instance
    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        _settings_instance = Settings(**config_data)
    except FileNotFoundError:
        # Fallback to defaults if file not found, or raise error?
        # Given the requirement, we should probably warn or fail, but for now let's return defaults
        print(f"Warning: Config file {config_path} not found. Using defaults.")
        _settings_instance = Settings()
    except Exception as e:
        print(f"Error loading config: {e}")
        raise e

    return _settings_instance


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        return load_settings()
    return _settings_instance

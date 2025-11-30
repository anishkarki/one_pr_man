from unittest.mock import patch, mock_open
from opensearch_management.config import load_settings


def test_load_settings_defaults():
    with patch("builtins.open", side_effect=FileNotFoundError):
        settings = load_settings("non_existent.yaml")
        assert settings.connection.hosts == ["localhost"]
        assert settings.connection.port == 9200
        assert settings.auth.type == "basic"


def test_load_settings_from_yaml():
    yaml_content = """
connection:
  hosts: 
    - "test-host"
  port: 8888
  use_ssl: false
auth:
  type: "token"
  token: "secret"
settings:
  app_env: "prod"
"""
    with patch("builtins.open", mock_open(read_data=yaml_content)):
        settings = load_settings("config.yaml")
        assert settings.connection.hosts == ["test-host"]
        assert settings.connection.port == 8888
        assert settings.connection.use_ssl is False
        assert settings.auth.type == "token"
        assert settings.auth.token == "secret"
        assert settings.settings.app_env == "prod"

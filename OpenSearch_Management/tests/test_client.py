import pytest
from unittest.mock import Mock, patch, mock_open
from opensearch_management.client import OpenSearchClient
from opensearch_management.config import (
    Settings,
    ConnectionConfig,
    AuthConfig,
    AppSettings,
)


@pytest.fixture
def mock_settings():
    settings = Settings(
        connection=ConnectionConfig(
            hosts=["localhost"], port=9200, use_ssl=True, verify_certs=False
        ),
        auth=AuthConfig(type="basic", username="admin", password="admin"),
        settings=AppSettings(
            history_dir="test_history",
            app_env="test",
            log_level="INFO",
            json_logs=False,
        ),
    )
    return settings


@pytest.fixture
def client(mock_settings):
    return OpenSearchClient(settings=mock_settings)


def test_client_init(client, mock_settings):
    assert client.base_url == "https://localhost:9200"
    assert client.auth == ("admin", "admin")
    assert client.verify_certs is False


@patch("requests.request")
def test_client_get_success(mock_request, client):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"test": "data"}
    mock_request.return_value = mock_response

    response = client.get("test-index")

    assert response == {"test": "data"}
    mock_request.assert_called_once_with(
        method="GET",
        url="https://localhost:9200/test-index",
        auth=("admin", "admin"),
        json=None,
        params=None,
        headers={"Content-Type": "application/json"},
        verify=False,
        timeout=30,
    )


@patch("requests.request")
def test_client_dry_run(mock_request, mock_settings):
    client = OpenSearchClient(settings=mock_settings, dry_run=True)

    response = client.get("test-index")

    assert response == {}
    mock_request.assert_not_called()


@patch("opensearch_management.client.open", new_callable=mock_open)
@patch("opensearch_management.client.os.makedirs")
@patch("requests.request")
def test_client_query_history(mock_request, mock_makedirs, mock_file, mock_settings):
    client = OpenSearchClient(settings=mock_settings, query_history=True)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_request.return_value = mock_response

    client.get("test-index")

    # Check if directory was created
    mock_makedirs.assert_called_with("test_history", exist_ok=True)

    # Check if file was written
    mock_file.assert_called()
    handle = mock_file()
    handle.write.assert_called()

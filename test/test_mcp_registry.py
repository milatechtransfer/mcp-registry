import json
import os
from pathlib import Path

import pytest
import requests


@pytest.fixture(scope="session")
def local_registry_path():
    """Provide the path to the local registry JSON file."""
    return Path(__file__).resolve().parents[1] / "v0.1" / "servers" / "index.json"


@pytest.fixture(scope="session")
def api_url():
    """Optional live API URL for integration checks."""
    return os.getenv("MCP_REGISTRY_API_URL")


@pytest.fixture(scope="session")
def expected_server_names():
    """Provide a list of expected server names in the registry."""
    return ["github", "comet-mcp"]


@pytest.fixture(scope="session")
def registry_data(api_url, local_registry_path):
    """Load registry JSON from local file by default, or from API when configured."""

    if api_url:
        response = requests.get(api_url, timeout=10)
        assert response.status_code == 200, f"Registry not found at {api_url}"

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            pytest.fail("The registry response is not valid JSON. Check for trailing commas!")

    assert local_registry_path.exists(), f"Local registry file not found: {local_registry_path}"
    try:
        return json.loads(local_registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        pytest.fail("The local registry file is not valid JSON. Check for trailing commas!")


def test_registry_structure(registry_data):
    """Verify the registry JSON has the expected structure."""

    assert "servers" in registry_data, "Root 'servers' key missing in registry JSON."
    assert isinstance(registry_data["servers"], list), "'servers' value must be an array."


def test_server_existence(registry_data, expected_server_names):
    """Check that the server names are as expected."""
    actual_server_names = [
        item.get("server", {}).get("name") 
        for item in registry_data["servers"]
    ]
    
    assert set(expected_server_names) == set(actual_server_names), \
        f"Expected server names {expected_server_names} do not match actual {actual_server_names}."

def test_cors_headers(api_url):
    """Check that the file is served with CORS enabled."""
    if not api_url:
        pytest.skip("Set MCP_REGISTRY_API_URL to run CORS checks against a live endpoint.")
    
    headers = {"Origin": "https://vscode.dev"}
    response = requests.options(api_url, headers=headers)
    assert response.headers.get("Access-Control-Allow-Origin") == "*" or \
           requests.get(api_url).headers.get("Access-Control-Allow-Origin") == "*", \
           "CORS headers missing. VS Code may block this registry."
    
def test_json_header(api_url):
    if not api_url:
        pytest.skip("Set MCP_REGISTRY_API_URL to run Content-Type checks against a live endpoint.")

    response = requests.get(api_url)
    content_type = response.headers.get("Content-Type", "")
    assert "application/json" in content_type, \
        f"Expected application/json header, but got {content_type}. VS Code might ignore the file."
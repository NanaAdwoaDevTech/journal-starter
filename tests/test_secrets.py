"""Tests for the AWS Secrets Manager loader. boto3 is always mocked."""

import json
import os
from typing import Any
from unittest.mock import MagicMock

import pytest

from api import secrets

TOUCHED = [
    "SECRETS_SOURCE",
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "DATABASE_URL_SECRET_ID",
    "OPENAI_SECRET_ID",
]
DB_URL = "postgresql://user:pw@db.example:5432/journal"
OPENAI_JSON = json.dumps(
    {"api_key": "test-key", "base_url": "https://api.example/v1", "model": "test-model"}
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test without these variables and restore them afterwards."""
    for name in TOUCHED:
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)


def install_client(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> MagicMock:
    client = MagicMock()

    def get_secret_value(**kwargs: Any) -> dict[str, str]:
        return {"SecretString": values[kwargs["SecretId"]]}

    client.get_secret_value.side_effect = get_secret_value
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(secrets.boto3, "client", factory)
    return factory


def test_does_nothing_when_switch_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = install_client(monkeypatch, {})
    secrets.load_secrets_from_aws()
    factory.assert_not_called()
    assert "DATABASE_URL" not in os.environ


def test_loads_all_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "aws")
    install_client(monkeypatch, {"journal/database-url": DB_URL, "journal/openai": OPENAI_JSON})
    secrets.load_secrets_from_aws()
    assert os.environ["DATABASE_URL"] == DB_URL
    assert os.environ["OPENAI_API_KEY"] == "test-key"
    assert os.environ["OPENAI_BASE_URL"] == "https://api.example/v1"
    assert os.environ["OPENAI_MODEL"] == "test-model"


def test_trims_whitespace_around_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "aws")
    install_client(
        monkeypatch, {"journal/database-url": DB_URL + "\n", "journal/openai": OPENAI_JSON}
    )
    secrets.load_secrets_from_aws()
    assert os.environ["DATABASE_URL"] == DB_URL


def test_custom_secret_names_are_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "aws")
    monkeypatch.setenv("DATABASE_URL_SECRET_ID", "other/db")
    monkeypatch.setenv("OPENAI_SECRET_ID", "other/openai")
    install_client(monkeypatch, {"other/db": DB_URL, "other/openai": OPENAI_JSON})
    secrets.load_secrets_from_aws()
    assert os.environ["DATABASE_URL"] == DB_URL


def test_missing_openai_key_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "aws")
    payload = json.dumps({"api_key": "test-key", "base_url": "https://api.example/v1"})
    install_client(monkeypatch, {"journal/database-url": DB_URL, "journal/openai": payload})
    with pytest.raises(RuntimeError, match="model"):
        secrets.load_secrets_from_aws()


def test_invalid_json_error_does_not_echo_the_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "aws")
    install_client(
        monkeypatch, {"journal/database-url": DB_URL, "journal/openai": "not json at all"}
    )
    with pytest.raises(RuntimeError) as info:
        secrets.load_secrets_from_aws()
    assert "not valid JSON" in str(info.value)
    assert "not json at all" not in str(info.value)


def test_aws_failure_hides_details(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "aws")
    client = MagicMock()
    client.get_secret_value.side_effect = ValueError("leaky-detail")
    monkeypatch.setattr(secrets.boto3, "client", MagicMock(return_value=client))
    with pytest.raises(RuntimeError) as info:
        secrets.load_secrets_from_aws()
    assert "journal/database-url" in str(info.value)
    assert "leaky-detail" not in str(info.value)


def test_empty_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_SOURCE", "aws")
    install_client(monkeypatch, {"journal/database-url": "", "journal/openai": OPENAI_JSON})
    with pytest.raises(RuntimeError, match="no string value"):
        secrets.load_secrets_from_aws()

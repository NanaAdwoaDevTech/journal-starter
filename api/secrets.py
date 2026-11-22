"""Load application secrets from AWS Secrets Manager at startup.

Active only when SECRETS_SOURCE=aws, so local development with a .env file
and the test suite are unaffected. In the cluster, boto3 finds its credentials
through EKS Pod Identity, so no keys are stored anywhere. Secret values are
never logged, and error messages name only the secret ID.
"""

import json
import os
from typing import Any

import boto3

SOURCE_VARIABLE = "SECRETS_SOURCE"
DATABASE_ID_VARIABLE = "DATABASE_URL_SECRET_ID"
OPENAI_ID_VARIABLE = "OPENAI_SECRET_ID"
DEFAULT_DATABASE_ID = "journal/database-url"
DEFAULT_OPENAI_ID = "journal/openai"
OPENAI_KEYS = {
    "api_key": "OPENAI_API_KEY",
    "base_url": "OPENAI_BASE_URL",
    "model": "OPENAI_MODEL",
}


def _read_secret(client: Any, secret_id: str) -> str:
    try:
        response = client.get_secret_value(SecretId=secret_id)
    except Exception as exc:
        raise RuntimeError(f"Could not read secret {secret_id}: {type(exc).__name__}") from exc
    value = response.get("SecretString")
    if not value:
        raise RuntimeError(f"Secret {secret_id} has no string value")
    return str(value)


def load_secrets_from_aws() -> None:
    """Copy the vault secrets into the environment that Settings reads."""
    if os.environ.get(SOURCE_VARIABLE, "").strip().lower() != "aws":
        return

    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client("secretsmanager", region_name=region)

    database_id = os.environ.get(DATABASE_ID_VARIABLE, DEFAULT_DATABASE_ID)
    os.environ["DATABASE_URL"] = _read_secret(client, database_id).strip()

    openai_id = os.environ.get(OPENAI_ID_VARIABLE, DEFAULT_OPENAI_ID)
    try:
        openai_values = json.loads(_read_secret(client, openai_id))
    except ValueError as exc:
        raise RuntimeError(f"Secret {openai_id} is not valid JSON") from exc

    missing = [key for key in OPENAI_KEYS if not openai_values.get(key)]
    if missing:
        raise RuntimeError(f"Secret {openai_id} is missing keys: {', '.join(missing)}")
    for key, variable in OPENAI_KEYS.items():
        os.environ[variable] = str(openai_values[key])

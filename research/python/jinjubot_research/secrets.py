from __future__ import annotations

import json
from typing import Any

import boto3

_SECRET_CACHE: dict[str, dict[str, str]] = {}


def _extract_secret_string(secret_response: dict[str, Any]) -> str:
    secret_string = secret_response.get("SecretString")
    if isinstance(secret_string, str) and secret_string.strip():
        return secret_string

    raise ValueError("Secrets Manager secret must contain a non-empty SecretString.")


def _normalize_access_secret(secret_payload: dict[str, Any]) -> dict[str, str]:
    client_id = secret_payload.get("client_id")
    client_secret = secret_payload.get("client_secret")

    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError("Secret must contain a non-empty 'client_id' value.")

    if not isinstance(client_secret, str) or not client_secret.strip():
        raise ValueError("Secret must contain a non-empty 'client_secret' value.")

    return {
        "client_id": client_id.strip(),
        "client_secret": client_secret.strip(),
    }


def get_cloudflare_access_secret(secret_arn: str) -> dict[str, str]:
    cached = _SECRET_CACHE.get(secret_arn)
    if cached:
        return cached

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    payload = json.loads(_extract_secret_string(response))
    normalized = _normalize_access_secret(payload)
    _SECRET_CACHE[secret_arn] = normalized
    return normalized

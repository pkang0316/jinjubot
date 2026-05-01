from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import boto3


def _to_dynamodb_value(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, list):
        return [_to_dynamodb_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_dynamodb_value(item) for key, item in value.items()}
    return value


def put_json(bucket_name: str, key: str, payload: dict[str, Any]) -> None:
    s3_client = boto3.client("s3")
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=f"{json.dumps(payload, indent=2)}\n".encode("utf-8"),
        ContentType="application/json",
    )


def put_items(table_name: str, items: list[dict[str, Any]]) -> None:
    table = boto3.resource("dynamodb").Table(table_name)
    with table.batch_writer(overwrite_by_pkeys=["item_id"]) as batch:
        for item in items:
            batch.put_item(
                Item=_to_dynamodb_value({
                    "item_id": item["id"],
                    "category": item["category"],
                    **item,
                })
            )


def ensure_source_definitions(table_name: str, source_definitions: list[dict[str, Any]]) -> None:
    table = boto3.resource("dynamodb").Table(table_name)
    for source in source_definitions:
        source_id = str(source["source_id"])
        current = table.get_item(Key={"source_id": source_id}).get("Item") or {}
        merged = dict(current)
        merged.setdefault("source_id", source_id)
        for key, value in source.items():
            merged.setdefault(key, value)
        merged.setdefault("source_kind", "discovery_source")
        merged.setdefault("enabled", True)
        table.put_item(Item=_to_dynamodb_value(merged))


def list_active_sources(table_name: str) -> list[dict[str, Any]]:
    table = boto3.resource("dynamodb").Table(table_name)
    items: list[dict[str, Any]] = []
    response = table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    active_sources: list[dict[str, Any]] = []
    required_fields = {
        "source_id",
        "label",
        "category",
        "listing_url",
        "extract_strategy",
        "source_type",
        "candidate_strategy",
        "source_name",
        "allowed_domains",
        "max_candidate_urls",
        "max_follow_up_pages",
    }

    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("source_kind", "discovery_source") != "discovery_source":
            continue
        if item.get("enabled", True) is False:
            continue
        if not required_fields.issubset(set(item.keys())):
            continue
        active_sources.append(item)

    return sorted(active_sources, key=lambda source: str(source.get("source_id", "")))


def upsert_source_status(table_name: str, source_id: str, payload: dict[str, Any]) -> None:
    table = boto3.resource("dynamodb").Table(table_name)
    expression_names = {"#source_kind": "source_kind"}
    expression_values: dict[str, Any] = {":source_kind": "discovery_source"}
    assignments = ["#source_kind = if_not_exists(#source_kind, :source_kind)"]

    for index, (key, value) in enumerate(payload.items(), start=1):
        name_key = f"#n{index}"
        value_key = f":v{index}"
        expression_names[name_key] = key
        expression_values[value_key] = _to_dynamodb_value(value)
        assignments.append(f"{name_key} = {value_key}")

    table.update_item(
        Key={"source_id": source_id},
        UpdateExpression=f"SET {', '.join(assignments)}",
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values,
    )

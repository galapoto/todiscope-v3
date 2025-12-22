from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any


class ParseError(Exception):
    pass


def _decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ParseError("DECODE_FAILED") from e


def _parse_json(text: str) -> list[dict[str, Any]]:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise ParseError("JSON_INVALID") from e
    if isinstance(obj, dict) and isinstance(obj.get("records"), list):
        obj = obj["records"]
    if not isinstance(obj, list):
        raise ParseError("JSON_EXPECTED_LIST")
    out: list[dict[str, Any]] = []
    for item in obj:
        if not isinstance(item, dict):
            raise ParseError("JSON_ITEM_NOT_OBJECT")
        out.append(item)
    return out


def _parse_ndjson(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise ParseError("NDJSON_INVALID") from e
        if not isinstance(obj, dict):
            raise ParseError("NDJSON_ITEM_NOT_OBJECT")
        out.append(obj)
    if not out:
        raise ParseError("RECORDS_REQUIRED")
    return out


def _parse_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ParseError("CSV_NO_HEADER")
    out: list[dict[str, Any]] = []
    for row in reader:
        out.append({k: v for k, v in row.items()})
    if not out:
        raise ParseError("RECORDS_REQUIRED")
    return out


def parse_records(*, filename: str | None, content_type: str | None, content: bytes) -> list[dict[str, Any]]:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    text = _decode_text(content)

    if name.endswith(".ndjson") or "application/x-ndjson" in ctype:
        return _parse_ndjson(text)
    if name.endswith(".csv") or "text/csv" in ctype:
        return _parse_csv(text)
    if name.endswith(".json") or "application/json" in ctype or not ctype:
        return _parse_json(text)

    raise ParseError("FORMAT_UNSUPPORTED")


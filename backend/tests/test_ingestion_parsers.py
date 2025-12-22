from __future__ import annotations

from backend.app.core.ingestion.parsers import parse_records
from backend.app.core.normalization.pipeline import normalize_payload


def test_parse_csv_and_normalize() -> None:
    csv_bytes = b"source_system,source_record_id,Some Field\nsys,r1,  Value  \n"
    records = parse_records(filename="x.csv", content_type="text/csv", content=csv_bytes)
    assert records == [{"source_system": "sys", "source_record_id": "r1", "Some Field": "  Value  "}]

    normalized = normalize_payload(records[0])
    assert isinstance(normalized, dict)
    assert normalized["source_system"] == "sys"
    assert normalized["source_record_id"] == "r1"
    assert normalized["some_field"] == "  Value  "

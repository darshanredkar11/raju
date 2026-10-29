import json
from pathlib import Path


def test_rfq_schema_is_valid_json_and_allows_partial_intake():
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "rfq-intake.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["type"] == "object"
    assert schema["required"] == ["source_channel"]
    assert schema["additionalProperties"] is False
    assert "product" in schema["properties"]
    assert "verification" in schema["properties"]
    assert "current_availability_verified" in schema["properties"]["verification"]["properties"]

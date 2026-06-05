import pytest
from pydantic import BaseModel
from backend.app.llm.schema_validation import validate_json

class SimpleModel(BaseModel):
    name: str
    age: int

def test_validate_json_valid():
    text = '{"name": "Alice", "age": 30}'
    result = validate_json(text, SimpleModel)
    assert result.name == "Alice"
    assert result.age == 30

def test_validate_json_repairable():
    text = '```json\n{"name": "Bob", "age": 25,}\n```'
    result = validate_json(text, SimpleModel)
    assert result.name == "Bob"
    assert result.age == 25

def test_validate_json_invalid_json():
    text = '{"name": "Alice", "age": }'
    with pytest.raises(ValueError, match="Failed to parse repaired JSON"):
        validate_json(text, SimpleModel)

def test_validate_json_schema_mismatch():
    text = '{"name": "Alice"}'
    with pytest.raises(ValueError, match="fails schema validation"):
        validate_json(text, SimpleModel)

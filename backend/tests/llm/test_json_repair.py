import pytest
from backend.app.llm.json_repair import repair_json
import json

def test_repair_json_markdown():
    text = "```json\n{\"test\": 123}\n```"
    repaired = repair_json(text)
    assert json.loads(repaired) == {"test": 123}

def test_repair_json_trailing_comma():
    text = '{"test": 123, "list": [1, 2, 3, ], }'
    repaired = repair_json(text)
    assert json.loads(repaired) == {"test": 123, "list": [1, 2, 3]}

def test_repair_json_clean():
    text = '{"a": "b"}'
    repaired = repair_json(text)
    assert json.loads(repaired) == {"a": "b"}

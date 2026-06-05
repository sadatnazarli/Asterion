import json
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from app.llm.json_repair import repair_json

T = TypeVar("T", bound=BaseModel)

def validate_json(text: str, model_class: Type[T]) -> T:
    """
    Attempt to repair the JSON string and parse it into a Pydantic model.
    """
    repaired_text = repair_json(text)
    try:
        data = json.loads(repaired_text)
        return model_class.model_validate(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse repaired JSON: {e}\nRepaired text: {repaired_text}") from e
    except ValidationError as e:
        raise ValueError(f"JSON matches format but fails schema validation for {model_class.__name__}: {e}") from e

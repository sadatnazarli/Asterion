import pytest
from unittest.mock import MagicMock
from backend.app.llm.audit import log_model_call
from sqlalchemy.engine import Connection

def test_log_model_call():
    conn = MagicMock(spec=Connection)
    
    # Mock scalar to return a dummy ID
    result_mock = MagicMock()
    result_mock.scalar.return_value = 42
    conn.execute.return_value = result_mock
    
    call_id = log_model_call(
        conn=conn,
        task="test_task",
        model="test_model",
        prompt_version="v1",
        input_text="hello",
        output_text='{"response": "world"}',
        latency_ms=100,
        status="success"
    )
    
    assert call_id == 42
    assert conn.execute.call_count == 2  # One for model_calls, one for llm_outputs

def test_log_model_call_error():
    conn = MagicMock(spec=Connection)
    
    result_mock = MagicMock()
    result_mock.scalar.return_value = 43
    conn.execute.return_value = result_mock
    
    call_id = log_model_call(
        conn=conn,
        task="test_task",
        model="test_model",
        prompt_version="v1",
        input_text="hello",
        output_text=None,
        latency_ms=100,
        status="failed",
        error="Something went wrong"
    )
    
    assert call_id == 43
    assert conn.execute.call_count == 1  # Only model_calls, no llm_outputs if output_text is None

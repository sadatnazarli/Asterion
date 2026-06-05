import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import text
from sqlalchemy.engine import Connection

def log_model_call(
    conn: Connection,
    task: str,
    model: str,
    prompt_version: str,
    input_text: str,
    output_text: Optional[str],
    latency_ms: int,
    status: str,
    error: Optional[str] = None
) -> int:
    """
    Log an LLM API call to the database.
    
    Calculates SHA256 hashes of input and output text for auditing.
    
    Args:
        conn: SQLAlchemy database connection.
        task: Description of the task being performed.
        model: Name of the LLM model used.
        prompt_version: Version of the prompt template used.
        input_text: The exact text sent to the model.
        output_text: The exact text returned by the model.
        latency_ms: Request latency in milliseconds.
        status: Call status ('success', 'failed', etc.).
        error: Optional error message if the call failed.
        
    Returns:
        The ID of the inserted model_call record.
    """
    
    input_hash = None
    if input_text is not None:
        input_hash = hashlib.sha256(input_text.encode("utf-8")).hexdigest()
        
    output_hash = None
    if output_text is not None:
        output_hash = hashlib.sha256(output_text.encode("utf-8")).hexdigest()
        
    # Check schema valid heuristically by trying to parse output as json if it looks like one, 
    # but for now we default to None.
    schema_valid = None
    if output_text is not None and output_text.strip().startswith("{"):
        try:
            json.loads(output_text)
            schema_valid = True
        except ValueError:
            schema_valid = False

    call_insert_query = text("""
        INSERT INTO model_calls (
            task, model_name, prompt_version, input_hash, 
            latency_ms, status, error, created_at
        ) VALUES (
            :task, :model_name, :prompt_version, :input_hash, 
            :latency_ms, :status, :error, :created_at
        ) RETURNING id
    """)
    
    result = conn.execute(
        call_insert_query,
        {
            "task": task,
            "model_name": model,
            "prompt_version": prompt_version,
            "input_hash": input_hash,
            "latency_ms": latency_ms,
            "status": status,
            "error": error,
            "created_at": datetime.now(timezone.utc)
        }
    )
    
    model_call_id = result.scalar()
    
    if output_text is not None or output_hash is not None:
        output_insert_query = text("""
            INSERT INTO llm_outputs (
                model_call_id, raw_output, output_hash, schema_valid
            ) VALUES (
                :model_call_id, :raw_output, :output_hash, :schema_valid
            )
        """)
        
        conn.execute(
            output_insert_query,
            {
                "model_call_id": model_call_id,
                "raw_output": output_text,
                "output_hash": output_hash,
                "schema_valid": schema_valid
            }
        )
        
    return model_call_id

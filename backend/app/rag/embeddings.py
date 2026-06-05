import json
import logging
from typing import Any, Dict, List

from psycopg.errors import DatatypeMismatch, UndefinedColumn

from app.llm.ollama_provider import embed_texts

logger = logging.getLogger(__name__)

def generate_embeddings(chunks: List[Dict[str, Any]], model: str = "nomic-embed-text") -> List[Dict[str, Any]]:
    """
    Takes a list of chunks, generates embeddings for the 'text' field, 
    and adds an 'embedding' key to each chunk.
    If Ollama is unavailable, logs a warning and returns chunks without embeddings.
    """
    if not chunks:
        return chunks

    texts = [chunk.get("text", "") for chunk in chunks]
    
    try:
        embeddings = embed_texts(texts, model=model)
        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb
    except Exception as e:
        logger.warning(f"Ollama unavailable or embedding generation failed: {e}. Returning chunks without embeddings.")

    return chunks

def store_chunks(conn, chunks: List[Dict[str, Any]]) -> None:
    """
    Writes chunks into the `document_chunks` table.
    Gracefully handles if pgvector or embedding column is missing.
    """
    if not chunks:
        return
        
    for chunk in chunks:
        has_embedding = "embedding" in chunk and chunk["embedding"] is not None
        
        # Prepare data for insertion (convert list to JSON string for pgvector parsing if needed)
        columns = list(chunk.keys())
        values = []
        for k in columns:
            if k == "embedding" and isinstance(chunk[k], list):
                values.append(json.dumps(chunk[k]))
            else:
                values.append(chunk[k])
        
        col_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO document_chunks ({col_str}) VALUES ({placeholders})"
        
        try:
            with conn.transaction():
                conn.execute(query, values)
        except (UndefinedColumn, DatatypeMismatch, Exception) as e:
            # If insertion fails and chunk has embedding, try again without embedding
            # In psycopg3, the transaction block acts as a savepoint context manager, 
            # so the outer transaction can continue.
            error_msg = str(e)
            if has_embedding and ("embedding" in error_msg or isinstance(e, (UndefinedColumn, DatatypeMismatch))):
                logger.warning(f"Failed to insert chunk with embedding, trying without it: {e}")
                
                # Retry without embedding
                cols_no_emb = [k for k in chunk.keys() if k != "embedding"]
                vals_no_emb = [chunk[k] for k in cols_no_emb]
                col_str_no = ", ".join(cols_no_emb)
                pl_no = ", ".join(["%s"] * len(cols_no_emb))
                query_no = f"INSERT INTO document_chunks ({col_str_no}) VALUES ({pl_no})"
                
                try:
                    with conn.transaction():
                        conn.execute(query_no, vals_no_emb)
                except Exception as e2:
                    logger.error(f"Failed to insert chunk even without embedding: {e2}")
                    raise
            else:
                logger.error(f"Failed to insert chunk: {e}")
                raise

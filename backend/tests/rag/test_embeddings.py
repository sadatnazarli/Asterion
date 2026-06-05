import pytest
from unittest.mock import patch, MagicMock
from psycopg.errors import UndefinedColumn

from app.rag.embeddings import generate_embeddings, store_chunks

@patch("app.rag.embeddings.embed_texts")
def test_generate_embeddings_success(mock_embed):
    mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
    chunks = [{"text": "Hello"}, {"text": "World"}]
    
    result = generate_embeddings(chunks)
    
    assert len(result) == 2
    assert result[0]["embedding"] == [0.1, 0.2]
    assert result[1]["embedding"] == [0.3, 0.4]

@patch("app.rag.embeddings.embed_texts")
def test_generate_embeddings_failure(mock_embed):
    mock_embed.side_effect = Exception("Ollama is down")
    chunks = [{"text": "Hello"}]
    
    # Should handle gracefully and return chunks without embeddings
    result = generate_embeddings(chunks)
    
    assert len(result) == 1
    assert "embedding" not in result[0]

def test_store_chunks_empty():
    mock_conn = MagicMock()
    store_chunks(mock_conn, [])
    mock_conn.execute.assert_not_called()

def test_store_chunks_success():
    mock_conn = MagicMock()
    # Mock context manager for transaction
    mock_conn.transaction.return_value.__enter__.return_value = MagicMock()
    
    chunks = [{"text": "Hello", "embedding": [0.1, 0.2]}]
    store_chunks(mock_conn, chunks)
    
    # Should have been called once with json string for the list
    assert mock_conn.execute.call_count == 1
    args, kwargs = mock_conn.execute.call_args
    assert "INSERT INTO document_chunks" in args[0]
    assert "[0.1, 0.2]" in args[1] or args[1] == ["Hello", "[0.1, 0.2]"] or args[1] == ["[0.1, 0.2]", "Hello"]

def test_store_chunks_missing_column():
    mock_conn = MagicMock()
    mock_conn.transaction.return_value.__enter__.return_value = MagicMock()
    
    # Simulate first insert failing with UndefinedColumn (e.g. embedding doesn't exist)
    def side_effect(query, values):
        if "embedding" in query:
            raise UndefinedColumn("column 'embedding' of relation 'document_chunks' does not exist")
    
    mock_conn.execute.side_effect = side_effect
    
    chunks = [{"text": "Hello", "embedding": [0.1, 0.2]}]
    store_chunks(mock_conn, chunks)
    
    # Should be called twice. First fails, second succeeds without embedding
    assert mock_conn.execute.call_count == 2
    args, kwargs = mock_conn.execute.call_args
    assert "INSERT INTO document_chunks (text) VALUES (%s)" in args[0]
    assert args[1] == ["Hello"]

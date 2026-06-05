import pytest
from unittest.mock import patch, MagicMock

from app.llm.ollama_provider import embed_texts

def test_embed_texts_empty():
    assert embed_texts([]) == []

@patch("app.llm.ollama_provider.Client")
def test_embed_texts_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.embeddings.side_effect = [
        {"embedding": [0.1, 0.2]},
        {"embedding": [0.3, 0.4]}
    ]
    
    texts = ["Hello", "World"]
    embeddings = embed_texts(texts)
    
    assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
    assert mock_client.embeddings.call_count == 2
    mock_client.embeddings.assert_any_call(model="nomic-embed-text", prompt="Hello")
    mock_client.embeddings.assert_any_call(model="nomic-embed-text", prompt="World")

@patch("app.llm.ollama_provider.Client")
def test_embed_texts_failure(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.embeddings.side_effect = Exception("Ollama is down")
    
    with pytest.raises(Exception, match="Ollama is down"):
        embed_texts(["Test text"])

from app.llm.ollama_provider import generate_chat
from pydantic import BaseModel

class DummyResponse(BaseModel):
    response: str

@patch("app.llm.ollama_provider.Client")
def test_generate_chat_basic(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.chat.return_value = {"message": {"content": "Hello world"}}
    
    result = generate_chat(prompt="Hi", system="Sys")
    assert result == {"message": {"content": "Hello world"}}

@patch("app.llm.ollama_provider.Client")
def test_generate_chat_with_model(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.chat.return_value = {"message": {"content": '{"response": "Hello"}'}}
    
    result = generate_chat(prompt="Hi", system="Sys", response_model=DummyResponse)
    assert isinstance(result, DummyResponse)
    assert result.response == "Hello"

@patch("app.llm.ollama_provider.Client")
def test_generate_chat_retry_failure(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.chat.side_effect = Exception("Connection refused")
    
    with pytest.raises(RuntimeError, match="Failed to connect to Ollama"):
        generate_chat(prompt="Hi", system="Sys", max_retries=2)
    
    assert mock_client.chat.call_count == 2

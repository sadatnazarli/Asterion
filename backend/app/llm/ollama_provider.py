import logging
from typing import List, Type, Optional, Union, Dict, Any
from pydantic import BaseModel
from ollama import Client

from app.llm.schema_validation import validate_json

logger = logging.getLogger(__name__)

def embed_texts(texts: List[str], model: str = "nomic-embed-text") -> List[List[float]]:
    """
    Generate embeddings for a list of texts using local Ollama instance.
    
    Args:
        texts: A list of string texts to embed.
        model: The model name to use for embedding (default: nomic-embed-text).
        
    Returns:
        A list of embedding vectors (list of floats).
    """
    if not texts:
        return []

    client = Client(host='http://localhost:11434')
    
    embeddings = []
    for text in texts:
        try:
            # We use the embeddings API from ollama python client
            response = client.embeddings(model=model, prompt=text)
            embeddings.append(response.get('embedding', []))
        except Exception as e:
            logger.error(f"Failed to generate embedding for text using model {model}: {e}")
            raise
    
    return embeddings

def generate_chat(
    prompt: str,
    system: str,
    model: str = "qwen2.5:7b-instruct",
    max_retries: int = 3,
    response_model: Optional[Type[BaseModel]] = None
) -> Union[Dict[str, Any], BaseModel]:
    """
    Generate a chat completion using local Ollama instance.
    
    Args:
        prompt: The user prompt.
        system: The system prompt.
        model: The model name to use.
        max_retries: Number of retries on failure.
        response_model: Optional Pydantic model to parse the response into.
        
    Returns:
        The raw response dict or the parsed Pydantic model.
    """
    client = Client(host='http://localhost:11434')
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ]
    
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "options": {"temperature": 0.0}
    }
    
    if response_model is not None:
        kwargs["format"] = "json"
        
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            response = client.chat(**kwargs)
            
            if response_model is not None:
                content = response.get("message", {}).get("content", "")
                return validate_json(content, response_model)
                
            return response
            
        except Exception as e:
            last_exception = e
            logger.warning(f"Ollama chat generation failed on attempt {attempt + 1}/{max_retries}: {e}")
            
    logger.error("Ollama chat generation failed after max retries.")
    if last_exception:
        # Check if it looks like a connection error
        if "Connection" in str(last_exception) or "ConnectError" in str(last_exception):
            raise RuntimeError(
                f"Failed to connect to Ollama. Is it running? Error: {last_exception}"
            ) from last_exception
        raise last_exception
    
    raise RuntimeError("Failed to generate chat completion.")

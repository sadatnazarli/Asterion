#!/usr/bin/env python3
import argparse
import sys
import os

# Add the backend directory to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.db.session import get_connection
from app.rag.hybrid_search import hybrid_search
from app.llm.ollama_provider import embed_texts
import logging

logging.basicConfig(level=logging.WARNING)

def main():
    parser = argparse.ArgumentParser(description="Test RAG hybrid search via CLI.")
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument("--ticker", type=str, help="Filter by ticker symbol (e.g., PLTR)", default=None)
    parser.add_argument("--top-k", type=int, help="Number of results to return", default=5)
    
    args = parser.parse_args()
    
    print(f"Searching for: '{args.query}' (Ticker: {args.ticker})")
    
    filters = {}
    if args.ticker:
        filters["ticker"] = args.ticker
        
    try:
        with get_connection() as conn:
            # Generate query embedding using local Ollama model
            try:
                embeddings = embed_texts([args.query])
                query_embedding = embeddings[0] if embeddings else None
            except Exception as e:
                print(f"Warning: Failed to generate query embedding ({e}). Falling back to BM25-only search.", file=sys.stderr)
                query_embedding = None
            
            results = hybrid_search(
                conn=conn,
                query=args.query,
                query_embedding=query_embedding,
                filters=filters,
                top_k=args.top_k
            )
            
            if not results:
                print("\nNo results found.")
                return
                
            print(f"\nFound {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"--- Result {i} (Score: {result.score:.4f}) ---")
                print(result.to_formatted_string())
                print()
                
    except Exception as e:
        print(f"Error executing search: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

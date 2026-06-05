-- Asterion 0007 — pgvector embeddings for document_chunks.
-- Adds the embedding column (vector 768) if pgvector is available.
-- Uses an EXCEPTION block so that local setups without pgvector don't fail,
-- gracefully degrading to keyword search only.

DO $$
BEGIN
    -- Try to add the vector column
    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(768);
    RAISE NOTICE 'Added embedding column to document_chunks';
    
    -- Create an index for vector similarity search (HNSW is best for pgvector 0.5.0+, ivfflat otherwise)
    -- We'll use HNSW with cosine distance if possible.
    CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);
    RAISE NOTICE 'Created HNSW index on document_chunks.embedding';
    
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'pgvector is not available or failed to configure. document_chunks will not store embeddings. Error: %', SQLERRM;
END $$;

-- Asterion 0008 — M4 LLM Audit additions.
-- Adds tracking columns to model_calls and llm_outputs for hallucination auditing.

ALTER TABLE model_calls ADD COLUMN IF NOT EXISTS input_hash TEXT;
ALTER TABLE model_calls ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'success';
ALTER TABLE model_calls ADD COLUMN IF NOT EXISTS error TEXT;

ALTER TABLE llm_outputs ADD COLUMN IF NOT EXISTS output_hash TEXT;

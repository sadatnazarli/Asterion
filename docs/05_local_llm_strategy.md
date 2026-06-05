# 05 — Local LLM Strategy

Trace: `MASTER_PLAN.md` §8, `00_..._requirements.md` §2 (LLM is the analyst, not
the oracle). Primary runtime for this build: **Ollama**.

---

## 1. Hard Rules (apply to every model below)

- LLM **never** calculates a financial ratio, price, or score.
- LLM may: summarize filing sections, extract risk factors, compare management
  tone, explain a deterministic scorecard, draft bull/bear, apply investor lenses,
  write memos, propose monitoring triggers.
- **Every output is strict JSON**, schema-validated, retried, JSON-repaired.
- **Every numeric token** in an output is audited: if it is not present in the
  structured data or the evidence pack, it is flagged as a possible hallucination.
- Every call logs: model name, prompt version, tokens in/out, latency, temperature.

## 2. Model Evaluation (local options)

Ratings are qualitative for finance-doc extraction + JSON reliability on a
solo-dev machine. "JSON" = reliability of strict structured output.

| Model | Sizes | Ctx | Reasoning | JSON | Finance docs | Speed | Mem (Q4) | Best use | Weakness |
|-------|-------|-----|-----------|------|--------------|-------|----------|----------|----------|
| **Qwen2.5 / Qwen3** | 7/14/32B | 32–128k | High | **Excellent** | Strong | Med | ~5/9/20GB | committee reasoning, extraction, JSON | larger sizes need RAM |
| **Llama 3.1/3.3** | 8/70B | 128k | Med–High | Good | Good | Med | ~5/40GB | general summarize, memo | 8B reasoning ceiling; 70B heavy |
| **Mistral / Mistral-Nemo** | 7/12B | 32–128k | Med | Good | Med | Fast | ~5/7GB | fast summarize, drafts | weaker multi-step reasoning |
| **DeepSeek-R1 (distill)** | 7/14/32B | 64k+ | **High (CoT)** | Med | Med | Slow | ~5/9/20GB | bull/bear debate, forensic reasoning | verbose CoT; must constrain to JSON |
| **Phi-4** | 14B | 16k | Med–High | Good | Med | Fast | ~9GB | cheap reasoning on 16GB | short context limits long filings |
| **Gemma 2** | 9/27B | 8k | Med | Good | Med | Med | ~6/16GB | summarize | small context |
| **nomic-embed-text** | 137M | 8k | — | — | — | Fast | <1GB | embeddings | embed-only |
| **bge-m3 / bge-large** | 0.3–0.6B | 8k | — | — | — | Fast | ~1–2GB | embeddings, multilingual | embed-only |

## 3. Recommended MVP Setup (Ollama)

```
# reasoning / committee (default)
ollama pull qwen2.5:7b-instruct          # primary, fits 16GB
ollama pull qwen2.5:14b-instruct         # upgrade on 24GB+

# heavy forensic / debate (optional, 24GB+)
ollama pull deepseek-r1:14b

# fast drafts / summaries
ollama pull mistral-nemo:12b             # optional

# embeddings
ollama pull nomic-embed-text             # default embedder
```

**Defaults written into config:**
- `ASTERION_LLM_MODEL=qwen2.5:7b-instruct`
- `ASTERION_LLM_REASONING_MODEL=qwen2.5:14b-instruct` (falls back to primary)
- `ASTERION_EMBED_MODEL=nomic-embed-text`
- `ASTERION_EMBED_DIM=768`  (nomic-embed-text dimension; pgvector column sized to match)

Rationale: Qwen2.5-Instruct is the strongest open model for **strict JSON +
extraction** at sizes that fit a normal machine, which matters more here than raw
chat quality. DeepSeek-R1 is reserved for tasks that genuinely benefit from chain
-of-thought (bull/bear debate, forensic narrative) but is constrained to emit JSON.

## 4. Task → Model Routing

| Task | Default model | Temp | Notes |
|------|---------------|------|-------|
| Summarize filing section | primary 7B | 0.2 | grounded, cite sections |
| Extract risk factors | primary 7B | 0.0 | JSON list + char spans |
| Compare mgmt tone (Q/Q) | reasoning 14B | 0.3 | needs two evidence sets |
| Explain scorecard | primary 7B | 0.2 | numbers come from scores, not model |
| Bull / Bear case | reasoning / R1 | 0.4 | debate; every claim cited |
| Investor lens analysis | reasoning 14B | 0.3 | lens JSON + evidence |
| Final investment memo | reasoning 14B | 0.3 | consumes scores+evidence only |
| Trade setup memo | primary 7B | 0.2 | walled; experimental label |
| Monitoring triggers | primary 7B | 0.2 | deterministic-friendly JSON |
| Embeddings | nomic-embed-text | — | RAG |

Router (`llm/router.py`) picks by task name; falls back to primary if reasoning
model unavailable.

## 5. Reliability Mechanisms

1. **Strict JSON** — request `format=json` (Ollama) / response_format json; provide
   a JSON schema in the prompt; set low temperature for extraction.
2. **Schema validation** — pydantic models per task; reject + retry on failure.
3. **JSON repair** (`llm/json_repair.py`) — fix trailing commas, code fences,
   truncation before re-parsing; one repair attempt before a model retry.
4. **Retries** — N attempts with backoff; escalate to reasoning model on final try.
5. **Timeouts** — per-call wall clock; long filings chunked first.
6. **Hallucination audit** — extract every number/percentage from output, check
   presence in evidence pack / structured inputs; unmatched → `flagged_numbers`.
7. **Citation audit** — every claim must reference a chunk id / data field;
   uncited claims downgraded.
8. **Logging** — `model_calls`, `llm_outputs`, `hallucination_audits` tables.

## 6. Provider Abstraction

`provider_base.ChatProvider` interface → `OllamaProvider` (native API) and
`OpenAICompatibleLocalProvider` (LM Studio / llama.cpp / vLLM). External cloud
provider only if `ASTERION_ALLOW_EXTERNAL_LLM=true` (default false). Same
interface everywhere; swapping backends is a config change.

## 7. Fallback Philosophy

If local reasoning proves insufficient for the **final memo only**, the external
fallback flag exists — but determinism, scores, extraction, and citations stay
local. The fallback never computes numbers; it only rephrases grounded inputs.
The system is fully usable (scores + evidence + decision) with the LLM layer
disabled entirely (`ASTERION_LLM_ENABLED=false`) — memos just become templated.

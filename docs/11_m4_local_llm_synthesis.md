# M4: Local LLM Synthesis Layer

The M4 milestone introduces the agentic synthesis layer to Asterion. It orchestrates a suite of specialized LLM sub-analysts to review deterministic M2 financial ratios alongside M3 qualitative SEC RAG chunks, ultimately generating an institutional-grade, evidence-backed company memo.

## What Was Implemented

1. **LLM Provider Layer (`app.llm.ollama_provider`)**
   - Seamless local execution utilizing Ollama (`qwen2.5:7b-instruct`).
   - Implemented strict JSON mode for analyst agents.
   - Built-in retry loops and timeout logic for robustness.
   - Detailed, fail-fast error reporting if models are not pulled locally.

2. **JSON Repair & Validation (`app.llm.schema_validation` & `json_repair`)**
   - Pydantic schema constraints.
   - Auto-repair for common LLM JSON serialization bugs (e.g. trailing commas, stray markdown blocks).

3. **Audit Trails (`app.llm.audit` & Migrations)**
   - SQL Migration `0008` expanded `model_calls` and `llm_outputs` tables.
   - Every local LLM execution is deterministically logged with hashed inputs, outputs, models, and latency.

4. **Hallucination Audit (`app.llm.hallucination_audit`)**
   - After the LLM generates a memo, an aggressive regex cross-checks *every single number* against the raw Evidence Pack. 
   - If a number appears in the LLM text but was not in the underlying data, the auditor flags it as suspicious.

5. **Multi-Agent Framework (`app.analysis.agents`)**
   - **5 Sub-Analysts** run concurrently: Financial Ratio Explainer, Filing Risk Analyst, Bull Analyst, Bear Analyst, Forensic Accountant.
   - The Lead Analyst Agent combines their outputs into a cohesive final markdown memo.
   - All prompts strictly forbid: invented numbers, "buy/sell" language, and price targets.

## Setup Instructions

Ensure you have Ollama running locally.

```bash
# Pull the required models
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

## How to Run

To run the full end-to-end multi-agent pipeline and generate a memo:

```bash
cd backend
.venv/bin/python ../scripts/generate_company_memo.py PLTR
```

To just build the deterministic Evidence Pack without calling Ollama (Dry Run):

```bash
cd backend
.venv/bin/python ../scripts/generate_company_memo.py PLTR --dry-run
```

## Known Weaknesses & Limitations

- **Hallucination Audit limitations:** The regex engine might catch dates (like "2026") or standard text figures (like "10-K") and flag them if they don't perfectly align with the data hashes.
- **Model Hardware Bounds:** Running 6 LLM queries sequentially (or concurrently) requires high RAM/VRAM. The concurrent execution might OOM lower-tier machines, in which case the script should be modified to run the agents serially.

## Next Step: M5

M5 will focus on building the Decision Policy Layer: creating deterministic rules that take the grounded memo and structured analyst red flags, and synthesize them into defined portfolio allocation limits, entirely bypassing "black-box" LLM judgments.

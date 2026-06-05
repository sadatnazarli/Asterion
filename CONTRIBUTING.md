# Contributing to Asterion

Thanks for your interest. Asterion is a local-first research tool — contributions
that improve correctness, data honesty, and developer experience are welcome.

## Run locally

```bash
git clone <your-fork-url> Asterion && cd Asterion
cp .env.example .env
cp backend/.env.example backend/.env        # all API keys optional

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python ../scripts/migrate.py                # needs local Postgres 16

cd ../frontend && npm install && cd ..
make start                                   # backend :8000 + frontend :3000
```

## Run tests

```bash
# Backend (pytest)
cd backend && .venv/bin/python -m pytest tests/

# Frontend (build must pass)
cd frontend && npm run build

# Health check (servers must be running)
make health
```

Add or update tests for any behavior change. Backend tests live in
`backend/tests/`.

## Coding standards

- **Python** — type hints, small pure functions, deterministic math kept out of
  the LLM layer. Match the style of the surrounding module.
- **TypeScript** — keep components typed; don't break `npm run build`.
- **Determinism** — financial ratios, multiples, and valuations are computed in
  code, never by an LLM. The LLM explains; it does not calculate.
- **Data honesty** — missing data must be surfaced as missing and must lower
  confidence. Never fabricate a number to fill a gap.

## Hard rules

- **No secrets in commits.** Never commit `.env`, API keys, tokens, real
  portfolio data, generated private reports, logs, or local machine paths. Use
  `*.example` templates and `examples/` sample data only.
- **No buy/sell recommendation language.** Asterion does not tell users to buy or
  sell. Outputs are research signals with confidence, risk, and invalidation
  conditions — keep wording neutral and evidence-based.
- **Cite the source.** Every number should trace to a SEC fact, price bar, or
  named provider.

## Pull requests

1. Branch off `main`.
2. Keep changes focused; describe what and why.
3. Ensure backend tests and `npm run build` pass.
4. Confirm `git status` shows no secret or personal files staged.

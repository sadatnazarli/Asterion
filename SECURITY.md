# Security Policy

## Secrets policy

- **Never commit `.env` files.** Only `*.example` templates belong in git.
  `.env`, `backend/.env`, and `frontend/.env.local` are gitignored — keep it that
  way.
- **Never commit** API keys, tokens, broker/portfolio data, generated private
  reports, logs, local caches, or local machine paths.
- All provider keys (`FINNHUB_API_KEY`, `FMP_API_KEY`, `FRED_API_KEY`,
  `POLYGON_API_KEY`, `OPENFIGI_API_KEY`) are **optional**; Asterion degrades to
  stored/fallback data without them.
- Tooling that prints provider status (e.g. `make health`) reports only whether a
  key is **configured** — it never prints key values.

## If you find a secret in the repo

1. Treat the key as compromised and **rotate it immediately** at the provider.
2. Remove it from the working tree and from git history.
3. Do not paste the secret into issues, logs, or PRs.

## Reporting a vulnerability

Please report security issues **privately** — open a GitHub Security Advisory
(Security → Report a vulnerability) on the repository, or contact the maintainer
directly. Do not open a public issue for undisclosed vulnerabilities.

We aim to acknowledge reports promptly and will coordinate a fix and disclosure
timeline with you.

## Scope notes

- Asterion is local-first; by default no data is sent to external services.
- External LLM usage is **off by default** (`ASTERION_ALLOW_EXTERNAL_LLM=false`).
- SEC EDGAR ingestion requires a real email in the User-Agent (SEC policy) — this
  is the user's own email, set in their local `.env`, never committed.

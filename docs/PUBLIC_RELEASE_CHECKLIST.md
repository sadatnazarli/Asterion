# Public Release Checklist

Run through this before making the repository public or cutting a release.

## Secrets & privacy

- [ ] No secrets tracked: `git ls-files | grep -E "env|key|token|secret"` returns
      only `*.example` files.
- [ ] `.env`, `backend/.env`, `frontend/.env.local` are gitignored and untracked.
- [ ] No personal email, name, or local machine paths in tracked files.
- [ ] No real portfolio data (`real_portfolio.csv`, `my_portfolio.csv`) tracked.
- [ ] No generated private reports (`portfolio_report.*`, `my_real_portfolio_report.*`,
      `portfolio_coverage.*`) tracked — `reports/` is gitignored.
- [ ] No screenshots containing private holdings/values tracked — `screenshots/`
      is gitignored.
- [ ] No logs or local caches tracked (`logs/`, `data/cache/`).
- [ ] Git history scanned — no secret was ever committed.

## Public-safe samples present

- [ ] `.env.example` and `backend/.env.example` exist with empty placeholders.
- [ ] `examples/sample_portfolio.csv` exists with fake demo holdings.
- [ ] `examples/reports/` contains only sanitized public-company demo reports.

## Build & tests

- [ ] Backend tests pass: `cd backend && .venv/bin/python -m pytest tests/`.
- [ ] Frontend builds: `cd frontend && npm run build`.
- [ ] `make health` is green/yellow (not red) with servers running.

## Docs

- [ ] `README.md` rendered correctly (logo, disclaimer, quickstart, license).
- [ ] `LICENSE` present (AGPL-3.0).
- [ ] `CONTRIBUTING.md` and `SECURITY.md` present.
- [ ] Disclaimer states Asterion is **not financial advice** and issues no
      buy/sell recommendations.

## Final

- [ ] `git status` clean (no stray private files staged).
- [ ] Commit message describes the release prep.
- [ ] Do not push until explicitly approved.

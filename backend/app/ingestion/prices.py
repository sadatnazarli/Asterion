"""Daily OHLCV ingestion — provider interface + free Stooq fallback.

No paid API dependency in M1. The default provider is Stooq (free CSV, no key).
Design goals:
  * swappable: implement ``PriceProvider`` for any source (Alpaca/Polygon later);
  * non-blocking: a price failure must never abort SEC ingestion — callers treat
    ``fetch_daily`` failures as soft (log + continue).

This module fetches + parses only. Persistence into prices_daily is the caller's
job (bootstrap). No LLM, no computed numbers — raw vendor OHLCV only.
"""
from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

import httpx
import pandas as pd
import yfinance as yf

from app.core.config import settings


@dataclass(slots=True)
class OHLCV:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adj_close: float | None
    volume: int | None


class PriceProvider(Protocol):
    name: str

    def fetch_daily(self, ticker: str, start: date | None = None, end: date | None = None) -> list[OHLCV]: ...


class StooqProvider:
    """Free daily OHLCV from Stooq CSV. US symbols use the '.us' suffix.

    Endpoint: https://stooq.com/q/d/l/?s=<sym>.us&i=d
    Returns columns: Date,Open,High,Low,Close,Volume (no adjusted close — we mirror
    close into adj_close and flag the limitation in docs).
    """

    name = "stooq"
    BASE = "https://stooq.com/q/d/l/"

    def __init__(self, timeout_s: float = 20.0) -> None:
        self._timeout = timeout_s

    def _symbol(self, ticker: str) -> str:
        t = ticker.strip().lower()
        return t if "." in t else f"{t}.us"

    def fetch_daily(self, ticker: str, start: date | None = None, end: date | None = None) -> list[OHLCV]:
        url = f"{self.BASE}?s={self._symbol(ticker)}&i=d"
        with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
            resp = client.get(url)
        if resp.status_code != 200:
            raise PriceError(f"stooq HTTP {resp.status_code} for {ticker}")
        text = resp.text.strip()
        if not text or text.lower().startswith("<"):  # html error page
            raise PriceError(f"stooq returned no CSV for {ticker}")
        rows: list[OHLCV] = []
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or "Date" not in reader.fieldnames:
            # stooq emits "No data" as a single line for unknown/limited symbols
            raise PriceError(f"stooq no data for {ticker}: {text[:60]!r}")
        for r in reader:
            try:
                d = datetime.strptime(r["Date"], "%Y-%m-%d").date()
                if start and d < start:
                    continue
                if end and d > end:
                    continue
            except (ValueError, KeyError):
                continue
            close = _f(r.get("Close"))
            rows.append(
                OHLCV(
                    date=d,
                    open=_f(r.get("Open")),
                    high=_f(r.get("High")),
                    low=_f(r.get("Low")),
                    close=close,
                    adj_close=close,  # stooq close is already split/div-adjusted
                    volume=_i(r.get("Volume")),
                )
            )
        return rows


class PriceError(RuntimeError):
    pass


class YFinanceProvider:
    name = "yfinance"

    def fetch_daily(self, ticker: str, start: date | None = None, end: date | None = None) -> list[OHLCV]:
        try:
            kwargs = {}
            if start:
                kwargs["start"] = start.strftime("%Y-%m-%d")
            if end:
                kwargs["end"] = end.strftime("%Y-%m-%d")
                
            t = yf.Ticker(ticker)
            df = t.history(auto_adjust=False, **kwargs)
            if df.empty:
                raise PriceError(f"yfinance returned no data for {ticker}")
                
            rows: list[OHLCV] = []
            for date_idx, row in df.iterrows():
                try:
                    d = date_idx.date()
                    c = float(row["Close"])
                    ac = float(row.get("Adj Close", c))
                    rows.append(
                        OHLCV(
                            date=d,
                            open=float(row["Open"]),
                            high=float(row["High"]),
                            low=float(row["Low"]),
                            close=c,
                            adj_close=ac,
                            volume=int(row["Volume"])
                        )
                    )
                except (ValueError, KeyError, TypeError):
                    continue
            return rows
        except Exception as e:
            raise PriceError(f"yfinance failed for {ticker}: {e}")


class CSVProvider:
    """Manual CSV ingestion from data/prices/TICKER.csv"""
    name = "csv"

    def fetch_daily(self, ticker: str, start: date | None = None, end: date | None = None) -> list[OHLCV]:
        path = os.path.join(settings.data_dir, "prices", f"{ticker.upper()}.csv")
        if not os.path.exists(path):
            raise PriceError(f"CSV not found: {path}")
            
        rows: list[OHLCV] = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "Date" not in reader.fieldnames:
                raise PriceError(f"CSV invalid format for {ticker}")
            for r in reader:
                try:
                    d = datetime.strptime(r["Date"], "%Y-%m-%d").date()
                    if start and d < start:
                        continue
                    if end and d > end:
                        continue
                except (ValueError, KeyError):
                    continue
                c = _f(r.get("Close"))
                ac = _f(r.get("Adj Close")) or c
                rows.append(
                    OHLCV(
                        date=d,
                        open=_f(r.get("Open")),
                        high=_f(r.get("High")),
                        low=_f(r.get("Low")),
                        close=c,
                        adj_close=ac,
                        volume=_i(r.get("Volume")),
                    )
                )
        if not rows:
            raise PriceError(f"CSV had no valid rows for {ticker}")
        return rows


class FallbackProvider:
    name = "fallback"
    
    def __init__(self, providers: list[PriceProvider]) -> None:
        self.providers = providers
        
    def fetch_daily(self, ticker: str, start: date | None = None, end: date | None = None) -> list[OHLCV]:
        errors = []
        for p in self.providers:
            try:
                return p.fetch_daily(ticker, start, end)
            except Exception as e:
                errors.append(f"{p.name}: {e}")
        raise PriceError(f"All providers failed for {ticker}. Errors: " + " | ".join(errors))


def get_price_provider(name: str | None = None) -> PriceProvider:
    """Factory — returns the configured provider."""
    provider = (name or settings.prices_provider or "fallback").lower()
    if provider == "stooq":
        return StooqProvider()
    elif provider == "yfinance":
        return YFinanceProvider()
    elif provider == "csv":
        return CSVProvider()
    elif provider in ("fallback", "auto"):
        return FallbackProvider([YFinanceProvider(), StooqProvider(), CSVProvider()])
        
    raise PriceError(f"price provider {provider!r} not available")


def _f(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "", "N/A") else None
    except ValueError:
        return None


def _i(v: str | None) -> int | None:
    f = _f(v)
    return int(f) if f is not None else None

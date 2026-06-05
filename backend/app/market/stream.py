"""Finnhub WebSocket quote stream with polling fallback."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FINNHUB_WS_URL = "wss://ws.finnhub.io"
POLL_INTERVAL_S = 45
RECONNECT_BASE_S = 2
RECONNECT_MAX_S = 60


def us_market_open(now: datetime | None = None) -> bool:
    now = now or datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:
        return False
    open_at = now.replace(hour=9, minute=30, second=0, microsecond=0)
    close_at = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_at <= now <= close_at


def normalize_tick(
    ticker: str,
    price: float,
    *,
    provider: str,
    is_realtime: bool,
    change_pct: float | None = None,
) -> dict:
    tick = {
        "type": "quote_tick",
        "ticker": ticker.upper(),
        "price": round(float(price), 4),
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "provider": provider,
        "is_realtime": is_realtime,
    }
    if change_pct is not None:
        tick["change_pct"] = round(float(change_pct), 4)
    return tick


def stream_status_event(
    status: str,
    provider: str,
    message: str = "",
) -> dict:
    return {
        "type": "stream_status",
        "status": status,
        "provider": provider,
        "message": message,
        "market_open": us_market_open(),
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


class QuoteStreamHub:
    """Broadcasts quote ticks to browser WebSocket clients."""

    def __init__(self) -> None:
        self._clients: dict[asyncio.Queue, set[str]] = {}
        self._tickers: set[str] = set()
        self._upstream_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self.latest_quotes: dict[str, dict] = {}
        self.tick_count = 0
        self.last_tick_at: datetime | None = None
        self.connection_status = "disconnected"
        self.active_provider = "none"
        self.status_message = ""

    async def register(self, tickers: list[str]) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        normalized = {t.upper() for t in tickers if t.strip()}
        self._clients[queue] = normalized
        self._tickers |= normalized
        await self._ensure_upstream()
        await queue.put(stream_status_event(self.connection_status, self.active_provider, self.status_message))
        for ticker in normalized:
            cached = self.latest_quotes.get(ticker)
            if cached:
                await queue.put(cached)
        return queue

    async def unregister(self, queue: asyncio.Queue) -> None:
        self._clients.pop(queue, None)
        if not self._clients:
            await self._stop_upstream()

    async def _ensure_upstream(self) -> None:
        if self._upstream_task and not self._upstream_task.done():
            return
        self._upstream_task = asyncio.create_task(self._run_upstream())

    async def _stop_upstream(self) -> None:
        if self._upstream_task:
            self._upstream_task.cancel()
            try:
                await self._upstream_task
            except asyncio.CancelledError:
                pass
            self._upstream_task = None
        self.connection_status = "disconnected"
        self.active_provider = "none"
        await self._broadcast_status("disconnected", "none", "No active subscribers")

    async def _run_upstream(self) -> None:
        if get_settings().finnhub_api_key:
            await self._run_finnhub_with_backoff()
        else:
            await self._run_polling("finnhub_key_missing")

    async def _run_finnhub_with_backoff(self) -> None:
        delay = RECONNECT_BASE_S
        while self._clients:
            try:
                await self._run_finnhub_ws()
                delay = RECONNECT_BASE_S
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Finnhub WS error: %s", exc)
                self.connection_status = "disconnected"
                await self._broadcast_status(
                    "disconnected",
                    "finnhub_ws",
                    f"Finnhub reconnecting: {exc}",
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_S)
        if self._clients:
            await self._run_polling("finnhub_ws_failed")

    async def _run_finnhub_ws(self) -> None:
        api_key = get_settings().finnhub_api_key
        assert api_key
        url = f"{FINNHUB_WS_URL}?token={api_key}"
        tickers = sorted(self._tickers)
        async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
            for ticker in tickers:
                await ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
            self.connection_status = "connected"
            self.active_provider = "finnhub_ws"
            msg = "Live Finnhub WebSocket connected"
            if not us_market_open():
                msg = "Market closed — Finnhub connected, last tick shown"
            self.status_message = msg
            await self._broadcast_status("connected", "finnhub_ws", msg)

            while self._clients:
                try:
                    raw = await asyncio.wait_for(
                        ws.recv(),
                        timeout=90 if not us_market_open() else 45,
                    )
                except asyncio.TimeoutError:
                    if not us_market_open():
                        await self._broadcast_status(
                            "connected",
                            "finnhub_ws",
                            "Market closed, last tick shown",
                        )
                        continue
                    break
                payload = json.loads(raw)
                if payload.get("type") != "trade":
                    continue
                for trade in payload.get("data") or []:
                    symbol = str(trade.get("s", "")).upper()
                    price = trade.get("p")
                    if not symbol or price is None:
                        continue
                    await self._emit_tick(
                        symbol,
                        float(price),
                        provider="finnhub_ws",
                        is_realtime=True,
                    )

    async def _run_polling(self, reason: str) -> None:
        from app.market.router import fetch_quote

        self.connection_status = "fallback"
        self.active_provider = "polling_fallback"
        if reason == "finnhub_key_missing":
            msg = (
                "Finnhub API key missing — set FINNHUB_API_KEY or ASTERION_FINNHUB_API_KEY in .env"
            )
        else:
            msg = "Polling fallback every 45s — not real-time streaming"
        if not us_market_open():
            msg = f"Market closed, last tick shown. {msg}"
        self.status_message = msg
        await self._broadcast_status("fallback", "polling_fallback", msg)

        while self._clients:
            for ticker in sorted(self._tickers):
                quote = fetch_quote(ticker)
                if quote and quote.get("c"):
                    await self._emit_tick(
                        ticker,
                        float(quote["c"]),
                        provider="polling_fallback",
                        is_realtime=False,
                        change_pct=quote.get("dp"),
                    )
            await asyncio.sleep(POLL_INTERVAL_S)

    async def _emit_tick(
        self,
        ticker: str,
        price: float,
        *,
        provider: str,
        is_realtime: bool,
        change_pct: float | None = None,
    ) -> None:
        tick = normalize_tick(
            ticker,
            price,
            provider=provider,
            is_realtime=is_realtime,
            change_pct=change_pct,
        )
        self.latest_quotes[ticker.upper()] = tick
        self.tick_count += 1
        self.last_tick_at = datetime.now(UTC)
        await self._broadcast(tick)

    async def _broadcast_status(self, status: str, provider: str, message: str) -> None:
        self.connection_status = status
        self.active_provider = provider
        self.status_message = message
        await self._broadcast(stream_status_event(status, provider, message))

    async def _broadcast(self, event: dict) -> None:
        dead: list[asyncio.Queue] = []
        for queue, tickers in list(self._clients.items()):
            if event.get("type") == "quote_tick" and event.get("ticker") not in tickers:
                continue
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(queue)
        for queue in dead:
            self._clients.pop(queue, None)

    def debug_state(self) -> dict:
        return {
            "connection_status": self.connection_status,
            "active_provider": self.active_provider,
            "status_message": self.status_message,
            "subscribed_tickers": sorted(self._tickers),
            "tick_count": self.tick_count,
            "last_tick_at": self.last_tick_at.isoformat().replace("+00:00", "Z")
            if self.last_tick_at
            else None,
            "market_open": us_market_open(),
            "finnhub_configured": bool(get_settings().finnhub_api_key),
        }


hub = QuoteStreamHub()

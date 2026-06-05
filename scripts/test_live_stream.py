"""Connect to backend quote WebSocket and print ticks."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    sys.exit(1)


async def main(ticker: str, host: str, timeout: float) -> int:
    url = f"{host}/ws/quotes?tickers={ticker.upper()}"
    print(f"Connecting to {url}")
    tick_count = 0
    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 5))
                except asyncio.TimeoutError:
                    continue
                event = json.loads(raw)
                print(json.dumps(event, indent=2))
                if event.get("type") == "quote_tick":
                    tick_count += 1
                if event.get("type") == "stream_status":
                    status = event.get("status")
                    msg = event.get("message", "")
                    if status == "fallback":
                        print(f"\nNote: {msg}")
                    if not event.get("market_open", True):
                        print("\nUS market appears closed — ticks may not arrive until open.")
            if tick_count == 0:
                print(f"\nNo quote ticks received in {timeout}s.")
                print("Possible reasons: market closed, Finnhub key missing, or symbol inactive.")
                return 1
            print(f"\nReceived {tick_count} tick(s).")
            return 0
    except Exception as exc:
        print(f"Connection failed: {exc}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Asterion live quote WebSocket")
    parser.add_argument("ticker", nargs="?", default="MSFT")
    parser.add_argument("--host", default="ws://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.ticker, args.host, args.timeout)))

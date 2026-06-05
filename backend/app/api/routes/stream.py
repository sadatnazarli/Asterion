"""WebSocket quote streaming routes."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.market.stream import hub

router = APIRouter()


@router.websocket("/ws/quotes")
async def ws_quotes(
    websocket: WebSocket,
    tickers: str = Query(default="MSFT,NVDA,PLTR,VOO,META"),
) -> None:
    await websocket.accept()
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        await websocket.send_json(
            {
                "type": "stream_status",
                "status": "disconnected",
                "provider": "none",
                "message": "No tickers requested",
            }
        )
        await websocket.close()
        return

    queue = await hub.register(ticker_list)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.unregister(queue)


@router.get("/api/system/stream-debug")
def stream_debug() -> dict:
    return hub.debug_state()

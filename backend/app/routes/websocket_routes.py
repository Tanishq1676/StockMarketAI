"""WebSocket endpoint (Phase 11): live market updates."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.ws_feed import build_update_payload

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/market-updates")
async def market_updates_ws(websocket: WebSocket):
    await websocket.accept()
    logger.info("ws client connected")
    try:
        while True:
            payload = await asyncio.to_thread(build_update_payload)
            try:
                await websocket.send_json(payload)
            except Exception as exc:
                logger.debug("ws send failed: %s", exc)
                break
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        logger.info("ws client disconnected")
    except Exception as exc:
        logger.warning("ws error: %s", exc)

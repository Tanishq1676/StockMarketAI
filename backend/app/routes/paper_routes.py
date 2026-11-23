"""Paper trading endpoints (Phase 9): simulated BUY/SELL orders."""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from ..paper.trading import paper_trading_service

router = APIRouter()


@router.get("/paper/wallet", tags=["paper_trading"])
def paper_wallet():
    return paper_trading_service.wallet_summary()


@router.post("/paper/order", tags=["paper_trading"])
def place_paper_order(
    symbol: str = Body(...),
    action: str = Body(...),
    qty: int = Body(...),
    entry_price: float = Body(None),
    stop_loss: float = Body(None),
    target: float = Body(None),
    fees_pct: float = Body(0.1),
):
    if action.upper() not in ("BUY", "SELL"):
        raise HTTPException(400, "action must be BUY or SELL")
    try:
        result = paper_trading_service.place_order(
            symbol=symbol.upper(),
            action=action.upper(),
            qty=qty,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            fees_pct=fees_pct,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return result


@router.get("/paper/trades", tags=["paper_trading"])
def paper_trades(limit: int = 50):
    return {"trades": paper_trading_service.get_trades(limit=limit)}


@router.get("/paper/stats", tags=["paper_trading"])
def paper_stats():
    return paper_trading_service.stats()



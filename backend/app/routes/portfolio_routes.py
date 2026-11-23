"""Portfolio management endpoints (Phase 9).

POST /api/portfolio/transaction  - record a buy or sell
GET  /api/portfolio/summary      - full auto-computed summary
GET  /api/portfolio/stocks/{sym} - per-stock performance
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Body, HTTPException

from ..portfolio.calculator import portfolio_service

router = APIRouter()


@router.post("/portfolio/transaction", tags=["portfolio"])
def add_transaction(
    symbol: str = Body(...),
    action: str = Body(...),
    qty: int = Body(...),
    price: float = Body(...),
    fees: float = Body(0.0),
    taxes: float = Body(0.0),
    other_fees: float = Body(0.0),
    transaction_date: Optional[str] = Body(None),
    user_id: Optional[int] = Body(None),
):
    if action.lower() not in ("buy", "sell"):
        raise HTTPException(400, "action must be 'buy' or 'sell'")
    if qty <= 0:
        raise HTTPException(400, "qty must be positive")
    txn = portfolio_service.add_transaction(
        symbol=symbol.upper(),
        action=action.lower(),
        qty=qty,
        price=price,
        fees=fees,
        taxes=taxes,
        other_fees=other_fees,
        transaction_date=transaction_date or date.today().isoformat(),
        user_id=user_id,
    )
    return {
        "id": txn.id,
        "symbol": txn.symbol,
        "action": txn.action,
        "qty": txn.qty,
        "price": txn.price,
        "total_cost": round(txn.total_cost + txn.fees + txn.taxes + txn.other_fees, 2),
        "fees": txn.fees,
        "taxes": txn.taxes,
        "date": txn.date,
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
    }


@router.get("/portfolio/summary", tags=["portfolio"])
def portfolio_summary():
    return portfolio_service.portfolio_summary()


@router.get("/portfolio/stocks/{symbol}", tags=["portfolio"])
def stock_performance(symbol: str):
    perf = portfolio_service.portfolio_summary()
    for s in perf["stocks"]:
        if s["symbol"] == symbol.upper():
            return s
    return {"symbol": symbol.upper(), "message": "no position in this symbol"}

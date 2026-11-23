"""Paper trading (simulated trading, Phase 9).

Maintains a virtual wallet (initial ₹1,00,000 by default) and simulates
BUY/SELL orders. Never executes real trades.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..config import PAPER_TRADING_INITIAL_BALANCE
from ..database import SessionLocal
from ..models import PaperPosition, PaperTrade
from ..data import providers


class PaperTradingService:
    def __init__(self, initial_balance: float = PAPER_TRADING_INITIAL_BALANCE):
        self._initial_balance = initial_balance

    # ------------------------------------------------------------------
    # Wallet
    # ------------------------------------------------------------------
    def wallet_summary(self) -> Dict:
        db = SessionLocal()
        try:
            positions = db.query(PaperPosition).all()
            trades = db.query(PaperTrade).all()
            balance = float(self._initial_balance)
            for t in trades:
                if t.action == "buy":
                    balance -= (t.price * t.qty) - (t.fees or 0)
                else:
                    balance += (t.price * t.qty) + (t.pnl or 0)
            open_pnl = sum(p["unrealised_pnl"] for p in [self._pos_dict(p) for p in positions])
            return {
                "initial_balance": round(float(self._initial_balance), 2),
                "wallet_balance": round(balance + open_pnl, 2),
                "open_positions_pnl": round(open_pnl, 2),
                "total_pnl": round(balance + open_pnl - float(self._initial_balance), 2),
                "total_trades": len(trades),
                "positions": [self._pos_dict(p) for p in positions],
            }
        finally:
            db.close()

    def _pos_dict(self, p: PaperPosition) -> Dict:
        try:
            cur = float(providers.get_quote(p.symbol).close)
        except Exception:
            cur = 0.0
        qty = p.qty
        unreal = (cur - p.avg_entry) * qty
        return {
            "symbol": p.symbol,
            "qty": qty,
            "avg_entry": round(p.avg_entry, 2),
            "current_price": round(cur, 2),
            "current_value": round(qty * cur, 2),
            "unrealised_pnl": round(unreal, 2),
            "unrealised_pct": round((unreal / (p.avg_entry * qty)) * 100, 3) if p.avg_entry else 0.0,
        }

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def _current_price(self, symbol: str) -> float:
        return float(providers.get_quote(symbol).close)

    def place_order(
        self,
        symbol: str,
        action: str,
        qty: int,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        fees_pct: float = 0.1,
    ) -> Dict:
        symbol = symbol.upper()
        qty = int(qty)
        if qty <= 0:
            raise ValueError("quantity must be positive")
        if action not in ("BUY", "SELL"):
            raise ValueError("action must be BUY or SELL")
        price = float(entry_price) if entry_price else self._current_price(symbol)

        db = SessionLocal()
        try:
            # Reconstruct balance: initial + net purchased + net sold + realized PnL
            trades_all = db.query(PaperTrade).all()
            balance = float(self._initial_balance)
            for t in trades_all:
                if t.action == "buy":
                    balance -= (t.price * t.qty) - (t.fees or 0)
                else:
                    balance += (t.price * t.qty) + (t.pnl or 0)
            if action == "BUY":
                fees = round(price * qty * fees_pct / 100.0, 2)
                if balance - (price * qty + fees) < -0.01:
                    raise ValueError("insufficient paper funds")
                # update/merge position
                pos = db.query(PaperPosition).filter(PaperPosition.symbol == symbol).first()
                if pos:
                    new_qty = pos.qty + qty
                    pos.avg_entry = (pos.avg_entry * pos.qty + price * qty) / new_qty if new_qty else 0.0
                    pos.qty = new_qty
                else:
                    db.add(PaperPosition(symbol=symbol, qty=qty, avg_entry=price))
                pnl = 0.0
            else:
                pos = db.query(PaperPosition).filter(PaperPosition.symbol == symbol).first()
                if not pos or pos.qty <= 0:
                    raise ValueError(f"no open position in {symbol}")
                if qty > pos.qty:
                    qty = pos.qty
                pnl = round((price - pos.avg_entry) * qty, 2)
                pos.qty -= qty
                if pos.qty <= 0:
                    db.delete(pos)
                fees = round(price * qty * fees_pct / 100.0, 2)

            trade = PaperTrade(
                symbol=symbol,
                action=action,
                qty=qty,
                price=price,
                pnl=pnl,
                fees=fees,
                executed_at=datetime.utcnow(),
            )
            db.add(trade)
            db.commit()
            new_balance = balance + (pnl if action == "SELL" else -(price * qty - fees))
            return {
                "order_id": f"PT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "symbol": symbol,
                "action": action,
                "qty": qty,
                "price": round(price, 2),
                "fees": fees,
                "pnl": pnl,
                "executed_at": datetime.utcnow().isoformat(),
                "wallet_balance": round(new_balance, 2),
                "stop_loss": stop_loss,
                "target": target,
            }
        except ValueError:
            db.rollback()
            raise
        finally:
            db.close()

    def get_trades(self, limit: int = 50) -> List[Dict]:
        db = SessionLocal()
        try:
            rows = db.query(PaperTrade).order_by(PaperTrade.executed_at.desc()).limit(limit).all()
            return [
                {
                    "symbol": r.symbol,
                    "action": r.action,
                    "qty": r.qty,
                    "price": round(r.price, 2),
                    "fees": round(r.fees or 0, 2),
                    "pnl": round(r.pnl or 0, 2),
                    "executed_at": r.executed_at.isoformat() if r.executed_at else None,
                }
                for r in rows
            ]
        finally:
            db.close()

    def stats(self) -> Dict:
        db = SessionLocal()
        try:
            trades = db.query(PaperTrade).all()
            sold = [t for t in trades if t.action == "SELL"]
            wins = sum(1 for t in sold if (t.pnl or 0) > 0)
            gross = sum(t.price * t.qty for t in sold)
            costs = sum(t.price * t.qty for t in trades if t.action == "BUY") + sum((t.fees or 0) for t in trades)
            pnl = round(sum((t.pnl or 0) for t in sold), 2)
            return {
                "total_trades": len(trades),
                "win_rate": round(wins / len(sold) * 100, 2) if sold else 0.0,
                "profit_factor": round(gross / costs, 3) if costs else 0.0,
                "total_pnl": pnl,
            }
        finally:
            db.close()


paper_trading_service = PaperTradingService()

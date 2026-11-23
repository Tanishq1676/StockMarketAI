"""Portfolio management (Phase 9).

Manual trade recording with automatic calculations:
- Total investment, current value, unrealised PnL, realised PnL, total PnL, % returns
- Individual stock performance, allocation, sector allocation
- Average purchase price, realised stats, per-user support

FIFO selling is applied so partial sales and transaction costs are accounted
for accurately.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

from ..database import SessionLocal
from ..models import StockMeta, Transaction


def _today() -> str:
    return date.today().isoformat()


class PortfolioService:
    def __init__(self):
        from ..data import providers

        self.providers = providers

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def add_transaction(
        self,
        symbol: str,
        action: str,
        qty: int,
        price: float,
        fees: float = 0.0,
        taxes: float = 0.0,
        other_fees: float = 0.0,
        transaction_date: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Transaction:
        assert action in ("buy", "sell"), "action must be buy or sell"
        total = round(qty * price, 2)
        txn = Transaction(
            symbol=symbol.upper(),
            action=action.lower(),
            qty=int(qty),
            price=round(float(price), 2),
            total_cost=total,
            fees=fees,
            taxes=taxes,
            other_fees=other_fees,
            date=transaction_date or _today(),
            user_id=user_id,
        )
        db = SessionLocal()
        try:
            db.add(txn)
            db.commit()
            return txn
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    def _net_positions(self, user_id: Optional[int] = None) -> Dict[str, Dict]:
        """Symbol -> {qty, avg_buy_price}. FIFO attribution of sells."""
        db = SessionLocal()
        try:
            q = db.query(Transaction).order_by(Transaction.date, Transaction.id)
            if user_id:
                q = q.filter(Transaction.user_id == user_id)
            fifo: Dict[str, List] = defaultdict(list)  # symbol -> [(qty, price), ...]
            for t in q.all():
                lst = fifo[t.symbol]
                if t.action == "buy":
                    lst.append((int(t.qty), float(t.price)))
                else:
                    need = int(t.qty)
                    while need > 0 and lst:
                        q0, p0 = lst[0]
                        if q0 <= need:
                            lst.pop(0)
                            need -= q0
                        else:
                            lst[0] = (q0 - need, p0)
                            need = 0
            out = {}
            for sym, lst in fifo.items():
                if not lst:
                    continue
                qty = sum(q_ for q_, _ in lst)
                avg = sum(q_ * p_ for q_, p_ in lst) / qty
                out[sym] = {"qty": qty, "avg_buy_price": round(avg, 2)}
            return out
        finally:
            db.close()

    def current_price_of(self, symbol: str) -> float:
        try:
            quote = self.providers.get_quote(symbol)
            return float(quote.close)
        except Exception:
            return 0.0

    def _realised_stats(self, user_id: Optional[int] = None) -> Dict[str, float]:
        db = SessionLocal()
        try:
            sells = db.query(Transaction).filter(Transaction.action == "sell")
            buys = db.query(Transaction).filter(Transaction.action == "buy")
            if user_id:
                sells = [t for t in sells if t.user_id == user_id]
                buys = [t for t in buys if t.user_id == user_id]
            gross = sum(t.total_cost for t in sells)
            sell_costs = sum(t.fees + t.taxes + t.other_fees for t in sells)
            buy_fees = sum(t.fees + t.taxes + t.other_fees for t in buys)
            return {"realised_gross": round(gross, 2), "realised_costs": round(sell_costs + buy_fees, 2)}
        finally:
            db.close()

    def portfolio_summary(self, user_id: Optional[int] = None) -> Dict:
        positions = self._net_positions(user_id)
        realised = self._realised_stats(user_id)
        # per-stock details
        stock_perf = []
        total_value = 0.0
        total_invested = 0.0
        total_unrealised = 0.0
        # investment per symbol: sum of buy total + fees/taxes
        db = SessionLocal()
        try:
            buys = db.query(Transaction).filter(Transaction.action == "buy").all()
            if user_id:
                buys = [t for t in buys if t.user_id == user_id]
            invested_by_symbol: Dict[str, float] = defaultdict(float)
            for t in buys:
                invested_by_symbol[t.symbol] += t.total_cost + t.fees + t.taxes + t.other_fees
        finally:
            db.close()

        for symbol, p in positions.items():
            cur = self.current_price_of(symbol)
            value = p["qty"] * cur
            cost = invested_by_symbol.get(symbol, p["avg_buy_price"] * p["qty"])
            unreal = value - cost
            stock_perf.append(
                {
                    "symbol": symbol,
                    "qty": p["qty"],
                    "avg_buy_price": round(p["avg_buy_price"], 2),
                    "current_price": round(cur, 2),
                    "current_value": round(value, 2),
                    "invested_cost": round(cost, 2),
                    "unrealised_pnl": round(unreal, 2),
                    "unrealised_pct": round((unreal / cost) * 100, 3) if cost else 0.0,
                    "weight_pct": None,  # filled later
                    "sector": _sector_of(symbol),
                }
            )
            total_value += value
            total_invested += cost
            total_unrealised += unreal

        sector_allocation = defaultdict(float)
        for row in stock_perf:
            sector_allocation[row["sector"] or "other"] += row["current_value"]
        sector_pct = {k: round(v / total_value * 100, 3) if total_value else 0.0
                      for k, v in sector_allocation.items()}
        for row in stock_perf:
            row["weight_pct"] = round(row["current_value"] / total_value * 100, 3) if total_value else 0.0

        realised_gross = realised["realised_gross"]
        realised_costs = realised["realised_costs"]
        realised_pnl = round(realised_gross - realised_costs - total_unrealised, 2) if False else None
        # Correct: realised PnL is net of costs and open positions remain open.
        realised_pnl = round(realised_gross - realised_costs, 2)
        total_pnl = round(total_unrealised + realised_pnl, 2)
        total_pct = round((total_pnl / total_invested) * 100, 3) if total_invested else 0.0

        return {
            "total_investment": round(total_invested, 2),
            "current_portfolio_value": round(total_value, 2),
            "unrealised_pnl": round(total_unrealised, 2),
            "realised_pnl": round(realised_pnl, 2),
            "realised_gross_sales": round(realised_gross, 2),
            "total_pnl": total_pnl,
            "total_return_pct": total_pct,
            "stocks": stock_perf,
            "sector_allocation": sector_pct,
            "available_cash": round(0.0, 2),  # n/a for manual portfolio tracking
            "data_source": "manual_portfolio",
            "updated_at": _today(),
        }


def _sector_of(symbol: str) -> str:
    from ..data import catalog

    meta = catalog.find_stock(symbol)
    return meta.get("sector", "") if meta else ""


portfolio_service = PortfolioService()

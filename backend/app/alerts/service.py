"""Alert & notification system (Phase 13).

Users can configure alerts for: price reaching levels, percentage moves,
unusual volume, AI signals, and important news/announcements. Fired alerts
are stored as notification records in the alerts table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..database import SessionLocal
from ..models import Alert, Signal

ALERT_CONDITIONS = (
    "price_above",
    "price_below",
    "pct_up",
    "pct_down",
    "volume_above",
    "volume_below",
    "ai_buy",
    "ai_sell",
)


class AlertsService:
    def create_alert(self, symbol: str, condition: str, threshold: float,
                     user_id: Optional[int] = None, note: str = "") -> Dict:
        assert condition in ALERT_CONDITIONS, f"unsupported condition {condition}"
        db = SessionLocal()
        try:
            alert = Alert(symbol=symbol.upper(), condition=condition, threshold=float(threshold),
                          status="active", user_id=user_id, created_at=datetime.utcnow())
            db.add(alert)
            db.commit()
            db.refresh(alert)
            return self._to_dict(alert)
        finally:
            db.close()

    def delete_alert(self, alert_id: int) -> bool:
        db = SessionLocal()
        try:
            row = db.query(Alert).filter(Alert.id == alert_id).first()
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True
        finally:
            db.close()

    def list_alerts(self, active_only: bool = False, user_id: Optional[int] = None) -> List[Dict]:
        db = SessionLocal()
        try:
            q = db.query(Alert).order_by(Alert.created_at.desc())
            if active_only:
                q = q.filter(Alert.status == "active")
            if user_id:
                q = q.filter(Alert.user_id == user_id)
            return [self._to_dict(a) for a in q.all()]
        finally:
            db.close()

    def dismiss(self, alert_id: int) -> bool:
        db = SessionLocal()
        try:
            row = db.query(Alert).filter(Alert.id == alert_id).first()
            if row and row.status == "fired":
                row.status = "dismissed"
                db.commit()
                return True
            return False
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(self, market_map: Dict[str, Dict]) -> List[Dict]:
        """Evaluate active alerts against a {symbol: quote-dict} snapshot."""
        db = SessionLocal()
        try:
            alerts = db.query(Alert).filter(Alert.status == "active").all()
            fired: List[Dict] = []
            for a in alerts:
                data = market_map.get(a.symbol)
                if not data:
                    continue
                cond = a.condition
                thr = float(a.threshold)
                close = float(data.get("price", data.get("price_close", 0)) or 0)
                pct = float(data.get("change_pct", 0) or 0)
                vol = float(data.get("volume", 0) or 0)
                tripped = False
                if cond == "price_above" and close >= thr:
                    tripped = True
                elif cond == "price_below" and close <= thr:
                    tripped = True
                elif cond == "pct_up" and pct >= thr:
                    tripped = True
                elif cond == "pct_down" and pct <= -abs(thr):
                    tripped = True
                elif cond == "volume_above" and vol >= thr:
                    tripped = True
                elif cond == "volume_below" and vol <= thr:
                    tripped = True
                elif cond == "ai_buy":
                    sig = self._latest_signal(a.symbol)
                    if sig and sig["signal_type"] in ("BUY", "WAIT_FOR_CONFIRMATION"):
                        tripped = True
                elif cond == "ai_sell":
                    sig = self._latest_signal(a.symbol)
                    if sig and sig["signal_type"] == "SELL":
                        tripped = True
                if tripped:
                    a.status = "fired"
                    a.fired_at = datetime.utcnow()
                    a.message = f"{cond} {thr:g} triggered for {a.symbol} (price {close:.2f}, change {pct:+.2f}%)"
                    db.commit()
                    fired.append({"alert": self._to_dict(a), "message": a.message})
            return fired
        finally:
            db.close()

    def notifications(self, limit: int = 20) -> List[Dict]:
        """Fired-alert notifications visible to the user."""
        db = SessionLocal()
        try:
            rows = (
                db.query(Alert)
                .filter(Alert.status == "fired")
                .order_by(Alert.fired_at.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(a) for a in rows]
        finally:
            db.close()

    def _latest_signal(self, symbol: str) -> Optional[Dict]:
        db = SessionLocal()
        try:
            row = db.query(Signal).filter(Signal.symbol == symbol).order_by(Signal.generated_at.desc()).first()
            if not row:
                return None
            return {"symbol": row.symbol, "signal_type": row.signal_type, "generated_at": row.generated_at}
        finally:
            db.close()

    def _to_dict(self, a: Alert) -> Dict:
        def iso(v):
            return v.isoformat() if isinstance(v, datetime) else v

        return {
            "id": a.id,
            "symbol": a.symbol,
            "condition": a.condition,
            "threshold": round(float(a.threshold), 4),
            "status": a.status,
            "fired_at": iso(a.fired_at),
            "message": a.message or "",
            "created_at": iso(a.created_at),
        }


alerts_service = AlertsService()

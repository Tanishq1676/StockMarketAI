"""Alerts & notifications endpoints (Phase 13)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Query

from ..alerts.service import alerts_service

router = APIRouter()


@router.post("/alerts", tags=["alerts"])
def create_alert(symbol: str = Body(...), condition: str = Body(...), threshold: float = Body(...),
                 user_id: int = Body(None)):
    alert = alerts_service.create_alert(symbol=symbol, condition=condition, threshold=threshold, user_id=user_id)
    return {"alert": alert}


@router.get("/alerts", tags=["alerts"])
def list_alerts(active_only: bool = Query(False), user_id: int = Query(None)):
    return {"alerts": alerts_service.list_alerts(active_only=active_only, user_id=user_id)}


@router.get("/alerts/notifications", tags=["alerts"])
def list_notifications(limit: int = Query(20, ge=1, le=100)):
    return {"notifications": alerts_service.notifications(limit=limit)}


@router.post("/alerts/{alert_id}/dismiss", tags=["alerts"])
def dismiss_alert(alert_id: int):
    ok = alerts_service.dismiss(alert_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(404, "alert not found or already dismissed")
    return {"ok": True}


@router.delete("/alerts/{alert_id}", tags=["alerts"])
def delete_alert(alert_id: int):
    ok = alerts_service.delete_alert(alert_id)
    return {"ok": ok}


@router.post("/alerts/evaluate", tags=["alerts"])
def evaluate_alerts():
    from ..reports.helpers import build_market_context

    ctx = build_market_context()
    market_map = {d["symbol"]: d for d in ctx["all"]}
    fired = alerts_service.evaluate(market_map)
    return {"fired_count": len(fired), "fired": fired}



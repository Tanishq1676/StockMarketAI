"""Market reports endpoints (Phase 14): hourly/daily AI market reports."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..reports.service import market_report_service

router = APIRouter()


@router.post("/reports/hourly", tags=["reports"])
def generate_hourly_report():
    return market_report_service.generate_report("hourly")


@router.post("/reports/daily", tags=["reports"])
def generate_daily_report():
    return market_report_service.generate_report("daily")


@router.get("/reports", tags=["reports"])
def list_reports(limit: int = 20):
    return {"reports": market_report_service.list_reports(limit=limit)}


@router.get("/reports/{report_id}", tags=["reports"])
def get_report(report_id: int):
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        from ..models import MarketReport

        row = db.query(MarketReport).filter(MarketReport.id == report_id).first()
        if not row:
            raise HTTPException(404, "report not found")
        return {
            "id": row.id,
            "report_type": row.report_type,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
            "data_source": row.data_source,
            "content": row.content,
        }
    finally:
        db.close()

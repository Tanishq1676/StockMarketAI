"""Dashboard endpoint (Phase 11): composed terminal-style dashboard data."""

from __future__ import annotations

from ..services.dashboard import compose_dashboard

router = None

from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard", tags=["dashboard"])
def dashboard():
    return compose_dashboard()

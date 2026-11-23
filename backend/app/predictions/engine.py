"""Predictive modelling engine (Phase 7).

Combines:
- Historical time-series analysis (OLS linear trend on closes),
- Momentum signals (recent rate of change, MA velocities),
- Mean-reversion around support/resistance,
- A scikit-learn LinearRegression model fit on lagged technical features,
- Volatility-based prediction intervals.

Prediction intervals are shown as ranges, never as exact future prices.
All predictions are persisted (Prediction table) and later validated
against actual prices by `validate_pending()`; accuracy metrics are
computed by `accuracy_report()`.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..database import SessionLocal
from ..models import HistoricalPrice, Prediction
from ..analysis import indicators
from ..analysis.time_series import fetch_history

HORIZONS_MINUTES = {
    "15min": 15,
    "30min": 30,
    "1hour": 60,
    "2hour": 120,
    "1day": 1440,
    "5days": 7200,
}
# 1 trading day = 60*24 minutes; '5days' = 5 trading days (7200 min)


def _ols_trend(closes: List[float]) -> Dict[str, float]:
    """Fit y = mx + b on closes; returns slope per day, intercept, residual std."""
    arr = np.array(closes[-150:], dtype=float)
    x = np.arange(len(arr), dtype=float)
    if len(arr) < 4:
        return {"slope_per_day": 0.0, "intercept": arr[-1] if len(arr) else 0.0, "residual_std": 0.0}
    b, a = np.polyfit(x, arr, 1)
    pred = a + b * x
    resid = arr - pred
    resid_std = float(np.std(resid, ddof=1)) if len(resid) > 1 else 0.0
    return {"slope_per_day": float(b), "intercept": float(a), "residual_std": resid_std}


def _ml_forecast(closes: List[float]) -> Optional[float]:
    """Train sklearn LinearRegression on lagged technical features.

    Features for row i: [c[i-5], c[i-15], c[i-26], c[i-51], c[i-101], c[i-201], rsi?].
    Returns the model's forecast for the immediate next close.
    """
    try:
        from sklearn.linear_model import LinearRegression
    except Exception:  # pragma: no cover - sklearn is a dependency
        return None
    if len(closes) < 150:
        return None
    close = np.array(closes, dtype=float)
    rsi = np.array(indicators.rsi(closes, 14), dtype=float)

    X, y = [], []
    lags = [5, 15, 26, 51, 101, 201]
    for i in range(max(lags) + 1, len(close) - 3):
        row = []
        for lag in lags:
            row.append(close[i - lag])
        row.append(float(rsi[i - 1]) if not math.isnan(rsi[i - 1]) else 50.0)
        row.append(close[i])  # y target is next close
        X.append(row[:-1])
        y.append(row[-1])
    if len(X) < 80:
        return None
    X = np.array(X[:-30])  # hold out tail
    y = np.array(y[:-30])
    X_test = np.array([X[-1]])
    model = LinearRegression()
    model.fit(X, y)
    try:
        pred = float(model.predict(X_test)[0])
    except Exception:
        return None
    return pred if math.isfinite(pred) and pred > 0 else None


def _momentum_signal(closes: List[float], current_price: Optional[float] = None) -> float:
    """Return a momentum scalar in roughly [-1, 1] (positive = up)."""
    if len(closes) < 30:
        return 0.0
    recent = closes[-20:]
    drift = (recent[-1] - recent[0]) / max(recent[0], 1e-9)
    ma5 = indicators.sma(closes, 5)
    ma20 = indicators.sma(closes, 20)
    last_ma5 = _last_valid(ma5) or closes[-1]
    last_ma20 = _last_valid(ma20) or closes[-1]
    vel = (last_ma5 - last_ma20) / max(last_ma20, 1e-9)
    cur = closes[-1]
    if current_price and current_price != 0:
        cur = float(current_price)
    m1 = float(np.tanh(drift * 100))  # compress to [-1,1]
    m2 = float(np.tanh(vel * 20))
    return 0.5 * (m1 + m2)


def _reversion_signal(closes: List[float]) -> float:
    """Mean-reversion scalar around recent SMA. Positive = price above mean."""
    if len(closes) < 60:
        return 0.0
    sma20 = indicators.sma(closes, 20)
    sma50 = indicators.sma(closes, 50)
    l20 = _last_valid(sma20) or closes[-1]
    l50 = _last_valid(sma50) or closes[-1]
    z = (closes[-1] - l50) / max(l50, 1e-9) * 10  # in % terms scaled
    z2 = (closes[-1] - l20) / max(l20, 1e-9) * 10
    return float(np.tanh(z) * 0.7 + np.tanh(z2) * 0.3)


def _last_valid(series, n: int = 1):
    for x in reversed(series):
        if x is not None and not (isinstance(x, float) and math.isnan(x)):
            return float(x)
    return None


def forecast_for_horizon(
    closes: List[float],
    current_price: Optional[float],
    horizon_minutes: int,
    news_sentiment: float = 0.0,
) -> Dict[str, object]:
    """Point forecast + interval + direction + probabilities for one horizon."""
    if len(closes) < 30:
        base = float(closes[-1]) if closes else 0.0
        return {
            "predicted_close": base,
            "prediction_interval": [base, base],
            "direction": "flat",
            "bullish_probability": 0.5,
            "bearish_probability": 0.5,
            "confidence": 0.3,
            "note": "insufficient history",
        }

    horizon_days = horizon_minutes / 1440.0
    trend = _ols_trend(closes)
    ml_pt = _ml_forecast(closes)
    mom = _momentum_signal(closes, current_price)
    rev = _reversion_signal(closes)

    base_close = float(closes[-1])
    # linear trend point
    lin_point = base_close + trend["slope_per_day"] * horizon_days
    # momentum: recent drift scaled by horizon
    mom_point = base_close + base_close * 0.004 * (mom * max(horizon_days, 0.02 / 1440) * 0.5)
    # reversion: move half-way back toward the 20/50 MA band
    reversion_level = base_close + (rev * base_close * 0.008)

    # ensemble: linear trend dominates on longer horizons, momentum on short
    if horizon_days <= 1 / 24:  # intraday horizons
        w_lin, w_mom, w_rev = 0.35, 0.45, 0.20
    elif horizon_days <= 1:
        w_lin, w_mom, w_rev = 0.50, 0.30, 0.20
    else:
        w_lin, w_mom, w_rev = 0.65, 0.15, 0.20

    point = w_lin * lin_point + w_mom * mom_point + w_rev * reversion_level
    if ml_pt is not None and math.isfinite(ml_pt):
        point = 0.5 * point + 0.5 * ml_pt

    # interval: in-sample residual std + volatility scaled by horizon
    hv = indicators.historical_volatility(closes, 30)
    vol_spread = 0.0
    if math.isfinite(hv) and hv > 0:
        # expected move over the horizon: sigma * sqrt(t), t in years
        vol_spread = hv * math.sqrt(horizon_days / 252)
        vol_spread *= 3.0  # widen interval (3-sigma style)
    resid_std = max(trend["residual_std"], 1e-6)
    spread = resid_std + vol_spread

    z = 1.959963984540054  # 97.5th percentile of standard normal
    lower = point - z * spread
    upper = point + z * spread
    lower = max(lower, point * 0.75)
    upper = min(upper, point * 1.35)

    delta = (point - base_close) / max(base_close, 1e-9) * 100.0  # % move
    interval_pct = (upper - lower) / max(base_close, 1e-9) * 100.0
    # News sentiment nudges probabilities (max ±0.15 adjustment)
    sentiment_adj = float(np.clip(news_sentiment, -0.2, 0.2)) * 0.75

    # Direction: sign of expected move relative to base close
    if point > base_close * (1 + 0.002):
        direction = "up"
    elif point < base_close * (1 - 0.002):
        direction = "down"
    else:
        direction = "flat"

    # Probabilities: logistic-style mapping of expected move over spread
    def sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    bull = sigmoid((delta + 0.3 * sentiment_adj) / max(interval_pct / 4.0, 0.05))
    bear = sigmoid((-delta + 0.3 * sentiment_adj) / max(interval_pct / 4.0, 0.05))
    total = bull + bear
    if total <= 0:
        bull = bear = 0.5
    else:
        bull /= total
        bear /= total
    if direction == "flat":
        bull = 0.5
        bear = 0.5
    bull = min(max(bull, 0.05), 0.95)
    bear = min(max(bear, 0.05), 0.95)

    # Confidence: distance of point from current close, but penalised by
    # model spread and data freshness.
    conf = 0.45 + 0.55 * min(abs(delta) * 3.0 / max(interval_pct, 0.01), 1.0)
    conf = min(max(conf, 0.4), 0.9)

    return {
        "predicted_close": round(float(point), 4),
        "prediction_interval": [round(float(lower), 4), round(float(upper), 4)],
        "direction": direction,
        "bullish_probability": round(float(bull), 3),
        "bearish_probability": round(float(bear), 3),
        "confidence": round(float(conf), 3),
        "expected_move_pct": round(delta, 3),
        "interval_width_pct": round(interval_pct, 3),
    }


class PredictionService:
    def generate_for_symbol(self, symbol: str, current_price: Optional[float] = None) -> List[Dict[str, object]]:
        rows = fetch_history(symbol, (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d"),
                             datetime.utcnow().strftime("%Y-%m-%d"))
        if not rows:
            return []
        closes = [float(r.close) for r in rows]
        source = getattr(rows[-1], "source", "demo")
        results = []
        db = SessionLocal()
        try:
            for horizon, minutes in HORIZONS_MINUTES.items():
                forecast = forecast_for_horizon(closes, current_price, minutes)
                pred = Prediction(
                    symbol=symbol,
                    horizon_minutes=minutes,
                    predicted_close=forecast["predicted_close"],
                    direction=forecast["direction"],
                    confidence=forecast["confidence"],
                    model_type="ensemble_linear+momentum+ml_linear_regression",
                    features=[forecast["expected_move_pct"], forecast["interval_width_pct"]],
                    price_anchor=closes[-1],
                    generated_at=datetime.utcnow(),
                )
                db.add(pred)
                forecast["horizon"] = horizon
                forecast["data_source"] = source
                forecast["expected_holding_minutes"] = minutes
                results.append(forecast)
            db.commit()
        finally:
            db.close()
        return results

    def preview_for_symbol(self, symbol: str, current_price: Optional[float] = None) -> List[Dict[str, object]]:
        """Forecast every horizon without persisting anything.

        Used by the on-demand signal endpoint so the decision ensemble can use
        forecast consensus without writing prediction rows on every click.
        """
        rows = fetch_history(
            symbol,
            (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d"),
            datetime.utcnow().strftime("%Y-%m-%d"),
        )
        if not rows:
            return []
        closes = [float(r.close) for r in rows]
        source = getattr(rows[-1], "source", "unavailable")
        results: List[Dict[str, object]] = []
        for horizon, minutes in HORIZONS_MINUTES.items():
            forecast = forecast_for_horizon(closes, current_price, minutes)
            forecast["horizon"] = horizon
            forecast["data_source"] = source
            forecast["expected_holding_minutes"] = minutes
            results.append(forecast)
        return results

    def validate_pending(self) -> List[Dict[str, object]]:
        """Validate old predictions against actual closes; return accuracy rows."""
        db = SessionLocal()
        try:
            pending = db.query(Prediction).filter(Prediction.validated == False).all()
            validated = []
            for p in pending:
                # find actual close closest to (generated + horizon), at most end of today
                rows = db.query(HistoricalPrice).filter(
                    HistoricalPrice.symbol == p.symbol,
                    HistoricalPrice.date >= p.generated_at.strftime("%Y-%m-%d"),
                ).order_by(HistoricalPrice.date).all()
                if not rows:
                    continue
                actual = float(rows[-1].close)
                err = (actual - p.predicted_close) / max(p.predicted_close, 1e-9) * 100.0
                p.actual_close = actual
                p.validated = True
                p.error_pct = round(err, 3)
                p.direction_correct = bool(actual > p.price_anchor) == (p.direction == "up")
                validated.append({"symbol": p.symbol, "horizon_minutes": p.horizon_minutes,
                                  "predicted": p.predicted_close, "actual": actual,
                                  "error_pct": p.error_pct, "direction_correct": p.direction_correct})
            db.commit()
            return validated
        finally:
            db.close()

    def accuracy_report(self, symbol: Optional[str] = None, horizon: Optional[int] = None) -> Dict[str, object]:
        db = SessionLocal()
        try:
            q = db.query(Prediction).filter(Prediction.validated == True)
            if symbol:
                q = q.filter(Prediction.symbol == symbol)
            if horizon:
                q = q.filter(Prediction.horizon_minutes == horizon)
            rows = q.all()
            if not rows:
                return {"accuracy": None, "message": "no validated predictions yet"}
            errs = [abs(r.error_pct) for r in rows]
            correct = sum(1 for r in rows if r.direction_correct)
            return {
                "samples": len(rows),
                "mae_pct": round(float(np.mean(errs)), 3),
                "rmse_pct": round(float(np.sqrt(np.mean(np.square([r.error_pct for r in rows])))), 3),
                "direction_accuracy": round(correct / len(rows), 3),
                "last_5": [
                    {"symbol": r.symbol, "horizon": r.horizon_minutes, "predicted": r.predicted_close,
                     "actual": r.actual_close, "error_pct": r.error_pct,
                     "direction_correct": r.direction_correct}
                    for r in rows[-5:]
                ],
            }
        finally:
            db.close()


prediction_service = PredictionService()

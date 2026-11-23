"""Backend smoke tests (Phase 10 / data accuracy & calculations)."""

import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "backend"))
os.environ.setdefault("PAPER_TRADING_INITIAL_BALANCE", "100000")

from app.analysis import indicators  # noqa: E402


def test_indicators_rsi_ma():
    import math

    closes = [100 + ((i * 7) % 13) - 6 for i in range(60)]
    rsi = indicators.rsi(closes, 14)
    assert rsi[-1] is not None and not math.isnan(rsi[-1]) and 0 <= rsi[-1] <= 100, rsi[-1]
    up = indicators.rsi([100 + i * 0.5 for i in range(30)], 14)
    assert up[-1] > 90, up[-1]
    ma = indicators.sma(closes, 5)
    assert abs(ma[-1] - sum(closes[-5:]) / 5) < 0.01, ma[-1]


def test_bollinger_bands():
    closes = [100 + (i % 7) for i in range(40)]
    bb = indicators.bollinger_bands(closes, 20, 2.0)
    assert bb["upper"][-1] > bb["middle"][-1] > bb["lower"][-1]


def test_support_resistance():
    closes = [100 + (i * 0.1) % 3 - 1.5 for i in range(60)]
    levels = indicators.support_resistance(closes)
    assert len(levels) > 0 and levels == sorted(levels) and len(set(levels)) == len(levels)


def test_max_drawdown():
    closes = [100, 110, 90, 120, 60]
    dd, _ = indicators.max_drawdown(closes)
    assert abs(dd - (120 - 60) / 120 * 100) < 0.01, dd


def test_signal_engine_builds():
    from app.ai.rules_engine import rules_signal_for_stock

    tech = {"rsi14_last": 60, "ma50": 100.0, "ma200": 99.0, "trend": "bullish",
            "historical_volatility_annualized": 15, "volume_ratio": 1.2,
            "ma": {"ma50": [100.0], "ma200": [99.0]}}
    decision = rules_signal_for_stock("TEST", tech, [{"direction": "up", "confidence": 0.7}], 0.2)
    assert decision["signal_type"] in ("BUY", "WAIT_FOR_CONFIRMATION", "HOLD", "SELL")


def test_predictions_engine_runs():
    from app.predictions.engine import forecast_for_horizon

    closes = [100.0 + 0.02 * i + ((-1) ** i) * (i % 5) * 0.3 for i in range(400)]
    f = forecast_for_horizon(closes, 100.0, 1440)
    assert f["direction"] in ("up", "down", "flat")
    assert f["prediction_interval"][0] <= f["predicted_close"] <= f["prediction_interval"][1]
    assert 0 <= f["bullish_probability"] + f["bearish_probability"] <= 2


def test_paper_trading_buy_sell():
    from app.paper.trading import PaperTradingService

    svc = PaperTradingService(initial_balance=100000)
    # Fake provider-independent execution via entry_price path: use real provider quote
    order = svc.place_order("TCS", "BUY", 1, entry_price=3000.0)
    assert order["action"] == "BUY" and order["qty"] == 1
    wallet = svc.wallet_summary()
    assert wallet["total_trades"] >= 1
    print("wallet:", wallet["wallet_balance"])


def test_portfolio_math():
    from app.portfolio.calculator import PortfolioService

    svc = PortfolioService()
    sym = f"TEST-{os.getpid()}"
    svc.add_transaction(symbol=sym, action="buy", qty=10, price=100.0, fees=5.0, taxes=2.0)
    svc.add_transaction(symbol=sym, action="sell", qty=4, price=110.0)
    summary = svc.portfolio_summary()
    st = next((s for s in summary["stocks"] if s["symbol"] == sym), None)
    assert st is not None and st["qty"] == 6, summary["stocks"]
    assert st["invested_cost"] == 1007.0
    assert st["avg_buy_price"] == 100.0


def test_alerts_evaluate():
    from app.alerts.service import alerts_service

    alert = alerts_service.create_alert("TCS", "price_above", 100000.0)
    assert alert["status"] == "active"
    alerts_service.delete_alert(alert["id"])


def test_news_sentiment():
    from app.news import sentiment

    assert sentiment.score_text("reliance stock rally surge beat analyst expectations") > 0
    assert sentiment.score_text("crash market falls") < 0
    assert sentiment.classify_impact(0.5) == "positive"


def run_all():
    fns = [v for k, v in globals().items() if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"All {len(fns)} backend smoke tests passed")


if __name__ == "__main__":
    run_all()

"""Automatic, read-only review of matured forecasts.

The worker uses the official CN exchange calendar and unadjusted daily closes.
Missing calendar/price data leaves a prediction pending; it never invents a
weekday or a price and never submits an order.
"""
from __future__ import annotations

from datetime import date
import asyncio
import os
from typing import Callable

from .learning_store import LearningStore


def exchange_sessions_after(trade_date: str, horizon: int) -> list[str]:
    from tradingagents.dataflows.trade_calendar import _load_cn_trade_dates
    dates, _ = _load_cn_trade_dates()
    if not dates:
        raise RuntimeError("CN exchange calendar unavailable; review remains pending")
    start = date.fromisoformat(trade_date)
    return [d.isoformat() for d in dates if d > start][:horizon]


def fetch_unadjusted_close(symbol: str, start: str, end: str) -> dict[str, float]:
    import akshare as ak  # type: ignore
    code = symbol.split(".", 1)[0]
    frame = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start.replace("-", ""),
                               end_date=end.replace("-", ""), adjust="")
    if frame is None or frame.empty:
        return {}
    date_col = "日期" if "日期" in frame.columns else "date"
    close_col = "收盘" if "收盘" in frame.columns else "close"
    return {str(row[date_col])[:10]: float(row[close_col]) for _, row in frame.iterrows()
            if row[date_col] == row[date_col] and row[close_col] == row[close_col]}


def review_once(store: LearningStore, *, scope="local",
                fetch: Callable[[str, str, str], dict[str, float]] = fetch_unadjusted_close) -> dict:
    completed = failed = pending = 0
    for item in store.pending(scope=scope):
        try:
            sessions = exchange_sessions_after(item["trade_date"], item["horizon"])
            if len(sessions) < item["horizon"]:
                pending += 1
                continue
            prices = fetch(item["symbol"], item["trade_date"], sessions[-1])
            baseline = item["reference_price"]
            if baseline is None:
                baseline = prices.get(item["trade_date"])
            realized = prices.get(sessions[item["horizon"] - 1])
            if realized is None or baseline is None:
                pending += 1
                continue
            store.record_outcome(item["id"], realized_price=realized, reference_price=baseline,
                                 realized_date=sessions[item["horizon"] - 1], session_dates=sessions,
                                 source="akshare.stock_zh_a_hist:unadjusted", scope=scope)
            completed += 1
        except Exception as exc:
            failed += 1
            with store.connection() as conn:
                store._event(conn, scope, "review_fetch_failed", {"prediction_id": item["id"],
                                                                     "error": str(exc)[:300]})
    return {"completed": completed, "pending": pending, "failed": failed}


async def review_loop(path: str, interval: int = 3600):
    while True:
        try:
            await asyncio.to_thread(review_once, LearningStore(path))
        except Exception:
            pass
        await asyncio.sleep(max(60, interval))


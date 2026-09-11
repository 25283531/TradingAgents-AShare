"""Reproducible rules for A-share 2-5 trading-day research.

The functions deliberately accept mappings so they can consume provider data,
JSON fixtures, or an analyst state without coupling to a particular vendor.
Missing evidence fails closed for hard filters and never receives an invented value.
"""
from dataclasses import dataclass, asdict
import math
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RuleConfig:
    max_price: float = 7.0
    min_turnover: float = 100_000_000.0
    max_candidates: int = 5
    holding_days: int = 5
    default_size_cap: float = 0.10


WEIGHTS = {
    "market": 15, "industry_money": 15, "stock_money": 15,
    "relative_strength": 15, "liquidity": 10, "news_policy": 10,
    "sentiment": 10, "technical": 5, "expectation_gap": 5,
}


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        result = float(value)
        return result if math.isfinite(result) and not isinstance(value, bool) else None
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "yes", "y", "1", "是", "通过", "pass"}:
        return True
    if text in {"false", "no", "n", "0", "否", "不通过", "fail"}:
        return False
    return None


def evaluate_hard_filters(stock: Mapping[str, Any], config: RuleConfig | None = None) -> dict[str, Any]:
    """Return pass/fail, individual checks, and explicit reasons.

    Aliases commonly returned by market providers are supported. A missing
    required value fails the relevant check, making data quality visible.
    """
    cfg = config or RuleConfig()
    price = _num(stock.get("price", stock.get("last")))
    turnover = _num(stock.get("turnover", stock.get("amount", stock.get("成交额"))))
    relative = _bool(stock.get("stronger_than_industry", stock.get("relative_strength_pass")))
    persistent_outflow = _bool(stock.get("persistent_outflow", stock.get("funds_persistent_outflow")))
    consecutive_limit = _bool(stock.get("consecutive_limit_up", stock.get("consecutive_limitup")))
    overbought = _bool(stock.get("severely_overbought", stock.get("overbought")))
    catalyst = _bool(stock.get("has_2_5d_catalyst", stock.get("tradable_thesis")))
    checks = {
        "price": price is not None and 0 < price <= cfg.max_price,
        "turnover": turnover is not None and turnover >= cfg.min_turnover,
        "relative_strength": relative is True,
        "funds": persistent_outflow is False,
        "limit_up_pattern": consecutive_limit is False,
        "overbought": overbought is False,
        "thesis": catalyst is True,
    }
    missing = []
    for key, val in (("price", price), ("turnover", turnover), ("relative_strength", relative),
                     ("funds", persistent_outflow), ("limit_up_pattern", consecutive_limit),
                     ("overbought", overbought), ("thesis", catalyst)):
        if val is None:
            missing.append(key)
    reasons = [f"{key} check failed" for key, passed in checks.items() if not passed]
    return {"pass": all(checks.values()), "checks": checks, "reasons": reasons,
            "missing": missing, "config": asdict(cfg)}


def filter_candidates(stocks: Sequence[Mapping[str, Any]], config: RuleConfig | None = None) -> list[dict[str, Any]]:
    """Apply hard filters and return at most the configured number of stocks."""
    cfg = config or RuleConfig()
    result = []
    for stock in stocks:
        check = evaluate_hard_filters(stock, cfg)
        if check["pass"]:
            item = dict(stock)
            item["hard_filter"] = check
            result.append(item)
    return result[: cfg.max_candidates]


def score_candidate(stock: Mapping[str, Any], context: Mapping[str, Any] | None = None,
                    *, weights: Mapping[str, float] | None = None) -> dict[str, Any]:
    """Score a candidate on the nine rule dimensions (each value is 0..weight)."""
    ctx = context or {}
    weights = dict(weights or WEIGHTS)
    if set(weights) != set(WEIGHTS) or not math.isclose(sum(weights.values()), 100, abs_tol=1e-6):
        raise ValueError("weights must contain all factors and sum to 100")
    scores = {}
    for key, weight in weights.items():
        raw = stock.get(key, ctx.get(key, 0))
        value = _num(raw)
        if value is None:
            value = 0.0
        if not 0 <= value <= 1:
            raise ValueError("factor assessments must be normalized to [0,1]")
        scores[key] = round(value * weight, 2)
    total = round(sum(scores.values()), 2)
    rating = "strong_attention" if total >= 80 else "tradable_wait" if total >= 70 else "observe" if total >= 60 else "淘汰"
    return {"scores": scores, "total": total, "rating": rating, "weights": weights}


def normalize_action(action: Any, *, risk_veto: bool = False, trigger_confirmed: bool = False,
                     score: float | None = None) -> str:
    """Map model prose/directions to the four allowed short-term actions."""
    if risk_veto:
        return "NO TRADE"
    text = str(action or "").strip().upper()
    if text in {"NO TRADE", "NO_TRADE", "NOTRADE", "拒绝", "剔除", "SELL"}:
        return "NO TRADE"
    if text in {"BUY", "买入", "增持"}:
        return "BUY" if trigger_confirmed else "WAIT"
    if text in {"WAIT", "等待", "HOLD", "持有", "条件建仓"}:
        return "WAIT"
    if text in {"OBSERVE", "观望", "观察"}:
        return "OBSERVE"
    if score is not None and score < 60:
        return "NO TRADE"
    return "OBSERVE"


def build_trade_plan(stock: Mapping[str, Any], *, action: str, size_cap: float | None = None) -> dict[str, Any]:
    """Build explicit entry/exit fields for a 2-5 day paper-trading plan."""
    price = _num(stock.get("price", stock.get("last")))
    if price is None:
        return {"action": action, "status": "insufficient_data", "holding_period": "2-5 trading days"}
    volatility = str(stock.get("volatility", "normal")).lower()
    stop_pct = 0.07 if volatility in {"high", "高"} else 0.05
    entry_low = round(price * 0.98, 2)
    entry_high = round(price * 1.01, 2)
    return {
        "action": action, "entry": [entry_low, entry_high],
        "target_1": round(price * 1.06, 2), "target_2": round(price * 1.10, 2),
        "stop": round(price * (1 - stop_pct), 2), "time_stop": "2-3 trading days without thesis confirmation",
        "invalidation": ["industry weakens", "funds deteriorate", "breaks key support", "material negative news"],
        "size_cap": size_cap if size_cap is not None else RuleConfig().default_size_cap,
        "holding_period": "2-5 trading days",
    }

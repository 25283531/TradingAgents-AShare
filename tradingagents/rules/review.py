"""Historical forecast review and error statistics."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
from .learning_store import LearningStore

def review_predictions(records: Sequence[Mapping[str, Any]], *, horizon_days: int = 5) -> dict[str, Any]:
    items, errors = [], {}
    for record in records:
        pred = record.get("predicted_price", record.get("reference_price", record.get("entry")))
        realized = record.get("realized_price")
        try:
            pred, realized = float(pred), float(realized)
            if pred <= 0 or realized <= 0: raise ValueError
        except (TypeError, ValueError):
            continue
        ret = realized / pred - 1
        direction = record.get("direction")
        hit = (ret * int(direction) > 0) if direction in (-1, 1) else None
        error = (record.get("error_type") or "unknown") if hit is False else None
        if error: errors[error] = errors.get(error, 0) + 1
        items.append({"symbol": record.get("symbol"), "return": round(ret, 6),
                      "directional_hit": hit, "error_type": error,
                      "action": record.get("action", "OBSERVE")})
    scored = [i for i in items if i["directional_hit"] is not None]
    hits = sum(i["directional_hit"] is True for i in scored)
    return {"horizon_days": horizon_days, "sample_size": len(items),
            "directional_samples": len(scored), "hit_count": hits,
            "hit_rate": round(hits / len(scored), 4) if scored else None,
            "error_types": errors, "items": items,
            "metric": "forecast_direction_not_trade_pnl"}

def review_store(path="data/learning.db", *, scope="local", as_of=None) -> dict[str, Any]:
    return LearningStore(path).snapshot(scope=scope, as_of=as_of)

def review_daily_directory(directory: str | Path, realized_prices: Mapping[str, float], *, horizon_days: int = 5) -> dict[str, Any]:
    path = Path(directory)
    source = path / "candidates.json"
    records = json.loads(source.read_text(encoding="utf-8")) if source.exists() else []
    for item in records: item["realized_price"] = realized_prices.get(str(item.get("symbol")))
    result = review_predictions(records, horizon_days=horizon_days)
    (path / "review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

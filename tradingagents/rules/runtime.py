"""Connect V2 CLI, streaming API and scheduler research to persistent experience."""
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from .learning_store import LearningStore, number
from .short_term import WEIGHTS, normalize_action, score_candidate


def learning_db_path(config=None):
    return (config or {}).get("learning_db_path") or os.getenv("TA_LEARNING_DB", "data/learning.db")


def enabled(config=None):
    return str((config or {}).get("learning_enabled", os.getenv("TA_LEARNING_ENABLED", "1"))).lower() not in {"0", "false", "off"}


def payload(text, marker):
    matches = re.findall(r"<!--\s*" + marker + r":\s*(\{.*?\})\s*-->", str(text), re.S)
    try:
        value = json.loads(matches[-1]) if matches else {}
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def features_from_reports(state):
    proposed = payload(state.get("investment_plan", ""), "LEARNING_FEATURES")
    reports = {k: v for k, v in state.items() if k.endswith("_report") and isinstance(v, str)}
    features, evidence = {}, {}
    for k, item in proposed.items():
        if k not in WEIGHTS or not isinstance(item, dict):
            continue
        value = number(item.get("value"))
        report, quote = item.get("report"), item.get("quote")
        if value is None or not 0 <= value <= 1 or not isinstance(quote, str) or not quote.strip():
            continue
        if report not in reports or quote not in reports[report]:
            continue
        features[k] = value
        evidence[k] = {"report": report, "quote": quote, "kind": "model_assessment"}
    return features, evidence


def forecast_direction(text):
    direction = str(payload(text, "VERDICT").get("direction", "")).upper()
    return {"看多": 1, "偏多": 1, "BULLISH": 1, "LEAN_BULLISH": 1,
            "看空": -1, "偏空": -1, "BEARISH": -1, "LEAN_BEARISH": -1,
            "中性": 0, "NEUTRAL": 0}.get(direction)


def learning_instruction(state):
    if not state.get("learning_context"):
        return ""
    return """
【A 股短线经验与可检验因子】
以 2～5 交易日为口径，重点检验情绪阶段、热钱持续流向、板块轮动、
相对强度和价量异常；公司经营信息保留为重大风险与催化证据，不能单独推出短线涨跌。
量化资金影响是待核验的市场机制，不能凭价格异动断言资金身份。
历史记录仅为经验样本，不是当日事实。以下权重总和 100，已经过确定性验证；
请用于比较论据贡献，但不得改动价格、流动性、买点或风险否决约束。
""" + state["learning_context"] + """
最后另附一条机器可读记录（不要编造缺失维度）：
<!-- LEARNING_FEATURES: {"market":{"value":0.6,"report":"market_report","quote":"报告原文片段"}} -->
可用维度：market / industry_money / stock_money / relative_strength / liquidity /
news_policy / sentiment / technical / expectation_gap。
value 是 0～1 的相对看多程度，不是概率，不是加权分数；缺少证据时省略。
每个维度附 report 字段名和可在该报告中逐字找到的 quote，不可只引用历史经验。
"""


class LearningRuntime:
    def __init__(self, config=None):
        self.config = dict(config or {})

    def recall(self, state):
        if not enabled(self.config) or state.get("horizon", "short") != "short":
            return {}
        if not re.fullmatch(r"\d{6}(?:\.(?:SH|SZ|SS|BJ))?", state["company_of_interest"], re.I):
            return {}
        metadata = dict(state.get("metadata") or {})
        scope = str(metadata.get("learning_scope", "local"))
        metadata.setdefault("learning_run_key", str(uuid4()))
        store = LearningStore(learning_db_path(self.config))
        as_of = state["trade_date"]
        snapshot = store.snapshot(scope, as_of)
        policy = snapshot["policy"]
        context = {"weights": policy["weights"], "policy_id": policy["id"],
                   "directional_samples": snapshot["directional_samples"],
                   "directional_hit_rate": snapshot["directional_hit_rate"],
                   "lessons": store.lessons(scope, as_of)}
        metadata["learning_policy_id"] = policy["id"]
        return {"learning_context": json.dumps(context, ensure_ascii=False), "metadata": metadata}

    def archive(self, state):
        if not state.get("learning_context") or not enabled(self.config):
            return {}
        metadata = dict(state.get("metadata") or {})
        scope = str(metadata.get("learning_scope", "local"))
        store = LearningStore(learning_db_path(self.config))
        features, evidence = features_from_reports(state)
        context = json.loads(state["learning_context"])
        scored = score_candidate(features, weights=context["weights"]) if set(features) == set(WEIGHTS) else None
        final = state.get("final_trade_decision", "")
        risk = state.get("risk_feedback_state") or {}
        veto = not final or bool((state.get("circuit_breaker") or {}).get("triggered")) or risk.get("latest_risk_verdict") in {"reject", "revise"}
        action = normalize_action(payload(final, "ACTION").get("action", "OBSERVE"), risk_veto=veto)
        record = {"run_key": metadata["learning_run_key"], "symbol": state["company_of_interest"],
                  "trade_date": state["trade_date"], "horizon": 5, "action": action,
                  "direction": forecast_direction(final), "features": features, "evidence": evidence,
                  "policy_id": metadata.get("learning_policy_id")}
        prediction_id = store.record_prediction(record, scope=scope)
        metadata["learning_prediction_id"] = prediction_id
        result = {"prediction_id": prediction_id, "action": action, "score": scored,
                  "factor_coverage": len(features), "direction": record["direction"],
                  "policy_id": record["policy_id"], "review_status": "pending",
                  "metric": "5_session_close_to_close_direction"}
        from .reports import write_daily_reports
        scoped_root = (Path(self.config.get("daily_report_root", "trading/daily")) /
                       hashlib.sha256(scope.encode()).hexdigest()[:16] / str(prediction_id))
        write_daily_reports(state["trade_date"], {**state, "action": action},
                            root=scoped_root, candidates=[])
        return {"learning_result": result, "metadata": metadata}


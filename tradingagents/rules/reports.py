"""Markdown daily report and audit artifact writer."""
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
import json

ROLE_FILES = {
    "market": "00_market.md", "money": "01_money.md", "industry": "02_industry.md",
    "policy": "03_policy.md", "news": "04_news.md", "sentiment": "05_sentiment.md",
    "candidates": "06_candidates.md", "bull": "07_bull.md", "bear": "08_bear.md",
    "debate": "09_debate.md", "judge": "10_judge.md", "decision": "11_decision.md",
    "risk": "12_risk.md",
}


def _text(value: Any) -> str:
    if value is None:
        return "（无报告）"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def write_daily_reports(report_date: str, state: Mapping[str, Any], *, root: str | Path = "trading/daily",
                        data_timestamp: str | None = None, candidates: Sequence[Mapping[str, Any]] | None = None,
                        audit_sources: Mapping[str, str] | None = None) -> Path:
    """Write intermediate reports, final.md, and audit.json; return the report directory."""
    directory = Path(root) / str(report_date)
    directory.mkdir(parents=True, exist_ok=True)
    fields = {
        "market": state.get("market_report"), "money": state.get("smart_money_report"),
        "industry": state.get("sector_report"), "policy": state.get("macro_report"),
        "news": state.get("news_report"), "sentiment": state.get("sentiment_report"),
        "candidates": candidates if candidates is not None else state.get("candidates", []),
        "bull": state.get("bull_history", state.get("investment_debate_state", {}).get("bull_history")),
        "bear": state.get("bear_history", state.get("investment_debate_state", {}).get("bear_history")),
        "debate": state.get("investment_debate_state", {}).get("history"),
        "judge": state.get("investment_plan", state.get("investment_debate_state", {}).get("judge_decision")),
        "decision": state.get("trader_investment_plan", state.get("final_trade_decision")),
        "risk": state.get("risk_feedback_state", state.get("risk_debate_state", {}).get("judge_decision")),
    }
    for role, filename in ROLE_FILES.items():
        (directory / filename).write_text(
            f"# {role}\n\n- report_date: {report_date}\n- data_timestamp: {data_timestamp or '未提供'}\n- evidence: facts and inferences must be separated by the role\n\n{_text(fields[role])}\n",
            encoding="utf-8",
        )
    action = state.get("action", state.get("final_action", state.get("final_trade_decision", "NO TRADE")))
    final = [f"# A 股 2～5 日短线日报", f"\n- 日期：{report_date}", f"- 数据时间：{data_timestamp or '未提供'}",
             f"- 市场状态：{state.get('market_state', '未判定')}", f"- 情绪阶段：{state.get('sentiment_phase', '未判定')}",
             f"- 最终动作：`{action}`", "\n## 候选与交易计划\n"]
    rows = list(candidates if candidates is not None else state.get("candidates", []))[:5]
    if rows:
        final += ["| 标的 | 分数 | 动作 | 入场 | 目标 | 止损 |", "|---|---:|---|---|---|---|"]
        for item in rows:
            plan = item.get("trade_plan", {})
            final.append(f"| {item.get('name', item.get('symbol', '未命名'))} | {item.get('score', item.get('total', ''))} | {item.get('action', action)} | {plan.get('entry', '')} | {plan.get('target_1', '')}/{plan.get('target_2', '')} | {plan.get('stop', '')} |")
    else:
        final.append("今日不交易：没有通过硬筛选并完成证据核验的标的。")
    final += ["\n## 风控与失效条件\n", _text(state.get("risk_feedback_state", "未提供")),
              "\n## 审计\n", "| 角色 | 来源文件 |", "|---|---|"]
    sources = audit_sources or {role: filename for role, filename in ROLE_FILES.items()}
    for role, filename in ROLE_FILES.items():
        final.append(f"| {role} | [{filename}]({filename}) |")
    (directory / "final.md").write_text("\n".join(final) + "\n", encoding="utf-8")
    audit = {"report_date": str(report_date), "generated_at": datetime.now().isoformat(),
             "data_timestamp": data_timestamp, "roles": sources, "action": str(action),
             "evidence_policy": "A/B/C/D; facts separated from inferences"}
    (directory / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return directory

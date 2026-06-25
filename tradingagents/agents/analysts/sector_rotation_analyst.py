import asyncio
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage, SystemMessage

from tradingagents.dataflows.config import get_config
from tradingagents.prompts import get_prompt
from tradingagents.graph.intent_parser import build_horizon_context
from tradingagents.agents.utils.agent_states import current_tracker_var, extract_verdict


def create_sector_rotation_analyst(llm, data_collector=None):
    async def sector_rotation_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        horizon = "medium"
        user_intent = state.get("user_intent") or {}
        focus_areas = user_intent.get("focus_areas", [])
        specific_questions = user_intent.get("specific_questions", [])

        config = get_config()
        horizon_ctx = build_horizon_context(horizon, focus_areas, specific_questions, agent_type="sector")
        system_message = get_prompt("sector_rotation_system_message", config=config)

        board_fund_flow = "无数据"
        hot_stocks = "无数据"
        news_data = "无数据"

        if data_collector is not None:
            pool = data_collector.get(ticker, current_date)
            if pool is not None:
                windowed = data_collector.get_window(pool, horizon, current_date)
                board_fund_flow = windowed.get("board_fund_flow", "无数据")
                hot_stocks = windowed.get("hot_stocks", "无数据")
                news_data = windowed.get("news", "无数据")
            else:
                board_fund_flow, hot_stocks, news_data = await _fetch_direct(ticker, current_date)
        else:
            board_fund_flow, hot_stocks, news_data = await _fetch_direct(ticker, current_date)

        messages = [
            SystemMessage(content=system_message + "\n\n请全程使用中文。"),
            HumanMessage(content=(
                horizon_ctx + "\n"
                f"以下是 {ticker} 在 {current_date} 的行业轮动分析数据。\n\n"
                f"【板块资金流向】\n{board_fund_flow}\n\n"
                f"【热门股票/板块】\n{hot_stocks}\n\n"
                f"【相关新闻】\n{news_data}\n\n"
            )),
        ]

        tracker = current_tracker_var.get()
        full_content = ""
        async for chunk in llm.astream(messages):
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            full_content += content
            if tracker:
                tracker._emit_token("Sector Rotation Analyst", "sector_report", content)

        verdict, confidence = extract_verdict(full_content)

        return {
            "sector_report": full_content,
            "analyst_traces": [{
                "agent": "sector_rotation_analyst",
                "horizon": horizon,
                "key_finding": f"行业轮动结论：{verdict}",
                "verdict": verdict,
                "confidence": confidence,
            }],
        }

    return sector_rotation_analyst_node


async def _fetch_direct(ticker, current_date):
    from tradingagents.agents.utils.game_theory_tools import (
        get_board_fund_flow,
        get_hot_stocks_xq,
        get_news,
    )

    async def _safe(tool, payload):
        try:
            return await asyncio.to_thread(tool.invoke, payload)
        except Exception as exc:
            return f"调用失败：{exc}"

    days = 7
    end_dt = datetime.strptime(current_date, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=days)

    tasks = {
        "board_fund_flow": _safe(get_board_fund_flow, {"symbol": ticker}),
        "hot_stocks": _safe(get_hot_stocks_xq, {}),
        "news": _safe(get_news, {
            "symbol": ticker,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": current_date,
        }),
    }

    keys = list(tasks.keys())
    results = await asyncio.gather(*[tasks[k] for k in keys])
    res_map = dict(zip(keys, results))

    return res_map["board_fund_flow"], res_map["hot_stocks"], res_map["news"]

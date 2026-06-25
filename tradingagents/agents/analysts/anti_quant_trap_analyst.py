import asyncio
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage, SystemMessage

from tradingagents.dataflows.config import get_config
from tradingagents.prompts import get_prompt
from tradingagents.graph.intent_parser import build_horizon_context
from tradingagents.agents.utils.agent_states import current_tracker_var, extract_verdict


def create_anti_quant_trap_analyst(llm, data_collector=None):
    async def anti_quant_trap_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        horizon = "medium"
        user_intent = state.get("user_intent") or {}
        focus_areas = user_intent.get("focus_areas", [])
        specific_questions = user_intent.get("specific_questions", [])

        config = get_config()
        horizon_ctx = build_horizon_context(horizon, focus_areas, specific_questions, agent_type="anti_quant")
        system_message = get_prompt("anti_quant_trap_system_message", config=config)

        fund_flow = "无数据"
        lhb_detail = "无数据"
        stock_data = "无数据"
        market_cap = "无数据"
        avg_volume = "无数据"

        if data_collector is not None:
            pool = data_collector.get(ticker, current_date)
            if pool is not None:
                windowed = data_collector.get_window(pool, horizon, current_date)
                fund_flow = windowed.get("fund_flow", "无数据")
                lhb_detail = windowed.get("lhb_detail", "无数据")
                stock_data = windowed.get("stock_data", "无数据")
                market_cap = windowed.get("market_cap", "无数据")
                avg_volume = windowed.get("avg_volume", "无数据")
            else:
                fund_flow, lhb_detail, stock_data, market_cap, avg_volume = await _fetch_direct(ticker, current_date)
        else:
            fund_flow, lhb_detail, stock_data, market_cap, avg_volume = await _fetch_direct(ticker, current_date)

        messages = [
            SystemMessage(content=system_message + "\n\n请全程使用中文。"),
            HumanMessage(content=(
                horizon_ctx + "\n"
                f"以下是 {ticker} 在 {current_date} 的量化陷阱检测数据。\n\n"
                f"【个股资金流向】\n{fund_flow}\n\n"
                f"【龙虎榜数据】\n{lhb_detail}\n\n"
                f"【股票行情数据】\n{stock_data}\n\n"
                f"【市值信息】\n{market_cap}\n\n"
                f"【日均成交额】\n{avg_volume}\n\n"
            )),
        ]

        tracker = current_tracker_var.get()
        full_content = ""
        async for chunk in llm.astream(messages):
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            full_content += content
            if tracker:
                tracker._emit_token("Anti-Quant Trap Analyst", "anti_quant_report", content)

        verdict, confidence = extract_verdict(full_content)

        return {
            "anti_quant_report": full_content,
            "analyst_traces": [{
                "agent": "anti_quant_trap_analyst",
                "horizon": horizon,
                "key_finding": f"量化陷阱检测结论：{verdict}",
                "verdict": verdict,
                "confidence": confidence,
            }],
        }

    return anti_quant_trap_analyst_node


async def _fetch_direct(ticker, current_date):
    from tradingagents.agents.utils.core_stock_tools import get_stock_data
    from tradingagents.agents.utils.game_theory_tools import (
        get_individual_fund_flow,
        get_lhb_detail,
    )

    async def _safe(tool, payload):
        try:
            return await asyncio.to_thread(tool.invoke, payload)
        except Exception as exc:
            return f"调用失败：{exc}"

    days = 30
    end_dt = datetime.strptime(current_date, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=days)

    tasks = {
        "fund_flow": _safe(get_individual_fund_flow, {"symbol": ticker}),
        "lhb_detail": _safe(get_lhb_detail, {"symbol": ticker}),
        "stock_data": _safe(get_stock_data, {
            "symbol": ticker,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": current_date,
        }),
    }

    keys = list(tasks.keys())
    results = await asyncio.gather(*[tasks[k] for k in keys])
    res_map = dict(zip(keys, results))

    stock_data = res_map["stock_data"]
    market_cap = await _estimate_market_cap(ticker)
    avg_volume = _calculate_avg_volume(stock_data)

    return res_map["fund_flow"], res_map["lhb_detail"], stock_data, market_cap, avg_volume


async def _estimate_market_cap(symbol: str) -> str:
    try:
        from tradingagents.dataflows.interface import route_to_vendor
        result = route_to_vendor("get_fundamentals", symbol)
        if result and "总市值" in result:
            return result
    except Exception:
        pass
    return "无法获取市值数据"


def _calculate_avg_volume(stock_data: str) -> str:
    try:
        import pandas as pd
        lines = stock_data.strip().split("\n")
        data_lines = [line for line in lines if not line.startswith("#")]
        if not data_lines:
            return "无法计算"

        df = pd.DataFrame([line.split(",") for line in data_lines[1:]], columns=data_lines[0].split(","))
        if "Volume" in df.columns:
            df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
            avg_vol = df["Volume"].mean()
            if pd.notna(avg_vol):
                if avg_vol >= 1e8:
                    return f"日均成交额：{avg_vol/1e8:.2f} 亿"
                elif avg_vol >= 1e4:
                    return f"日均成交额：{avg_vol/1e4:.2f} 万"
                return f"日均成交额：{avg_vol:.0f}"
    except Exception:
        pass
    return "无法计算"

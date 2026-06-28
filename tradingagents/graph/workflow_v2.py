from typing import Dict, Any, List, Optional, Callable
from langgraph.graph import END, StateGraph, START

from tradingagents.agents.utils.agent_states import AgentState


def _load_agent_factories() -> dict[str, Any]:
    from tradingagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst
    from tradingagents.agents.analysts.macro_analyst import create_macro_analyst
    from tradingagents.agents.analysts.market_analyst import create_market_analyst
    from tradingagents.agents.analysts.news_analyst import create_news_analyst
    from tradingagents.agents.analysts.smart_money_analyst import create_smart_money_analyst
    from tradingagents.agents.analysts.social_media_analyst import create_social_media_analyst
    from tradingagents.agents.analysts.volume_price_analyst import create_volume_price_analyst
    from tradingagents.agents.analysts.sector_rotation_analyst import create_sector_rotation_analyst
    from tradingagents.agents.analysts.anti_quant_trap_analyst import create_anti_quant_trap_analyst
    from tradingagents.agents.managers.research_manager import create_research_manager
    from tradingagents.agents.managers.risk_manager import create_risk_manager
    from tradingagents.agents.researchers.bear_researcher import create_bear_researcher
    from tradingagents.agents.researchers.bull_researcher import create_bull_researcher
    from tradingagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
    from tradingagents.agents.risk_mgmt.conservative_debator import create_conservative_debator
    from tradingagents.agents.risk_mgmt.neutral_debator import create_neutral_debator
    from tradingagents.agents.trader.trader import create_trader

    return {
        "create_aggressive_debator": create_aggressive_debator,
        "create_bear_researcher": create_bear_researcher,
        "create_bull_researcher": create_bull_researcher,
        "create_conservative_debator": create_conservative_debator,
        "create_fundamentals_analyst": create_fundamentals_analyst,
        "create_macro_analyst": create_macro_analyst,
        "create_market_analyst": create_market_analyst,
        "create_neutral_debator": create_neutral_debator,
        "create_news_analyst": create_news_analyst,
        "create_research_manager": create_research_manager,
        "create_risk_manager": create_risk_manager,
        "create_smart_money_analyst": create_smart_money_analyst,
        "create_social_media_analyst": create_social_media_analyst,
        "create_volume_price_analyst": create_volume_price_analyst,
        "create_sector_rotation_analyst": create_sector_rotation_analyst,
        "create_anti_quant_trap_analyst": create_anti_quant_trap_analyst,
        "create_trader": create_trader,
    }


class WorkflowV2:
    CORE_ANALYSTS = [
        "market",
        "volume_price",
        "fundamentals",
        "smart_money",
        "macro",
        "news",
        "social",
    ]

    SPECIAL_ANALYSTS = [
        "sector_rotation",
        "anti_quant_trap",
    ]

    ANALYST_DISPLAY_NAMES = {
        "market": "技术面",
        "volume_price": "量价",
        "fundamentals": "基本面",
        "smart_money": "主力资金",
        "macro": "宏观",
        "news": "新闻",
        "social": "舆情",
        "sector_rotation": "行业轮动",
        "anti_quant_trap": "防量化陷阱",
    }

    def __init__(
        self,
        quick_thinking_llm,
        deep_thinking_llm,
        tool_nodes,
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        data_collector=None,
        risk_profile: str = "neutral",
        max_debate_rounds: int = 1,
        max_risk_discuss_rounds: int = 1,
    ):
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.data_collector = data_collector
        self.risk_profile = risk_profile
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds
        self.factories = _load_agent_factories()

    def setup_sequential_graph(self, selected_analysts: Optional[List[str]] = None):
        workflow = StateGraph(AgentState)

        core_analysts = [a for a in self.CORE_ANALYSTS if a in (selected_analysts or self.CORE_ANALYSTS)]
        special_analysts = [a for a in self.SPECIAL_ANALYSTS if a in (selected_analysts or self.SPECIAL_ANALYSTS)]

        analyst_nodes = {}
        tool_nodes_map = {}

        for analyst_type in core_analysts:
            if analyst_type == "market":
                analyst_nodes["market"] = self.factories["create_market_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["market"] = self.tool_nodes["market"]
            elif analyst_type == "volume_price":
                analyst_nodes["volume_price"] = self.factories["create_volume_price_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["volume_price"] = self.tool_nodes.get("volume_price", self.tool_nodes["market"])
            elif analyst_type == "fundamentals":
                analyst_nodes["fundamentals"] = self.factories["create_fundamentals_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["fundamentals"] = self.tool_nodes["fundamentals"]
            elif analyst_type == "smart_money":
                analyst_nodes["smart_money"] = self.factories["create_smart_money_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["smart_money"] = self.tool_nodes["smart_money"]
            elif analyst_type == "macro":
                analyst_nodes["macro"] = self.factories["create_macro_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["macro"] = self.tool_nodes["macro"]
            elif analyst_type == "news":
                analyst_nodes["news"] = self.factories["create_news_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["news"] = self.tool_nodes["news"]
            elif analyst_type == "social":
                analyst_nodes["social"] = self.factories["create_social_media_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["social"] = self.tool_nodes.get("social", self.tool_nodes["news"])

        for analyst_type in special_analysts:
            if analyst_type == "sector_rotation":
                analyst_nodes["sector_rotation"] = self.factories["create_sector_rotation_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["sector_rotation"] = self.tool_nodes.get("macro", self.tool_nodes["news"])
            elif analyst_type == "anti_quant_trap":
                analyst_nodes["anti_quant_trap"] = self.factories["create_anti_quant_trap_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["anti_quant_trap"] = self.tool_nodes.get("smart_money", self.tool_nodes["market"])

        bull_researcher_node = self.factories["create_bull_researcher"](
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = self.factories["create_bear_researcher"](
            self.quick_thinking_llm, self.bear_memory
        )
        research_manager_node = self.factories["create_research_manager"](
            self.deep_thinking_llm, self.invest_judge_memory
        )
        trader_node = self.factories["create_trader"](self.quick_thinking_llm, self.trader_memory)

        aggressive_debator_node = self.factories["create_aggressive_debator"](self.quick_thinking_llm)
        neutral_debator_node = self.factories["create_neutral_debator"](self.quick_thinking_llm)
        conservative_debator_node = self.factories["create_conservative_debator"](self.quick_thinking_llm)

        portfolio_manager_node = self.factories["create_risk_manager"](
            self.deep_thinking_llm, self.risk_manager_memory
        )

        def _add_analyst_node(workflow: StateGraph, analyst_key: str, display_name: str):
            workflow.add_node(f"{display_name} Analyst", analyst_nodes[analyst_key])
            workflow.add_node(f"tools_{analyst_key}", tool_nodes_map[analyst_key])

        for analyst_key in core_analysts:
            display_name = self.ANALYST_DISPLAY_NAMES.get(analyst_key, analyst_key)
            _add_analyst_node(workflow, analyst_key, display_name)

        for analyst_key in special_analysts:
            display_name = self.ANALYST_DISPLAY_NAMES.get(analyst_key, analyst_key)
            _add_analyst_node(workflow, analyst_key, display_name)

        workflow.add_node("多头", bull_researcher_node)
        workflow.add_node("空头", bear_researcher_node)
        workflow.add_node("研究总监", research_manager_node)
        workflow.add_node("交易员", trader_node)
        workflow.add_node("激进风控", aggressive_debator_node)
        workflow.add_node("中性风控", neutral_debator_node)
        workflow.add_node("稳健风控", conservative_debator_node)
        workflow.add_node("组合经理", portfolio_manager_node)

        core_analyst_display_names = [
            f"{self.ANALYST_DISPLAY_NAMES.get(a, a)} Analyst" for a in core_analysts
        ]

        for analyst_node in core_analyst_display_names:
            workflow.add_edge(START, analyst_node)

        for analyst_key in core_analysts:
            display_name = self.ANALYST_DISPLAY_NAMES.get(analyst_key, analyst_key)
            analyst_node = f"{display_name} Analyst"
            tool_node = f"tools_{analyst_key}"
            workflow.add_conditional_edges(
                analyst_node,
                self._create_analyst_tool_router(tool_node),
                {
                    "continue": tool_node,
                    "next": "多头",
                },
            )
            workflow.add_edge(tool_node, analyst_node)

        special_analyst_display_names = [
            f"{self.ANALYST_DISPLAY_NAMES.get(a, a)} Analyst" for a in special_analysts
        ]
        for analyst_node in special_analyst_display_names:
            workflow.add_edge(START, analyst_node)

        for analyst_key in special_analysts:
            display_name = self.ANALYST_DISPLAY_NAMES.get(analyst_key, analyst_key)
            analyst_node = f"{display_name} Analyst"
            tool_node = f"tools_{analyst_key}"
            workflow.add_conditional_edges(
                analyst_node,
                self._create_analyst_tool_router(tool_node),
                {
                    "continue": tool_node,
                    "next": "研究总监",
                },
            )
            workflow.add_edge(tool_node, analyst_node)

        def all_core_analysts_completed(state: AgentState) -> str:
            messages = state["messages"]
            analyst_names = [self.ANALYST_DISPLAY_NAMES.get(a, a) for a in core_analysts]
            completed_analysts = set()

            for msg in messages:
                content = getattr(msg, "content", "") or ""
                for name in analyst_names:
                    if f"{name}分析" in content or f"{name}报告" in content or name in content[:100]:
                        completed_analysts.add(name)

            if len(completed_analysts) >= len(core_analysts):
                return "bull"
            return "wait"

        workflow.add_conditional_edges(
            "多头",
            self._create_debate_router("bull"),
            {
                "bear": "空头",
                "research_manager": "研究总监",
            },
        )

        workflow.add_conditional_edges(
            "空头",
            self._create_debate_router("bear"),
            {
                "bull": "多头",
                "research_manager": "研究总监",
            },
        )

        workflow.add_conditional_edges(
            "研究总监",
            self._create_research_manager_router(),
            {
                "trader": "交易员",
                "reject": END,
            },
        )

        workflow.add_edge("交易员", "激进风控")
        workflow.add_edge("交易员", "中性风控")
        workflow.add_edge("交易员", "稳健风控")

        workflow.add_edge("激进风控", "组合经理")
        workflow.add_edge("中性风控", "组合经理")
        workflow.add_edge("稳健风控", "组合经理")

        workflow.add_edge("组合经理", END)

        return workflow.compile()

    def _create_analyst_tool_router(self, tool_node: str) -> Callable:
        def router(state: AgentState):
            messages = state["messages"]
            if not messages:
                return "next"
            last_message = messages[-1]
            if getattr(last_message, "tool_calls", None):
                return "continue"
            return "next"

        return router

    def _create_debate_router(self, speaker: str) -> Callable:
        def router(state: AgentState):
            debate_state = state.get("investment_debate_state", {})
            count = debate_state.get("count", 0)
            max_rounds = 2 * self.max_debate_rounds

            if count >= max_rounds:
                return "research_manager"

            if speaker == "bull":
                return "bear"
            return "bull"

        return router

    def _create_research_manager_router(self) -> Callable:
        def router(state: AgentState):
            messages = state["messages"]
            if not messages:
                return "reject"

            last_message = messages[-1]
            content = getattr(last_message, "content", "") or ""

            if "REJECT" in content or "reject" in content.lower():
                state["circuit_breaker"] = {
                    "triggered": True,
                    "reason": "研究总监裁定逻辑不成立",
                    "analyst": "研究总监",
                }
                return "reject"

            return "trader"

        return router

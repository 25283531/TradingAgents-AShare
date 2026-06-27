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
    ANALYST_ORDER = [
        "market",
        "volume_price",
        "anti_quant_trap",
        "fundamentals",
        "smart_money",
        "macro",
        "news",
        "social",
        "sector_rotation",
    ]

    ANALYST_DISPLAY_NAMES = {
        "market": "技术面",
        "volume_price": "量价",
        "anti_quant_trap": "防量化陷阱",
        "fundamentals": "基本面",
        "smart_money": "主力资金",
        "macro": "宏观",
        "news": "新闻",
        "social": "舆情",
        "sector_rotation": "行业轮动",
    }

    RESEARCH_ORDER = ["bull", "bear", "research_manager"]

    RESEARCH_DISPLAY_NAMES = {
        "bull": "多头",
        "bear": "空头",
        "research_manager": "研究总监",
    }

    EXECUTION_ORDER = ["trader", "risk_profile", "risk_manager"]

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

        if selected_analysts is None:
            selected_analysts = self.ANALYST_ORDER

        analyst_nodes = {}
        tool_nodes_map = {}

        for analyst_type in selected_analysts:
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
            elif analyst_type == "anti_quant_trap":
                analyst_nodes["anti_quant_trap"] = self.factories["create_anti_quant_trap_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["anti_quant_trap"] = self.tool_nodes.get("smart_money", self.tool_nodes["market"])
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
            elif analyst_type == "sector_rotation":
                analyst_nodes["sector_rotation"] = self.factories["create_sector_rotation_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["sector_rotation"] = self.tool_nodes.get("macro", self.tool_nodes["news"])

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

        risk_profile_node = self._create_risk_profile_node()
        risk_manager_node = self.factories["create_risk_manager"](
            self.deep_thinking_llm, self.risk_manager_memory
        )

        def _add_analyst_node(workflow: StateGraph, analyst_key: str):
            display_name = self.ANALYST_DISPLAY_NAMES.get(analyst_key, analyst_key)
            workflow.add_node(f"{display_name} Analyst", analyst_nodes[analyst_key])
            workflow.add_node(f"tools_{analyst_key}", tool_nodes_map[analyst_key])

        for analyst_key in selected_analysts:
            _add_analyst_node(workflow, analyst_key)

        workflow.add_node("多头", bull_researcher_node)
        workflow.add_node("空头", bear_researcher_node)
        workflow.add_node("研究总监", research_manager_node)
        workflow.add_node("交易员", trader_node)
        workflow.add_node(self._risk_profile_display_name(), risk_profile_node)
        workflow.add_node("风控经理", risk_manager_node)

        prev_node = START
        for i, analyst_key in enumerate(selected_analysts):
            display_name = self.ANALYST_DISPLAY_NAMES.get(analyst_key, analyst_key)
            current_node = f"{display_name} Analyst"
            current_tool = f"tools_{analyst_key}"

            workflow.add_edge(prev_node, current_node)
            workflow.add_conditional_edges(
                current_node,
                self._create_analyst_router(analyst_key, current_tool),
                {
                    "continue": current_tool,
                    "next": self._get_next_analyst_node(selected_analysts, i),
                    "reject": END,
                },
            )
            workflow.add_edge(current_tool, current_node)
            prev_node = current_node

        workflow.add_edge(prev_node, "多头")

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

        workflow.add_edge("交易员", self._risk_profile_display_name())
        workflow.add_edge(self._risk_profile_display_name(), "风控经理")
        workflow.add_edge("风控经理", END)

        return workflow.compile()

    def _risk_profile_display_name(self) -> str:
        display_names = {
            "aggressive": "激进风控",
            "neutral": "中性风控",
            "conservative": "稳健风控",
        }
        return display_names.get(self.risk_profile, "中性风控")

    def _create_risk_profile_node(self):
        if self.risk_profile == "aggressive":
            return self.factories["create_aggressive_debator"](self.quick_thinking_llm)
        elif self.risk_profile == "conservative":
            return self.factories["create_conservative_debator"](self.quick_thinking_llm)
        else:
            return self.factories["create_neutral_debator"](self.quick_thinking_llm)

    def _get_next_analyst_node(self, analysts: List[str], current_idx: int) -> str:
        if current_idx + 1 < len(analysts):
            next_key = analysts[current_idx + 1]
            return f"{self.ANALYST_DISPLAY_NAMES.get(next_key, next_key)} Analyst"
        return "多头"

    def _create_analyst_router(self, analyst_key: str, tool_node: str) -> Callable:
        def router(state: AgentState):
            messages = state["messages"]
            if not messages:
                return "next"
            last_message = messages[-1]
            if getattr(last_message, "tool_calls", None):
                return "continue"

            content = getattr(last_message, "content", "") or ""
            content_lower = content.lower()

            if analyst_key == "market":
                circuit_patterns = [
                    "空头下跌通道已确认",
                    "触发熔断",
                    "[致命风险：空头下跌通道]",
                    "建议触发熔断",
                    "不具备中线配置价值",
                ]
                for pattern in circuit_patterns:
                    if pattern in content or pattern.lower() in content_lower:
                        state["circuit_breaker"] = {
                            "triggered": True,
                            "reason": "技术面发现致命风险：空头下跌通道",
                            "analyst": "技术面",
                        }
                        return "reject"

            if analyst_key == "volume_price":
                circuit_patterns = [
                    "派发阶段已确认",
                    "抛售高峰确认",
                    "局内人正在大量卖出",
                    "触发熔断",
                ]
                for pattern in circuit_patterns:
                    if pattern in content or pattern.lower() in content_lower:
                        state["circuit_breaker"] = {
                            "triggered": True,
                            "reason": "量价分析发现派发阶段或抛售高峰",
                            "analyst": "量价",
                        }
                        return "reject"

            if analyst_key == "anti_quant_trap":
                circuit_patterns = [
                    "风险等级为高",
                    "风险等级：高",
                    "高量化风险",
                    "[高量化风险]",
                    "<SYSTEM_REJECT>",
                    "建议直接剔除",
                    "触发熔断",
                    "存在高量化陷阱风险",
                ]
                for pattern in circuit_patterns:
                    if pattern in content or pattern.lower() in content_lower:
                        state["circuit_breaker"] = {
                            "triggered": True,
                            "reason": "防量化陷阱发现高量化风险",
                            "analyst": "防量化陷阱",
                        }
                        return "reject"

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
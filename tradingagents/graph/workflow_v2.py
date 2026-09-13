from typing import Dict, Any, List, Optional, Callable
import re
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
        "market": "Market",
        "volume_price": "Volume Price",
        "fundamentals": "Fundamentals",
        "smart_money": "Smart Money",
        "macro": "Macro",
        "news": "News",
        "social": "Social",
        "sector_rotation": "Sector Rotation",
        "anti_quant_trap": "Anti-Quant Trap",
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
        debate_llm=None,
        judge_llm=None,
        data_collector=None,
        risk_profile: str = "neutral",
        max_debate_rounds: int = 1,
        max_risk_discuss_rounds: int = 1,
        learning_config=None,
    ):
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.debate_llm = debate_llm or deep_thinking_llm
        self.judge_llm = judge_llm or deep_thinking_llm
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
        from tradingagents.rules.runtime import LearningRuntime
        self.learning = LearningRuntime(learning_config)

    def setup_sequential_graph(self, selected_analysts: Optional[List[str]] = None, checkpointer=None):
        workflow = StateGraph(AgentState)

        # Stage 1 is an ordered evidence relay.  A manager must never run while
        # one of its reports is still being generated.
        ordered = self.CORE_ANALYSTS + self.SPECIAL_ANALYSTS
        selected = selected_analysts if selected_analysts is not None else ordered
        if not selected:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")
        analysts = [a for a in ordered if a in selected]
        if not analysts:
            raise ValueError("Trading Agents Graph Setup Error: selected analysts are unknown")

        analyst_nodes = {}
        tool_nodes_map = {}

        for analyst_type in analysts:
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
            elif analyst_type == "sector_rotation":
                analyst_nodes["sector_rotation"] = self.factories["create_sector_rotation_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["sector_rotation"] = self.tool_nodes.get("macro", self.tool_nodes.get("news"))
            elif analyst_type == "anti_quant_trap":
                analyst_nodes["anti_quant_trap"] = self.factories["create_anti_quant_trap_analyst"](
                    self.quick_thinking_llm, self.data_collector
                )
                tool_nodes_map["anti_quant_trap"] = self.tool_nodes.get("smart_money", self.tool_nodes.get("market"))

        bull_researcher_node = self.factories["create_bull_researcher"](
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = self.factories["create_bear_researcher"](
            self.quick_thinking_llm, self.bear_memory
        )
        research_manager_node = self.factories["create_research_manager"](
            self.judge_llm, self.invest_judge_memory
        )
        trader_node = self.factories["create_trader"](self.quick_thinking_llm, self.trader_memory)

        aggressive_debator_node = self.factories["create_aggressive_debator"](self.debate_llm)
        neutral_debator_node = self.factories["create_neutral_debator"](self.debate_llm)
        conservative_debator_node = self.factories["create_conservative_debator"](self.debate_llm)

        portfolio_manager_node = self.factories["create_risk_manager"](
            self.judge_llm, self.risk_manager_memory
        )

        def _add_analyst_node(workflow: StateGraph, analyst_key: str, display_name: str):
            workflow.add_node(f"{display_name} Analyst", analyst_nodes[analyst_key])
            workflow.add_node(f"tools_{analyst_key}", tool_nodes_map[analyst_key])

        for analyst_key in analysts:
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

        first_display = self.ANALYST_DISPLAY_NAMES[analysts[0]]
        workflow.add_node("经验检索", self.learning.recall)
        workflow.add_node("预测归档", self.learning.archive)
        workflow.add_edge(START, "经验检索")
        workflow.add_edge("经验检索", f"{first_display} Analyst")
        workflow.add_edge("预测归档", END)
        for index, analyst_key in enumerate(analysts):
            display_name = self.ANALYST_DISPLAY_NAMES.get(analyst_key, analyst_key)
            analyst_node = f"{display_name} Analyst"
            tool_node = f"tools_{analyst_key}"
            done_node = f"{display_name} Analyst Done"
            workflow.add_node(done_node, lambda _state: {})
            workflow.add_conditional_edges(
                analyst_node,
                self._create_analyst_tool_router(tool_node),
                {
                    "continue": tool_node,
                    "next": done_node,
                },
            )
            workflow.add_edge(tool_node, analyst_node)
            next_node = (f"{self.ANALYST_DISPLAY_NAMES[analysts[index + 1]]} Analyst"
                         if index + 1 < len(analysts) else "多头")
            if analyst_key in {"market", "volume_price", "anti_quant_trap"}:
                gate_node = f"熔断检查_{analyst_key}"
                workflow.add_node(gate_node, self._create_circuit_breaker_gate(analyst_key))
                workflow.add_edge(done_node, gate_node)
                workflow.add_conditional_edges(gate_node, self._circuit_breaker_route,
                                               {"continue": next_node, "reject": "预测归档"})
                continue
            if index + 1 < len(analysts):
                workflow.add_edge(done_node, f"{self.ANALYST_DISPLAY_NAMES[analysts[index + 1]]} Analyst")
            else:
                workflow.add_edge(done_node, "多头")

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
                "reject": "预测归档",
            },
        )

        workflow.add_edge("交易员", "激进风控")
        workflow.add_conditional_edges("激进风控", self._create_risk_router("aggressive"),
                                       {"conservative": "稳健风控", "judge": "组合经理", "aggressive": "激进风控"})
        workflow.add_conditional_edges("稳健风控", self._create_risk_router("conservative"),
                                       {"neutral": "中性风控", "judge": "组合经理", "aggressive": "激进风控"})
        workflow.add_conditional_edges("中性风控", self._create_risk_router("neutral"),
                                       {"aggressive": "激进风控", "judge": "组合经理", "conservative": "稳健风控"})
        workflow.add_conditional_edges("组合经理", self._create_risk_judge_router,
                                       {"trader": "交易员", "end": "预测归档"})

        return workflow.compile(checkpointer=checkpointer)

    def _create_analyst_tool_router(self, tool_node: str) -> Callable:
        def router(state: AgentState):
            messages = state.get("messages", [])
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
            if (state.get("circuit_breaker") or {}).get("triggered"):
                return "reject"
            content = state.get("investment_plan", "")
            if not content:
                return "reject"

            if ("该股投资逻辑不成立" in content or
                    re.search(r"(?:最终裁定|熔断结论|决策)\s*[:：]\s*(?:reject|拒绝|剔除)", content, re.I)):
                state["circuit_breaker"] = {
                    "triggered": True,
                    "reason": "研究总监裁定逻辑不成立",
                    "analyst": "研究总监",
                }
                return "reject"

            return "trader"

        return router

    def _create_risk_router(self, speaker: str) -> Callable:
        """Advance risk debate in Aggressive → Conservative → Neutral order."""
        def router(state: AgentState):
            debate = state.get("risk_debate_state", {})
            if int(debate.get("count", 0) or 0) >= 3 * self.max_risk_discuss_rounds:
                return "judge"
            return {"aggressive": "conservative", "conservative": "neutral", "neutral": "aggressive"}[speaker]
        return router

    @staticmethod
    def _create_risk_judge_router(state: AgentState) -> str:
        feedback = state.get("risk_feedback_state", {}) or {}
        verdict = str(feedback.get("latest_risk_verdict", "")).lower()
        retries = int(feedback.get("retry_count", 0) or 0)
        max_retries = int(feedback.get("max_retries", 1))
        return "trader" if verdict == "revise" and retries <= max_retries else "end"

    @staticmethod
    def _circuit_breaker_route(state: AgentState) -> str:
        return "reject" if (state.get("circuit_breaker") or {}).get("triggered") else "continue"

    @staticmethod
    def _create_circuit_breaker_gate(analyst_key: str) -> Callable:
        report_keys = {
            "market": ("market_report", r"空头下跌通道已确认", "技术面确认空头下跌通道"),
            "volume_price": ("volume_price_report", r"派发阶段已确认", "量价分析确认派发阶段"),
            "anti_quant_trap": ("anti_quant_report", r"风险等级\s*[：:]\s*高|高量化陷阱风险|建议直接剔除", "量化陷阱风险等级为高"),
        }
        report_key, pattern, reason = report_keys[analyst_key]
        def gate(state: AgentState):
            report = str(state.get(report_key, "") or "")
            if re.search(pattern, report, flags=re.IGNORECASE):
                return {"circuit_breaker": {"triggered": True, "reason": reason, "analyst": analyst_key}}
            return {"circuit_breaker": {"triggered": False}}
        return gate

"""
LangGraph 主工作流 — 多 Agent 协同编排引擎

工作流拓扑:

  [用户输入]
       │
       ▼
  [需求解析] ──→ 结构化 TravelRequest
       │
       ├──────────────────────────┐
       ▼                          ▼
  [调研 Agent]              (可并行扩展)
       │
       ├──────────────────────────┐
       ▼                          ▼
  [行程规划]                  [预算计算]
       │                          │
       ├──────────────────────────┤
       ▼                          ▼
  [避坑攻略 Agent]           [文案 Agent]
       │                          │
       └──────────┬───────────────┘
                  ▼
          [汇总导出]
                  │
                  ▼
          [用户反馈?] ──→ 是 → 回到行程规划
                  │
                 否 ↓
              [完成]
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from workflows.state import AgentState
from agents.research_agent import ResearchAgent
from agents.planning_agent import PlanningAgent
from agents.budget_agent import BudgetAgent
from agents.tips_agent import TipsAgent
from agents.copywriting_agent import CopywritingAgent

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# 节点函数 — 每个函数对应图中的一个处理节点
# ═══════════════════════════════════════════════════════


def parse_request_node(state: AgentState) -> dict:
    """
    节点 1: 需求解析
    将用户自然语言输入解析为结构化的 TravelRequest
    """
    from models.schemas import TravelRequest, TravelStyle

    raw_input = state.get("raw_input", "")
    user_request = state.get("user_request")

    # 如果已经有 user_request（如来自前端表单），跳过解析
    if user_request is not None:
        return {
            "current_stage": "parsed",
            "messages": ["📋 需求已获取"],
        }

    # 否则用 LLM 解析自然语言
    if not raw_input:
        return {
            "errors": ["未收到任何输入"],
            "current_stage": "error",
        }

    from agents.base import create_llm
    llm = create_llm(temperature=0.1)

    parse_prompt = f"""请从以下用户输入中提取旅行需求，输出 JSON:

用户输入: "{raw_input}"

输出格式:
```json
{{
  "destination": "城市名",
  "days": 天数,
  "travelers": 人数,
  "budget_total": 预算金额(元),
  "style": "穷游/轻奢/亲子/美食/拍照打卡/人文历史/休闲度假",
  "departure_city": "出发城市",
  "start_date": "YYYY-MM-DD",
  "special_requirements": ["特殊需求1", "特殊需求2"]
}}
```

如果某些字段用户未提及，使用合理默认值:
- days: 3
- travelers: 1
- budget_total: 0 (不限)
- style: "穷游"
- departure_city: ""
"""

    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=parse_prompt)])
        # 提取 JSON
        text = response.content
        import json
        json_str = text
        if "```json" in text:
            json_str = text[text.index("```json") + 7:text.index("```", text.index("```json") + 7)]
        elif "```" in text:
            json_str = text[text.index("```") + 3:text.index("```", text.index("```") + 3)]
        data = json.loads(json_str.strip())

        travel_request = TravelRequest(
            destination=data.get("destination", "杭州"),
            days=data.get("days", 3),
            travelers=data.get("travelers", 1),
            budget_total=data.get("budget_total", 0),
            style=TravelStyle(data.get("style", "穷游")),
            departure_city=data.get("departure_city", ""),
            start_date=data.get("start_date", ""),
            special_requirements=data.get("special_requirements", []),
            raw_input=raw_input,
        )

        return {
            "user_request": travel_request,
            "current_stage": "parsed",
            "messages": [f"✅ 需求解析完成: {travel_request.destination} {travel_request.days}日游, "
                        f"{travel_request.travelers}人, {travel_request.style.value}风格"],
        }
    except Exception as e:
        logger.error(f"需求解析失败: {e}")
        return {
            "errors": [f"需求解析失败: {str(e)}"],
            "current_stage": "error",
        }


def research_node(state: AgentState) -> dict:
    """节点 2: 调研 — 搜集目的地全方位信息"""
    agent = ResearchAgent()
    result = agent.invoke(state)
    return result


def planning_node(state: AgentState) -> dict:
    """节点 3: 行程规划 — 编排每日活动"""
    agent = PlanningAgent()
    result = agent.invoke(state)
    return result


def budget_node(state: AgentState) -> dict:
    """节点 4: 预算计算 — 生成明细预算表"""
    agent = BudgetAgent()
    result = agent.invoke(state)
    return result


def tips_node(state: AgentState) -> dict:
    """节点 5: 避坑攻略 — 输出避坑指南、物品清单、拍照攻略、应急预案"""
    agent = TipsAgent()
    result = agent.invoke(state)
    return result


def copywriting_node(state: AgentState) -> dict:
    """节点 6: 文案总结 — 生成行程总览和社交分享文案"""
    agent = CopywritingAgent()
    result = agent.invoke(state)
    return result


def finalize_node(state: AgentState) -> dict:
    """节点 7: 汇总 — 标记流程完成"""
    from models.schemas import TravelPlan

    daily_plans = state.get("daily_plans", [])
    overview = state.get("overview", "")

    return {
        "current_stage": "done",
        "messages": [
            f"🎉 旅行全案生成完毕！\n"
            f"   📅 {len(daily_plans)} 天详细行程\n"
            f"   💰 完整预算明细\n"
            f"   ⚠️ 避坑指南 + 拍照攻略\n"
            f"   📝 行程总览摘要\n"
            f"{'   ' + overview[:100] + '...' if overview else ''}"
        ],
    }


def user_feedback_node(state: AgentState) -> dict:
    """
    节点 8: 处理用户修改意见
    用户说 "去掉博物馆，多加两个美食店"，系统迭代修改行程
    """
    feedback = state.get("user_feedback", "")
    daily_plans = state.get("daily_plans", [])
    iteration = state.get("iteration_count", 0) + 1

    if not feedback:
        return {"current_stage": "done"}

    # 使用 LLM 根据反馈修改行程
    from agents.base import create_llm
    import json as _json
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = create_llm(temperature=0.7)

    sys_prompt = """你负责根据用户反馈修改旅行行程。用户会对当前行程提出修改意见，
请根据意见调整行程内容，输出修改后的完整行程 JSON。

输出格式 (与行程规划 Agent 一致):
```json
[{"day": 1, "theme": "...", "morning": [...], "afternoon": [...], "evening": [...], "meals": [...], "transport_notes": "...", "energy_level": "..."}]
```"""

    current_plan_json = _json.dumps(
        [d.model_dump() if hasattr(d, 'model_dump') else d for d in daily_plans],
        ensure_ascii=False, indent=2, default=str
    )

    user_msg = f"""
当前行程:
{current_plan_json}

用户修改意见: {feedback}

请输出修改后的完整行程 JSON。
"""

    try:
        response = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=user_msg)])

        from models.schemas import DayPlan
        json_str = response.content
        if "```json" in json_str:
            json_str = json_str[json_str.index("```json") + 7:json_str.index("```", json_str.index("```json") + 7)]
        elif "```" in json_str:
            json_str = json_str[json_str.index("```") + 3:json_str.index("```", json_str.index("```") + 3)]

        new_plans = [_json.loads(_json.dumps(d)) for d in _json.loads(json_str)]
        daily_plans = [DayPlan(**d) for d in new_plans]

        return {
            "daily_plans": daily_plans,
            "iteration_count": iteration,
            "user_feedback": "",
            "messages": [f"🔄 已根据反馈修改行程 (第 {iteration} 次迭代): {feedback}"],
            "current_stage": "planning_done",
        }
    except Exception as e:
        return {
            "errors": [f"行程修改失败: {str(e)}"],
            "messages": ["⚠️ 行程修改失败，请尝试用更具体的描述重新提交"],
            "iteration_count": iteration,
            "current_stage": "done",
        }


# ═══════════════════════════════════════════════════════
# 路由函数 — 决定流程分支走向
# ═══════════════════════════════════════════════════════


def route_after_parse(state: AgentState) -> Literal["research", END]:
    """解析完成后: 有错误则终止，否则进入调研"""
    if state.get("current_stage") == "error":
        return END
    return "research"


def route_after_research(state: AgentState) -> Literal["planning_and_budget", END]:
    """调研完成后: 进入规划+预算并行"""
    if state.get("errors"):
        return END
    return "planning_and_budget"


def route_after_tips(state: AgentState) -> Literal["copywriting", "feedback_check"]:
    """攻略完成后: 是否需要重新生成文案?"""
    return "copywriting"


def route_after_copywriting(state: AgentState) -> Literal["finalize", "planning"]:
    """文案完成后: 有反馈则回规划节点，否则汇总"""
    feedback = state.get("user_feedback", "")
    if feedback:
        return "planning"
    return "finalize"


def route_after_finalize(state: AgentState) -> Literal["feedback", END]:
    """汇总后: 是否需要迭代修改?"""
    feedback = state.get("user_feedback", "")
    if feedback and state.get("iteration_count", 0) < 5:
        return "feedback"
    return END


# ═══════════════════════════════════════════════════════
# 图构建
# ═══════════════════════════════════════════════════════


def build_graph() -> StateGraph:
    """
    构建 LangGraph 状态图

    返回编译后的 StateGraph，支持:
    - 从任意节点恢复执行 (checkpointer)
    - 多轮迭代修改
    - 并行执行规划+预算
    """
    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("parse", parse_request_node)
    workflow.add_node("research", research_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("budget", budget_node)
    workflow.add_node("tips", tips_node)
    workflow.add_node("copywriting", copywriting_node)
    workflow.add_node("finalize", finalize_node)
    workflow.add_node("feedback", user_feedback_node)

    # 设置入口
    workflow.set_entry_point("parse")

    # 添加边
    workflow.add_conditional_edges("parse", route_after_parse)
    workflow.add_edge("research", "planning")
    workflow.add_edge("planning", "budget")
    workflow.add_edge("budget", "tips")
    workflow.add_edge("tips", "copywriting")
    workflow.add_conditional_edges("copywriting", route_after_copywriting)
    workflow.add_conditional_edges("finalize", route_after_finalize)
    workflow.add_edge("feedback", "planning")  # 反馈后重新规划

    # 编译 (带内存 checkpointer，支持中断恢复)
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app


class TravelPlannerGraph:
    """
    LangGraph 工作流封装

    提供简洁的 API 供 Streamlit 前端调用，支持:
      - invoke: 同步阻塞，返回最终状态
      - stream: 生成器模式，逐节点产出中间结果供前端实时渲染
    """

    def __init__(self):
        self.graph = build_graph()

    # ── 同步模式 (CLI / 非流式 API) ──

    def run(self, user_input: str, thread_id: str = "default") -> AgentState:
        """从头运行完整流程 (同步阻塞)"""
        initial_state: AgentState = {
            "raw_input": user_input,
            "messages": [],
            "errors": [],
            "iteration_count": 0,
            "user_feedback": "",
            "current_stage": "init",
        }
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.invoke(initial_state, config)

    def run_with_request(self, travel_request, thread_id: str = "default") -> AgentState:
        """从结构化 TravelRequest 直接运行 (同步阻塞，跳过解析)"""
        initial_state: AgentState = {
            "user_request": travel_request,
            "messages": [],
            "errors": [],
            "iteration_count": 0,
            "user_feedback": "",
            "current_stage": "init",
        }
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.invoke(initial_state, config)

    # ── 流式模式 (前端实时渲染) ──

    def stream_run_with_request(self, travel_request, thread_id: str = "default"):
        """
        流式运行 — 每完成一个 Agent 节点就 yield 一次，前端实时更新

        Yields:
            {"node": "research", "update": {...state_partial...}}
            {"node": "planning", "update": {...state_partial...}}
            ...
        """
        initial_state: AgentState = {
            "user_request": travel_request,
            "messages": [],
            "errors": [],
            "iteration_count": 0,
            "user_feedback": "",
            "current_stage": "init",
        }
        config = {"configurable": {"thread_id": thread_id}}

        # stream_mode="updates": 每个节点完成后 yield {node_name: partial_state}
        for chunk in self.graph.stream(initial_state, config, stream_mode="updates"):
            # chunk 格式: {"research": {"research_result": ..., "messages": [...]}}
            node_name = list(chunk.keys())[0]
            update = chunk[node_name]
            yield {"node": node_name, "update": update}

    def stream_run(self, user_input: str, thread_id: str = "default"):
        """流式运行 (自然语言输入版)"""
        initial_state: AgentState = {
            "raw_input": user_input,
            "messages": [],
            "errors": [],
            "iteration_count": 0,
            "user_feedback": "",
            "current_stage": "init",
        }
        config = {"configurable": {"thread_id": thread_id}}
        for chunk in self.graph.stream(initial_state, config, stream_mode="updates"):
            node_name = list(chunk.keys())[0]
            update = chunk[node_name]
            yield {"node": node_name, "update": update}

    # ── 反馈迭代 ──

    def give_feedback(self, feedback: str, thread_id: str = "default") -> AgentState:
        """在已有方案基础上迭代修改"""
        config = {"configurable": {"thread_id": thread_id}}
        current_state = self.graph.get_state(config)
        if current_state is None or current_state.values is None:
            raise ValueError(f"未找到会话 {thread_id}，请先运行 run()")
        update = {"user_feedback": feedback}
        self.graph.update_state(config, update)
        return self.graph.invoke(None, config)


# ═══════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════

def create_travel_plan(user_input: str) -> dict:
    """
    一键生成旅行方案 (同步阻塞版本)

    适合 CLI 或 API 调用，返回完整的 TravelPlan 字典。
    """
    planner = TravelPlannerGraph()
    state = planner.run(user_input)

    from models.schemas import TravelPlan, BudgetTable, PitfallTips, PackingList, EmergencyPlan, PhotoGuide

    plan = TravelPlan(
        request=state.get("user_request"),
        daily_plans=state.get("daily_plans", []),
        budget=state.get("budget_table") or BudgetTable(),
        research=state.get("research_result"),
        pitfalls=state.get("pitfalls") or PitfallTips(),
        packing=state.get("packing_list") or PackingList(),
        emergency=state.get("emergency_plan") or EmergencyPlan(),
        photo_guide=state.get("photo_guide") or PhotoGuide(),
        overview=state.get("overview", ""),
    )

    return plan.model_dump()

"""
LangGraph State 定义

使用 TypedDict + Annotated 定义状态 schema，
支持 add reducer 用于消息列表的增量更新。
"""

from __future__ import annotations

from typing import TypedDict, Annotated, Optional
from operator import add

from models.schemas import (
    TravelRequest,
    ResearchResult,
    DayPlan,
    BudgetTable,
    PitfallTips,
    PackingList,
    EmergencyPlan,
    PhotoGuide,
)


class AgentState(TypedDict, total=False):
    """
    LangGraph 全局工作流状态

    每个节点返回部分更新，LangGraph 自动合并。
    使用 Annotated[list, add] 实现列表字段的增量追加。
    """

    # --- 用户输入 ---
    user_request: Optional[TravelRequest]
    raw_input: str

    # --- 各 Agent 产出 ---
    research_result: Optional[ResearchResult]
    daily_plans: list[DayPlan]
    budget_table: Optional[BudgetTable]
    pitfalls: Optional[PitfallTips]
    packing_list: Optional[PackingList]
    emergency_plan: Optional[EmergencyPlan]
    photo_guide: Optional[PhotoGuide]
    overview: str
    social_captions: list[str]

    # --- 流程控制 ---
    current_stage: str
    messages: Annotated[list[str], add]
    errors: Annotated[list[str], add]
    iteration_count: int
    user_feedback: str

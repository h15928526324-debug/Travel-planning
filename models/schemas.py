"""
核心数据模型 — 定义旅行规划中所有结构化数据

使用 Pydantic 保证类型安全，同时作为 LangGraph State 的序列化载体
"""

from __future__ import annotations

from datetime import time
from enum import Enum
from typing import Optional, Annotated
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════
# 枚举定义
# ══════════════════════════════════════════════

class TravelStyle(str, Enum):
    BUDGET = "穷游"
    LIGHT_LUXURY = "轻奢"
    FAMILY = "亲子"
    FOODIE = "美食"
    PHOTOGRAPHY = "拍照打卡"
    ADVENTURE = "探险"
    RELAXATION = "休闲度假"
    CULTURE = "人文历史"


class TransportMode(str, Enum):
    WALK = "步行"
    SUBWAY = "地铁"
    BUS = "公交"
    TAXI = "出租车/网约车"
    RENTAL_CAR = "租车自驾"
    HIGH_SPEED_RAIL = "高铁"
    FLIGHT = "飞机"


# ══════════════════════════════════════════════
# 用户输入
# ══════════════════════════════════════════════

class TravelRequest(BaseModel):
    """用户旅行需求 — 自然语言解析后的结构化表示"""
    destination: str = Field(..., description="目的地城市/国家")
    days: int = Field(..., ge=1, le=30, description="旅行天数")
    travelers: int = Field(default=1, ge=1, le=50, description="出行人数")
    budget_total: float = Field(default=0, ge=0, description="总预算(元)，0 表示不限")
    style: TravelStyle = Field(default=TravelStyle.BUDGET, description="出行风格")
    departure_city: str = Field(default="", description="出发城市")
    start_date: str = Field(default="", description="出发日期 YYYY-MM-DD")
    special_requirements: list[str] = Field(default_factory=list, description="特殊需求")
    raw_input: str = Field(default="", description="用户原始自然语言输入")


# ══════════════════════════════════════════════
# 调研结果
# ══════════════════════════════════════════════

class Activity(BaseModel):
    """单个活动/地点"""
    name: str
    category: str  # 景点 / 美食 / 购物 / 娱乐 / 交通
    description: str = ""
    address: str = ""
    duration_minutes: int = Field(default=60, ge=0, description="建议停留时间(分钟)")
    rating: float = Field(default=4.0, ge=0, le=5, description="评分")
    ticket_price: float = Field(default=0, ge=0, description="门票价格")
    tips: list[str] = Field(default_factory=list, description="小贴士")
    photo_spots: list[str] = Field(default_factory=list, description="拍照机位")
    must_try: list[str] = Field(default_factory=list, description="必体验项目")


class DayPlan(BaseModel):
    """单日行程"""
    day: int = Field(..., ge=1)
    date: str = Field(default="", description="日期 YYYY-MM-DD")
    theme: str = Field(default="", description="当日主题")
    morning: list[Activity] = Field(default_factory=list)
    afternoon: list[Activity] = Field(default_factory=list)
    evening: list[Activity] = Field(default_factory=list)
    transport_notes: str = Field(default="", description="当日交通建议")
    meals: list[dict] = Field(default_factory=list, description="推荐餐厅 [{meal_type, name, avg_cost}]")


class ResearchResult(BaseModel):
    """多 Agent 并行调研汇总结果"""
    attractions: list[Activity] = Field(default_factory=list, description="景点列表")
    foods: list[Activity] = Field(default_factory=list, description="美食列表")
    hotels: list[dict] = Field(default_factory=list, description="住宿推荐 [{name, area, price_range, pros, cons}]")
    weather: dict = Field(default_factory=dict, description="天气信息 {date, temp_high, temp_low, condition, tips}")
    transport: dict = Field(default_factory=dict, description="交通信息 {from_city, to_city, options: [{mode, duration, cost}]}")
    local_policies: list[str] = Field(default_factory=list, description="当地政策/须知")


# ══════════════════════════════════════════════
# 预算
# ══════════════════════════════════════════════

class BudgetItem(BaseModel):
    """单项预算"""
    category: str  # 交通 / 住宿 / 餐饮 / 门票 / 购物 / 其他
    item: str
    amount: float = Field(..., ge=0)
    per_person: bool = Field(default=False, description="是否按人均计算")
    notes: str = ""


class BudgetTable(BaseModel):
    """完整预算表"""
    items: list[BudgetItem] = Field(default_factory=list)
    total: float = Field(default=0, ge=0)
    per_person: float = Field(default=0, ge=0)
    contingency: float = Field(default=0, ge=0, description="应急备用金")
    savings_tips: list[str] = Field(default_factory=list, description="省钱建议")


# ══════════════════════════════════════════════
# 攻略 & 清单
# ══════════════════════════════════════════════

class PitfallTips(BaseModel):
    """避坑指南"""
    common_scams: list[str] = Field(default_factory=list, description="常见骗局")
    tourist_traps: list[str] = Field(default_factory=list, description="游客陷阱")
    transport_pitfalls: list[str] = Field(default_factory=list, description="交通避坑")
    food_safety: list[str] = Field(default_factory=list, description="饮食安全")
    cultural_taboos: list[str] = Field(default_factory=list, description="文化禁忌")


class PackingList(BaseModel):
    """必备物品清单"""
    essentials: list[str] = Field(default_factory=list, description="证件/钱/手机 等")
    clothing: list[str] = Field(default_factory=list)
    toiletries: list[str] = Field(default_factory=list)
    electronics: list[str] = Field(default_factory=list)
    medicine: list[str] = Field(default_factory=list)
    travel_specific: list[str] = Field(default_factory=list, description="目的地专属物品")


class EmergencyPlan(BaseModel):
    """应急预案"""
    emergency_contacts: dict[str, str] = Field(default_factory=dict, description="{报警, 急救, 使馆, ...}")
    nearest_hospital: str = ""
    backup_routes: list[str] = Field(default_factory=list, description="备用路线")
    rainy_day_plan: str = Field(default="", description="雨天备选方案")
    lost_items_procedure: str = Field(default="", description="物品遗失处理流程")


class PhotoGuide(BaseModel):
    """拍照打卡指南"""
    best_spots: list[dict] = Field(default_factory=list, description="[{name, best_time, pose_tips}]")
    outfit_suggestions: list[str] = Field(default_factory=list, description="穿搭建议")
    camera_settings: str = Field(default="", description="相机/手机参数建议")


# ══════════════════════════════════════════════
# 最终全案
# ══════════════════════════════════════════════

class TravelPlan(BaseModel):
    """最终旅行全案 — 全部 Agent 产出的汇总"""
    request: TravelRequest
    daily_plans: list[DayPlan] = Field(default_factory=list)
    budget: BudgetTable = Field(default_factory=BudgetTable)
    research: ResearchResult = Field(default_factory=ResearchResult)
    pitfalls: PitfallTips = Field(default_factory=PitfallTips)
    packing: PackingList = Field(default_factory=PackingList)
    emergency: EmergencyPlan = Field(default_factory=EmergencyPlan)
    photo_guide: PhotoGuide = Field(default_factory=PhotoGuide)
    overview: str = Field(default="", description="行程总览摘要")


# ══════════════════════════════════════════════
# LangGraph AgentState — 贯穿全流程的状态
# ══════════════════════════════════════════════

class AgentState(BaseModel):
    """
    LangGraph 工作流全局状态

    每个节点读取此状态、处理后返回更新字段。
    LangGraph 自动合并 (reducer=add) 增量更新。
    """
    # --- 用户输入 ---
    user_request: TravelRequest | None = None
    raw_input: str = ""

    # --- 各 Agent 产出 (None 表示尚未执行) ---
    research_result: ResearchResult | None = None
    daily_plans: list[DayPlan] = []
    budget_table: BudgetTable | None = None
    pitfalls: PitfallTips | None = None
    packing_list: PackingList | None = None
    emergency_plan: EmergencyPlan | None = None
    photo_guide: PhotoGuide | None = None
    overview: str = ""

    # --- 流程控制 ---
    current_stage: str = "init"  # init → research → plan → budget → tips → export → done
    messages: list[str] = []      # 用户可见的进度消息
    errors: list[str] = []        # 错误收集
    iteration_count: int = 0      # 修改迭代次数
    user_feedback: str = ""       # 用户修改意见

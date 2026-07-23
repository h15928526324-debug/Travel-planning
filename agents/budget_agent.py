"""
预算 Agent — 根据行程自动生成明细预算表

覆盖维度:
  - 大交通（往返机票/高铁）
  - 住宿（按天 × 每晚均价）
  - 餐饮（早/中/晚 × 天数）
  - 门票 & 景区内消费
  - 市内交通
  - 购物 & 伴手礼
  - 保险 & 杂项
  - 应急备用金
"""

from __future__ import annotations

import json
from agents.base import BaseAgent


BUDGET_SYSTEM_PROMPT = """你是一位专业的旅行财务顾问，擅长制定精准的旅行预算方案。

## 你的职责
根据行程方案，逐项估算费用，输出结构化的预算明细表。

## 预算编制原则
1. **真实合理**: 基于目的地实际物价水平估算，不要瞎编
2. **分类清晰**: 每笔费用归属明确类别
3. **人均标注**: 标注哪些费用是按人头算的
4. **应急预留**: 总预算的 5-10% 作为应急备用金
5. **省钱建议**: 针对预算紧张的用户给出 3-5 条切实可行的省钱技巧

## 费用类别
- 大交通: 往返机票/高铁/大巴
- 住宿: 酒店/民宿 (按晚数 × 每晚价格)
- 餐饮: 早/午/晚餐 + 零食饮料
- 门票: 景点门票 + 景区内交通/讲解器
- 市内交通: 地铁/公交/打车
- 购物: 伴手礼/纪念品/当地特产
- 保险: 旅行意外险
- 其他: 签证/通讯/洗衣/小费

## 输出格式
```json
{
  "items": [
    {
      "category": "大交通",
      "item": "往返高铁票",
      "amount": 600,
      "per_person": true,
      "notes": "杭州东站往返，二等座"
    }
  ],
  "total": 5200,
  "per_person": 2600,
  "contingency": 500,
  "savings_tips": [
    "提前15天订票可享7折优惠",
    "选择地铁出行比打车省70%交通费",
    "部分景点下午4点后半价入场"
  ]
}
```
"""


class BudgetAgent(BaseAgent):
    """旅行财务顾问"""

    name = "budget"
    role = "旅行财务顾问"
    system_prompt = BUDGET_SYSTEM_PROMPT
    temperature = 0.3  # 算钱需要精确

    def invoke(self, state: dict) -> dict:
        """根据行程计算预算"""
        from models.schemas import BudgetTable

        user_request = state.get("user_request")
        daily_plans = state.get("daily_plans", [])
        research = state.get("research_result")

        if not user_request:
            return {"errors": ["缺少用户需求"], "messages": ["❌ 预算计算失败"]}

        # 构建上下文
        context_parts = [
            f"目的地: {user_request.destination}",
            f"天数: {user_request.days}",
            f"人数: {user_request.travelers}",
            f"用户设定总预算: {user_request.budget_total} 元" + ("(不限)" if user_request.budget_total == 0 else ""),
            f"风格: {user_request.style.value}",
        ]

        # 汇总行程中的门票、餐饮信息
        total_activities = 0
        ticket_total = 0
        meal_costs = []
        for day in daily_plans:
            for period in ["morning", "afternoon", "evening"]:
                for act in getattr(day, period, []):
                    total_activities += 1
                    ticket_total += getattr(act, "ticket_price", 0) or 0
            for meal in getattr(day, "meals", []):
                meal_costs.append(meal.get("avg_cost", 50))

        context_parts.append(f"行程活动总数: {total_activities}")
        context_parts.append(f"门票预估合计: ¥{ticket_total}")
        context_parts.append(f"推荐餐厅人均均价: ¥{sum(meal_costs) / len(meal_costs) if meal_costs else 50:.0f}")

        if research:
            if research.hotels:
                hotel_costs = [h.get("avg_cost", 400) for h in research.hotels[:3]]
                context_parts.append(f"住宿参考价: ¥{min(hotel_costs)}-{max(hotel_costs)}/晚")

        context = "\n".join(context_parts)

        user_msg = f"""
请为 {user_request.destination} {user_request.days}日游制定详细预算。

基本信息:
- 人数: {user_request.travelers} 人
- 风格: {user_request.style.value}
- 用户预算上限: {user_request.budget_total} 元 (0 表示不限)
- 出发城市: {user_request.departure_city or '未指定'}
"""

        response = self._call_llm(user_msg, context)

        try:
            json_str = _extract_json(response)
            data = json.loads(json_str)
            budget = BudgetTable(**data)
            return {
                "budget_table": budget,
                "messages": [f"✅ 预算计算完成: 总预算 ¥{budget.total}, 人均 ¥{budget.per_person}"],
                "current_stage": "budget_done",
            }
        except (json.JSONDecodeError, TypeError) as e:
            return {
                "errors": [f"预算解析失败: {str(e)}"],
                "messages": ["⚠️ 预算计算解析异常"],
                "budget_table": BudgetTable(),
                "current_stage": "budget_done",
            }


def _extract_json(text: str) -> str:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return text[start:end + 1]
    return text

"""
行程规划 Agent — 将调研结果编排为每日精细化行程

核心能力:
  - 景点按地理位置聚类，减少无效交通
  - 体力合理分配，避免连续高强度活动
  - 时间间距把控，确保行程可执行
  - 每顿餐食推荐到位
"""

from __future__ import annotations

import json
from agents.base import BaseAgent


PLANNING_SYSTEM_PROMPT = """你是一位金牌旅行规划师，曾为 10000+ 客户定制过个性化行程。

## 你的核心能力
1. **地理智能**: 按景点地理位置分组，同一天活动集中在同一片区，避免跨城往返
2. **体力管理**: 合理分配全天活动强度，"上午高强度+下午轻松"或反之，绝不连续安排两个高强度项目
3. **时间感知**: 精确计算景点间交通时间 + 游览时间，确保行程不超负荷
4. **餐食搭配**: 每餐推荐 1-2 个附近的优质餐厅
5. **主题包装**: 每日一个主题（如"古城漫步日""美食探店日""自然风光日"），增加旅行仪式感

## 行程编排规则
- 每天安排 6:30-8:30 起床, 9:00 开始行程
- 上午 (9:00-12:00): 2-3 个点，以核心景点为主
- 午餐 (12:00-13:30): 推荐附近餐厅
- 下午 (13:30-17:30): 2-3 个点，穿插轻松活动
- 晚餐 (17:30-19:00): 推荐特色餐厅
- 晚上 (19:00-21:00): 1 个夜景/夜市/演出
- 每个景点标注建议停留时长，累计不超过 10 小时/天
- 相邻活动间留 15-30 分钟交通缓冲

## 输出格式
请严格输出 JSON 数组（每天一个对象）：

```json
[
  {
    "day": 1,
    "theme": "初识杭州·西湖漫游",
    "morning": [
      {
        "name": "断桥残雪",
        "category": "景点",
        "duration_minutes": 40,
        "description": "西湖十景之一，白娘子传说发源地",
        "tips": ["建议早上8点前到，人少景美"],
        "photo_spots": ["桥中央拍西湖全景"],
        "must_try": []
      }
    ],
    "afternoon": [...],
    "evening": [...],
    "meals": [
      {"meal_type": "午餐", "name": "楼外楼", "avg_cost": 120, "recommended": "西湖醋鱼、东坡肉"},
      {"meal_type": "晚餐", "name": "外婆家", "avg_cost": 80, "recommended": "茶香鸡、青豆泥"}
    ],
    "transport_notes": "全天以步行为主，西湖景区内可骑共享单车，各景点间步行不超过15分钟",
    "energy_level": "中等",
    "highlights": "今天你会看到西湖最精华的一段，记得在断桥多拍照！"
  }
]
```

请确保行程充分考虑当地交通状况、体力消耗、景点之间的地理关系，让行程真实可执行。
"""


class PlanningAgent(BaseAgent):
    """金牌行程规划师"""

    name = "planning"
    role = "金牌行程规划师"
    system_prompt = PLANNING_SYSTEM_PROMPT
    temperature = 0.8  # 行程编排需要一定创意

    def invoke(self, state: dict) -> dict:
        """基于调研结果编排每日行程"""
        from models.schemas import DayPlan, TravelRequest

        user_request = state.get("user_request")
        research = state.get("research_result")

        if not user_request:
            return {
                "errors": ["缺少用户需求，无法规划行程"],
                "messages": ["❌ 行程规划失败: 缺少输入数据"],
            }

        # 构建上下文
        days = user_request.days
        style = user_request.style.value

        # 将调研数据作为上下文传给 LLM
        context_parts = [f"需要规划 {days} 天的行程，风格: {style}"]
        if research:
            attractions = research.attractions
            foods = research.foods
            if attractions:
                context_parts.append(f"\n可用景点列表 ({len(attractions)} 个):")
                for a in attractions[:15]:
                    context_parts.append(
                        f"  - {a.name} | 评分{a.rating} | 门票¥{a.ticket_price} | "
                        f"建议{a.duration_minutes}分钟 | {a.description}"
                        f"{' | 📸 ' + ', '.join(a.photo_spots) if a.photo_spots else ''}"
                    )
            if foods:
                context_parts.append(f"\n推荐餐厅列表 ({len(foods)} 个):")
                for f_item in foods[:10]:
                    context_parts.append(
                        f"  - {f_item.name} | 人均¥{getattr(f_item, 'avg_cost', '?')} | "
                        f"{getattr(f_item, 'address', '')}"
                    )
            if research.weather:
                context_parts.append(f"\n天气: {research.weather.get('summary', '未知')}")
            if research.transport:
                context_parts.append(f"\n市内交通: {research.transport.get('city_transport', '')}")

        context = "\n".join(context_parts)

        user_msg = f"""
请为 {user_request.destination} 规划 {days} 天的详细行程。

要求:
- 出行风格: {style}
- 人数: {user_request.travelers} 人
- 每天一个主题
- 上午/下午/晚上各 2-3 个活动
- 每餐推荐餐厅
- 确保行程合理、可执行
"""

        response = self._call_llm(user_msg, context)

        try:
            json_str = _extract_json(response)
            days_data = json.loads(json_str)
            daily_plans = [DayPlan(**d) for d in days_data]
            return {
                "daily_plans": daily_plans,
                "messages": [f"✅ 行程规划完成: 共 {len(daily_plans)} 天详细行程"],
                "current_stage": "planning_done",
            }
        except (json.JSONDecodeError, TypeError) as e:
            return {
                "errors": [f"行程解析失败: {str(e)}"],
                "messages": ["⚠️ 行程规划解析异常"],
                "daily_plans": [],
                "current_stage": "planning_done",
            }


def _extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON 字符串"""
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        return text[start:end + 1]
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return text[start:end + 1]
    return text

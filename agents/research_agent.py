"""
调研 Agent — 负责目的地的全方位信息搜集

并行调研维度：
  - 热门景点 & 评分
  - 特色美食 & 餐厅
  - 住宿推荐 & 区域分析
  - 天气预报 & 穿衣建议
  - 城际交通方案
  - 当地政策 & 签证
"""

from __future__ import annotations

import json
from agents.base import BaseAgent, create_llm


RESEARCH_SYSTEM_PROMPT = """你是一位资深旅行调研专家，拥有全球 100+ 城市的一手旅行情报。

## 你的职责
针对用户的目的地，进行全方位调研，输出结构化的调研报告。

## 调研维度（逐一覆盖）
1. **🏛️ 热门景点**: 列出 TOP 10 景点，标注评分、门票、建议时长、必体验项目、拍照机位
2. **🍜 特色美食**: 推荐必吃美食及对应的口碑餐厅，标注人均消费
3. **🏨 住宿推荐**: 按区域推荐 3-5 个酒店/民宿，标注价格区间和优缺点
4. **🌤️ 天气**: 根据出行日期提供天气预报及穿衣/打包建议
5. **🚗 交通**: 从出发城市到目的地的最佳交通方式，以及市内交通建议
6. **📋 政策**: 是否需要签证、当地防疫/安全政策、货币/支付方式

## 输出要求
请严格按照以下 JSON 格式输出（不要输出其他内容）：

```json
{
  "attractions": [
    {
      "name": "景点名",
      "category": "景点",
      "rating": 4.5,
      "ticket_price": 60,
      "duration_minutes": 120,
      "description": "一句话介绍",
      "tips": ["建议早上去人少", "门口有讲解器租"],
      "photo_spots": ["大门左侧石狮子处", "后山观景台"],
      "must_try": ["必体验项目1", "必体验项目2"]
    }
  ],
  "foods": [
    {
      "name": "餐厅/美食名",
      "category": "美食",
      "avg_cost": 80,
      "must_try": ["招牌菜1", "招牌菜2"],
      "address": "地址",
      "tips": ["需要排队", "下午 2-5 点休息"]
    }
  ],
  "hotels": [
    {
      "name": "酒店名",
      "area": "区域",
      "price_range": "300-500元/晚",
      "avg_cost": 400,
      "pros": ["交通便利", "含早餐"],
      "cons": ["隔音一般"],
      "distance_to_center": "距离市中心 3km"
    }
  ],
  "weather": {
    "summary": "出行期间天气总体状况描述",
    "temperature_range": "26°C ~ 35°C",
    "condition": "晴转多云，偶有雷阵雨",
    "clothing_advice": "建议携带轻薄透气衣物，备防晒和雨具",
    "best_travel_time": "春秋季最佳，当前出行需要注意..."
  },
  "transport": {
    "from_city_to_dest": {
      "recommended": "高铁",
      "options": [
        {"mode": "高铁", "duration": "约4.5小时", "cost": "约300元/人"},
        {"mode": "飞机", "duration": "约2小时+机场交通", "cost": "约600元/人"}
      ]
    },
    "city_transport": "市内交通建议：地铁为主，景点间可打车，预计每日交通费50元以内"
  },
  "local_policies": [
    "无需签证，携带身份证即可",
    "当地支持微信/支付宝支付",
    "部分景点需提前预约，建议至少提前3天",
    "当地治安良好，注意保管随身物品"
  ],
  "travel_highlights": "该目的地最值得体验的 3-5 个亮点总结"
}
```

请确保所有信息准确、实用、接地气，站在旅行者角度思考。
"""


class ResearchAgent(BaseAgent):
    """旅行调研专家"""

    name = "research"
    role = "旅行调研专家"
    system_prompt = RESEARCH_SYSTEM_PROMPT
    temperature = 0.5  # 调研需要更准确的信息

    def invoke(self, state: dict) -> dict:
        """
        执行调研任务。

        从 state 中提取用户需求，输出 ResearchResult。
        """
        from models.schemas import ResearchResult

        user_request = state.get("user_request")
        raw_input = state.get("raw_input", "")

        if user_request:
            req = user_request
            user_msg = f"""
请为以下旅行需求进行调研：

- 目的地: {req.destination}
- 出行天数: {req.days} 天
- 出行人数: {req.travelers} 人
- 出行风格: {req.style.value}
- 出发城市: {req.departure_city or '未指定'}
- 出行日期: {req.start_date or '未指定'}
- 总预算: {req.budget_total} 元 (0 表示不限)
- 特殊需求: {', '.join(req.special_requirements) if req.special_requirements else '无'}
"""
        else:
            user_msg = raw_input or "请调研杭州的旅行信息"

        context = f"当前阶段: 调研阶段\n目的地: {user_request.destination if user_request else '待确认'}"
        response = self._call_llm(user_msg, context)

        # 解析 JSON 输出
        try:
            json_str = _extract_json(response)
            data = json.loads(json_str)
            research_result = ResearchResult(
                attractions=data.get("attractions", []),
                foods=data.get("foods", []),
                hotels=data.get("hotels", []),
                weather=data.get("weather", {}),
                transport=data.get("transport", {}),
                local_policies=data.get("local_policies", []),
            )
            return {
                "research_result": research_result,
                "messages": [f"✅ 调研完成: 获取 {len(research_result.attractions)} 个景点, "
                            f"{len(research_result.foods)} 个美食, {len(research_result.hotels)} 个住宿推荐"],
                "current_stage": "research_done",
            }
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return {
                "errors": [f"调研结果解析失败: {str(e)}"],
                "messages": [f"⚠️ 调研结果解析异常，将使用默认数据"],
                # 返回空的 ResearchResult 保证流程不中断
                "research_result": ResearchResult(),
                "current_stage": "research_done",
            }


def _extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON 字符串"""
    # 尝试提取 ```json ... ``` 代码块
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()

    # 尝试找到 { 和 } 的边界
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return text[start:end + 1]

    return text

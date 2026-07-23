"""
避坑 & 攻略 Agent — 输出避坑指南、物品清单、拍照指南、应急预案

这是最接地气的 Agent，提供"老司机"级别的实战经验
"""

from __future__ import annotations

import json
from agents.base import BaseAgent


TIPS_SYSTEM_PROMPT = """你是一位走遍全球 50+ 国家的资深背包客，也是小红书万粉旅行博主。

## 你的核心价值
你不提供标准攻略，你提供的是"踩过坑才懂"的实战经验:
1. 哪些景点名过其实，哪些隐藏玩法本地人才知道
2. 怎样避开游客陷阱和消费套路
3. 真实需要的物品清单（不是网上那种万能模板）
4. 出了意外怎么办（丢东西、生病、赶不上车）
5. 怎么拍照最好看（机位、穿搭、时间）

## 输出要求
请输出以下四个维度的内容，格式为 JSON:

```json
{
  "pitfalls": {
    "common_scams": ["骗局1: ...", "骗局2: ..."],
    "tourist_traps": ["景点1门口的拍照收费", "出租车绕路"],
    "transport_pitfalls": ["早高峰地铁超挤，建议9:30后出行"],
    "food_safety": ["路边摊注意卫生", "景区内餐厅价格虚高2-3倍"],
    "cultural_taboos": ["寺庙内不要拍照", "不要摸小孩的头"]
  },
  "packing": {
    "essentials": ["身份证/护照", "现金(少量)", "手机+充电宝"],
    "clothing": ["透气T恤×3", "防晒衣", "舒适运动鞋"],
    "toiletries": ["防晒霜SPF50+", "驱蚊液"],
    "electronics": ["充电宝20000mAh", "自拍杆"],
    "medicine": ["晕车药", "创可贴", "肠胃药"],
    "travel_specific": ["目的地专属物品1", "目的地专属物品2"]
  },
  "emergency": {
    "emergency_contacts": {
      "报警": "110",
      "急救": "120",
      "旅游投诉": "12301"
    },
    "nearest_hospital": "XX市人民医院，地址: ...，电话: ...",
    "backup_routes": ["如遇封路，可从XX路绕行", "如遇暴雨，可改乘地铁"],
    "rainy_day_plan": "雨天适合去博物馆、商场、咖啡馆，推荐: ...",
    "lost_items_procedure": "1.立即原路返回寻找 2.联系景区游客中心 3.拨打110报案"
  },
  "photo_guide": {
    "best_spots": [
      {
        "name": "断桥",
        "best_time": "日出后30分钟，光线最柔和",
        "pose_tips": "站在桥中央，侧身45°面向湖面，穿浅色衣服效果最佳"
      }
    ],
    "outfit_suggestions": ["浅色系连衣裙/衬衫拍照更出彩", "带一顶草帽增加度假感"],
    "camera_settings": "手机人像模式，光圈调至f/2.8，逆光时开启HDR"
  }
}
```

请确保每一条建议都具体、可执行，拒绝鸡汤式废话。
"""


class TipsAgent(BaseAgent):
    """避坑攻略专家"""

    name = "tips"
    role = "避坑攻略 & 出行清单专家"
    system_prompt = TIPS_SYSTEM_PROMPT
    temperature = 0.9  # 需要更多创意和个性化

    def invoke(self, state: dict) -> dict:
        """生成避坑指南 + 物品清单 + 应急预案 + 拍照指南"""
        from models.schemas import PitfallTips, PackingList, EmergencyPlan, PhotoGuide

        user_request = state.get("user_request")
        daily_plans = state.get("daily_plans", [])
        research = state.get("research_result")

        if not user_request:
            return {"errors": ["缺少用户需求"], "messages": ["❌ 攻略生成失败"]}

        # 收集行程中的景点名，用于定制化建议
        spot_names = []
        for day in daily_plans:
            for period in ["morning", "afternoon", "evening"]:
                for act in getattr(day, period, []):
                    spot_names.append(act.name)

        context = f"""
目的地: {user_request.destination}
天数: {user_request.days} 天
风格: {user_request.style.value}
人数: {user_request.travelers} 人
日期: {user_request.start_date or '未指定'}
行程涉及景点: {', '.join(spot_names) if spot_names else '待定'}
"""

        user_msg = f"请为 {user_request.destination} 的 {user_request.days} 日游生成完整的避坑指南、物品清单、应急预案和拍照攻略。"

        response = self._call_llm(user_msg, context)

        try:
            json_str = _extract_json(response)
            data = json.loads(json_str)

            pitfalls = PitfallTips(**data.get("pitfalls", {}))
            packing = PackingList(**data.get("packing", {}))
            emergency = EmergencyPlan(**data.get("emergency", {}))
            photo_guide = PhotoGuide(**data.get("photo_guide", {}))

            return {
                "pitfalls": pitfalls,
                "packing_list": packing,
                "emergency_plan": emergency,
                "photo_guide": photo_guide,
                "messages": [
                    f"✅ 攻略生成完成: "
                    f"避坑指南 {len(pitfalls.common_scams) + len(pitfalls.tourist_traps)} 条, "
                    f"拍照机位 {len(photo_guide.best_spots)} 个"
                ],
                "current_stage": "tips_done",
            }
        except (json.JSONDecodeError, TypeError) as e:
            return {
                "errors": [f"攻略解析失败: {str(e)}"],
                "messages": ["⚠️ 攻略生成解析异常"],
                "pitfalls": PitfallTips(),
                "packing_list": PackingList(),
                "emergency_plan": EmergencyPlan(),
                "photo_guide": PhotoGuide(),
                "current_stage": "tips_done",
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

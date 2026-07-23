"""
文案 & 总结 Agent — 生成行程总览、每日亮点摘要、社交分享文案

负责将前面所有 Agent 的产出做最后的整合和润色
"""

from __future__ import annotations

from agents.base import BaseAgent


COPYWRITING_SYSTEM_PROMPT = """你是一位旅行内容主编，擅长把旅行方案包装成让人眼前一亮的文案。

## 你的职责
1. 撰写一段 200 字以内的「行程总览」摘要，让读者 3 秒 get 这趟旅行的亮点
2. 为每天行程写一句「当日金句」(highlights)，像旅行博主那样有感染力
3. 生成 3 条适合发朋友圈/小红书的分享文案（不同风格: 文艺/幽默/ins风）

## 输出格式
```json
{
  "overview": "这是一场穿越杭州山水与人文的 3 天轻奢之旅。从西湖晨雾到龙井茶园，从南宋御街的烟火气到钱塘江畔的落日..." ,
  "daily_highlights": [
    "Day 1 | 初识西湖: 断桥的晨光会是你此行第一个心动瞬间",
    "Day 2 | 茶香满径: 龙井村的炒茶声里，藏着杭州最地道的味道"
  ],
  "social_captions": [
    "🍃 在杭州做了3天闲人 | 西湖的风，龙井的茶，和我爱的你 #杭州旅行 #治愈系出行",
    "家人们谁懂啊！杭州也太好拍了吧！3天2夜保姆级攻略已出 👉",
    "somewhere between the tea fields and the sunset, I found my peace 🌿✨ #hangzhou #traveldiaries"
  ]
}
```
"""


class CopywritingAgent(BaseAgent):
    """旅行内容主编"""

    name = "copywriting"
    role = "旅行内容主编"
    system_prompt = COPYWRITING_SYSTEM_PROMPT
    temperature = 0.9  # 文案需要高创意

    def invoke(self, state: dict) -> dict:
        """汇总所有产出，生成总结文案"""
        import json

        user_request = state.get("user_request")
        daily_plans = state.get("daily_plans", [])

        if not user_request or not daily_plans:
            return {
                "messages": ["📝 文案生成跳过: 缺少行程数据"],
                "overview": f"{user_request.destination} {user_request.days} 日游" if user_request else "",
            }

        # 构建简洁的行程摘要给 LLM
        plan_summary = f"目的地: {user_request.destination}\n天数: {user_request.days}\n风格: {user_request.style.value}\n\n"

        for day in daily_plans:
            spots = []
            for period in ["morning", "afternoon", "evening"]:
                for act in getattr(day, period, []):
                    spots.append(act.name)
            plan_summary += f"Day {day.day} ({day.theme or ''}): {' → '.join(spots[:5])}\n"

        user_msg = f"""
请为以下旅行方案撰写总览摘要、每日金句和社交分享文案:

{plan_summary}
"""

        response = self._call_llm(user_msg)

        try:
            json_str = _extract_json(response)
            data = json.loads(json_str)

            # 把 daily_highlights 注入到对应的 DayPlan 中
            highlights_map = {}
            for dh in data.get("daily_highlights", []):
                for i, day in enumerate(daily_plans):
                    if f"Day {day.day}" in dh:
                        day.highlights = dh.split("|", 1)[-1].strip() if "|" in dh else dh
                        break

            return {
                "overview": data.get("overview", ""),
                "daily_plans": daily_plans,  # 更新后的
                "messages": [
                    f"✅ 文案生成完成: 行程总览已生成, {len(data.get('social_captions', []))} 条社交文案"
                ],
                "current_stage": "copywriting_done",
            }
        except Exception:
            return {
                "overview": f"「{user_request.destination}{user_request.days}日{user_request.style.value}之旅」—— 一场精心策划的旅行，期待你的探索！",
                "messages": ["📝 文案已生成(默认)"],
                "current_stage": "copywriting_done",
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

"""
导出工具 — 将旅行全案导出为 Markdown / PDF / Excel 表格
"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

from langchain.tools import tool
from config.settings import get_settings

settings = get_settings()


@tool
def export_to_markdown(plan_json: str, output_dir: str = "") -> str:
    """
    将旅行全案导出为 Markdown 文件。

    Args:
        plan_json: JSON 格式的完整旅行方案序列化字符串
        output_dir: 输出目录，默认使用配置中的 output_dir

    Returns:
        导出文件路径
    """
    import json
    from models.schemas import TravelPlan

    plan = TravelPlan.model_validate_json(plan_json)
    output = output_dir or settings.output_dir
    Path(output).mkdir(parents=True, exist_ok=True)

    md = _build_markdown(plan)

    filename = f"旅行攻略_{plan.request.destination}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join(output, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    return filepath


def _build_markdown(plan) -> str:
    """构建完整的 Markdown 文档"""
    req = plan.request
    lines = []

    # 标题
    lines.append(f"# 🗺️ {req.destination} 旅行全案攻略")
    lines.append(f"\n> 📅 {req.days}天 | 👥 {req.travelers}人 | 💰 预算 {req.budget_total}元 | 🎯 {req.style.value}")
    lines.append(f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("\n---")

    # 行程总览
    if plan.overview:
        lines.append(f"\n## 📋 行程总览\n\n{plan.overview}")

    # 每日行程
    if plan.daily_plans:
        lines.append("\n---\n\n## 📅 每日详细行程")
        for day in plan.daily_plans:
            lines.append(f"\n### Day {day.day} — {day.theme or '探索日'}")
            if day.date:
                lines.append(f"*{day.date}*")

            if day.morning:
                lines.append("\n**☀️ 上午**")
                for a in day.morning:
                    lines.append(f"- 🏛️ **{a.name}** ({a.duration_minutes}分钟)")
                    if a.description:
                        lines.append(f"  {a.description}")
                    if a.tips:
                        lines.append(f"  💡 {' | '.join(a.tips)}")

            if day.afternoon:
                lines.append("\n**🌤️ 下午**")
                for a in day.afternoon:
                    lines.append(f"- 🏛️ **{a.name}** ({a.duration_minutes}分钟)")
                    if a.description:
                        lines.append(f"  {a.description}")

            if day.evening:
                lines.append("\n**🌙 晚上**")
                for a in day.evening:
                    lines.append(f"- 🍽️ **{a.name}** ({a.duration_minutes}分钟)")
                    if a.description:
                        lines.append(f"  {a.description}")

            if day.meals:
                lines.append("\n**🍴 推荐餐厅**")
                for m in day.meals:
                    lines.append(f"- {m.get('meal_type', '餐饮')}: {m.get('name', '')} (人均 ¥{m.get('avg_cost', 0)})")

            if day.transport_notes:
                lines.append(f"\n**🚗 交通**: {day.transport_notes}")
            lines.append("")

    # 预算表
    if plan.budget and plan.budget.items:
        lines.append("\n---\n\n## 💰 预算明细")
        lines.append("\n| 类别 | 项目 | 金额(元) | 备注 |")
        lines.append("|------|------|----------|------|")
        for item in plan.budget.items:
            per = " (人均)" if item.per_person else ""
            lines.append(f"| {item.category} | {item.item} | ¥{item.amount}{per} | {item.notes} |")
        lines.append(f"| **合计** | | **¥{plan.budget.total}** | |")
        lines.append(f"\n人均: ¥{plan.budget.per_person} | 应急备用: ¥{plan.budget.contingency}")

        if plan.budget.savings_tips:
            lines.append("\n**💡 省钱建议**")
            for tip in plan.budget.savings_tips:
                lines.append(f"- {tip}")

    # 避坑指南
    if plan.pitfalls:
        lines.append("\n---\n\n## ⚠️ 避坑指南")
        sections = [
            ("🚫 常见骗局", plan.pitfalls.common_scams),
            ("🎯 游客陷阱", plan.pitfalls.tourist_traps),
            ("🚗 交通避坑", plan.pitfalls.transport_pitfalls),
            ("🍔 饮食安全", plan.pitfalls.food_safety),
            ("🙏 文化禁忌", plan.pitfalls.cultural_taboos),
        ]
        for title, items in sections:
            if items:
                lines.append(f"\n### {title}")
                for item in items:
                    lines.append(f"- {item}")

    # 物品清单
    if plan.packing:
        lines.append("\n---\n\n## 🎒 必备物品清单")
        cats = [
            ("📋 证件资金", plan.packing.essentials),
            ("👔 衣物", plan.packing.clothing),
            ("🧴 洗漱用品", plan.packing.toiletries),
            ("📱 电子设备", plan.packing.electronics),
            ("💊 药品", plan.packing.medicine),
            ("🎯 专属物品", plan.packing.travel_specific),
        ]
        for title, items in cats:
            if items:
                lines.append(f"\n### {title}")
                for item in items:
                    lines.append(f"- [ ] {item}")

    # 拍照指南
    if plan.photo_guide:
        lines.append("\n---\n\n## 📸 拍照打卡指南")
        if plan.photo_guide.best_spots:
            lines.append("\n| 地点 | 最佳时间 | 拍照技巧 |")
            lines.append("|------|----------|----------|")
            for spot in plan.photo_guide.best_spots:
                lines.append(f"| {spot.get('name', '')} | {spot.get('best_time', '')} | {spot.get('pose_tips', '')} |")
        if plan.photo_guide.outfit_suggestions:
            lines.append("\n**👗 穿搭建议**")
            for s in plan.photo_guide.outfit_suggestions:
                lines.append(f"- {s}")

    # 应急预案
    if plan.emergency:
        lines.append("\n---\n\n## 🆘 应急预案")
        if plan.emergency.emergency_contacts:
            lines.append("\n**📞 紧急联系**")
            for k, v in plan.emergency.emergency_contacts.items():
                lines.append(f"- {k}: {v}")
        if plan.emergency.nearest_hospital:
            lines.append(f"\n**🏥 最近医院**: {plan.emergency.nearest_hospital}")
        if plan.emergency.rainy_day_plan:
            lines.append(f"\n**🌧️ 雨天备选**: {plan.emergency.rainy_day_plan}")
        if plan.emergency.backup_routes:
            lines.append("\n**🔄 备用路线**")
            for r in plan.emergency.backup_routes:
                lines.append(f"- {r}")

    lines.append(f"\n\n---\n\n*🤖 本方案由「智行规划师」AI 多智能体系统生成 | {datetime.now().year}*")
    return "\n".join(lines)


ExportTool = export_to_markdown

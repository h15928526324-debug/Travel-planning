"""
搜索 & 数据聚合工具

提供景点评分、美食推荐、酒店比价等搜索能力。
MVP 阶段使用 LLM 内建知识 + 模拟数据，后续可接入真实搜索 API。
"""

from __future__ import annotations

from langchain.tools import tool


@tool
def search_attractions(city: str, style: str = "综合", count: int = 10) -> list[dict]:
    """
    搜索目的地热门景点。

    Args:
        city: 城市名称
        style: 出行风格 (穷游/轻奢/亲子/美食/拍照打卡/人文历史)
        count: 返回数量

    Returns:
        [{name, category, rating, ticket_price, duration_minutes, description, tips, photo_spots}]
    """
    # MVP: 返回空列表，由 LLM Agent 根据训练数据生成
    # 后续可接入 马蜂窝/携程 API、Google Places API、小红书爬虫
    return []


@tool
def search_foods(city: str, style: str = "综合", count: int = 10) -> list[dict]:
    """
    搜索目的地特色美食和餐厅。

    Args:
        city: 城市名称
        style: 出行风格
        count: 返回数量

    Returns:
        [{name, category, avg_cost, recommended_dishes, address, tips}]
    """
    return []


@tool
def search_hotels(city: str, area: str = "", budget_per_night: float = 500, count: int = 5) -> list[dict]:
    """
    搜索酒店/民宿。

    Args:
        city: 城市名称
        area: 希望入住区域
        budget_per_night: 每晚预算
        count: 返回数量

    Returns:
        [{name, area, price_range, rating, pros, cons, distance_to_center}]
    """
    return []


@tool
def search_transport(from_city: str, to_city: str) -> list[dict]:
    """
    搜索城际交通方案。

    Args:
        from_city: 出发城市
        to_city: 目的城市

    Returns:
        [{mode, duration_minutes, cost, description}]
    """
    return []


SearchTool = search_attractions

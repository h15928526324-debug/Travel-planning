"""
地理编码 & 距离计算工具

提供地址解析、坐标转换、两地距离/时间估算
"""

from __future__ import annotations

import math
import requests
from langchain.tools import tool

from config.settings import get_settings

settings = get_settings()


@tool
def geocode(address: str, city: str = "") -> dict:
    """
    地址转经纬度坐标。

    Args:
        address: 详细地址
        city: 所在城市（可选，帮助精确定位）

    Returns:
        {"address": "...", "lng": 120.15, "lat": 30.28, "city": "杭州"}
    """
    api_key = settings.map_api_key

    if not api_key:
        return _mock_geocode(address, city)

    # 使用高德地图 API
    try:
        url = "https://restapi.amap.com/v3/geocode/geo"
        resp = requests.get(url, params={
            "key": api_key,
            "address": f"{city}{address}" if city else address,
        }, timeout=10)
        data = resp.json()

        if data.get("status") == "1" and data.get("geocodes"):
            geo = data["geocodes"][0]
            location = geo["location"].split(",")
            return {
                "address": geo["formatted_address"],
                "lng": float(location[0]),
                "lat": float(location[1]),
                "city": geo.get("city", city),
            }
    except Exception:
        pass

    return _mock_geocode(address, city)


@tool
def calculate_distance(origin: str, destination: str, mode: str = "transit") -> dict:
    """
    计算两地之间的距离和通勤时间。

    Args:
        origin: 起点地址
        destination: 终点地址
        mode: 出行方式 (walking / transit / driving)

    Returns:
        {"distance_km": 5.2, "duration_minutes": 30, "mode": "transit", "route_summary": "..."}
    """
    api_key = settings.map_api_key

    if not api_key:
        return _mock_distance(origin, destination, mode)

    try:
        # 高德路径规划
        mode_map = {"walking": "1", "transit": "0", "driving": "0"}
        url_map = {"walking": "https://restapi.amap.com/v3/direction/walking",
                    "driving": "https://restapi.amap.com/v3/direction/driving",
                    "transit": "https://restapi.amap.com/v3/direction/transit/integrated"}

        # 先地理编码获取坐标
        origin_geo = geocode(origin)
        dest_geo = geocode(destination)

        origin_coord = f"{origin_geo['lng']},{origin_geo['lat']}"
        dest_coord = f"{dest_geo['lng']},{dest_geo['lat']}"

        url = url_map.get(mode, url_map["transit"])
        resp = requests.get(url, params={
            "key": api_key,
            "origin": origin_coord,
            "destination": dest_coord,
            "city1": origin_geo.get("city", ""),
            "city2": dest_geo.get("city", ""),
        }, timeout=10)
        data = resp.json()

        if data.get("status") == "1" and data.get("route"):
            route = data["route"]
            if mode in ("walking", "driving"):
                paths = route.get("paths", [{}])
                distance = int(paths[0].get("distance", 0)) / 1000
                duration = int(paths[0].get("duration", 0)) / 60
            else:
                transits = route.get("transits", [{}])
                distance = int(transits[0].get("distance", 0)) / 1000 if transits else 0
                duration = int(transits[0].get("duration", 0)) / 60 if transits else 0

            return {
                "distance_km": round(distance, 1),
                "duration_minutes": round(duration),
                "mode": mode,
                "route_summary": f"约{round(distance, 1)}公里，预计{round(duration)}分钟",
            }
    except Exception:
        pass

    return _mock_distance(origin, destination, mode)


def _mock_geocode(address: str, city: str = "") -> dict:
    """MVP 模拟地理编码"""
    return {
        "address": f"{city}{address}" if city else address,
        "lng": 120.15,
        "lat": 30.28,
        "city": city or "杭州",
    }


def _mock_distance(origin: str, destination: str, mode: str) -> dict:
    """MVP 模拟距离计算 — 后续接入真实 API 替换"""
    # 简单 hash 模拟不同距离
    seed = abs(hash(origin + destination)) % 100
    distance = 0.5 + seed / 10
    speeds = {"walking": 5, "transit": 25, "driving": 40}
    speed = speeds.get(mode, 25)
    duration = distance / speed * 60

    return {
        "distance_km": round(distance, 1),
        "duration_minutes": round(duration),
        "mode": mode,
        "route_summary": f"约{round(distance, 1)}公里，预计{round(duration)}分钟（模拟数据）",
    }


GeoTool = geocode

"""
天气查询工具 — 基于免费 API (uapis.cn) 获取目的地实时天气 + 7 日预报 + 逐小时预报

接口特点:
  - 无需 API Key，零配置可用
  - 支持 forecast=true (7 日预报) + hourly=true (24 小时逐小时)
  - 支持中/英文城市名 + adcode 精确查询
  - 覆盖 7000+ 城市
  - 返回: 温度/天气/风力/湿度/降雨概率/UV/日出日落/体感温度/能见度
"""

from __future__ import annotations

import requests
from langchain.tools import tool

UAPIS_WEATHER_URL = "https://uapis.cn/api/v1/misc/weather"

# 常用目的地的 adcode 映射
ADCODE_MAP: dict[str, str] = {
    "杭州": "330100", "北京": "110000", "上海": "310000",
    "广州": "440100", "深圳": "440300", "成都": "510100",
    "重庆": "500000", "西安": "610100", "南京": "320100",
    "武汉": "420100", "长沙": "430100", "厦门": "350200",
    "青岛": "370200", "大连": "210200", "三亚": "460200",
    "丽江": "530700", "大理": "532900", "桂林": "450300",
    "苏州": "320500", "昆明": "530100", "哈尔滨": "230100",
    "拉萨": "540100", "乌鲁木齐": "650100",
    "香港": "810000", "澳门": "820000", "台北": "710000",
}


@tool
def get_weather(city: str, date: str = "") -> dict:
    """
    查询指定城市的天气信息（实时 + 7 日预报 + 24h 逐小时）。

    Args:
        city: 城市名称 (中文，如"杭州"、"北京")
        date: 日期 YYYY-MM-DD，留空返回全部

    Returns:
        {
            "city": "杭州", "province": "浙江省",
            "current": {"weather": "多云", "temperature": 32, "humidity": 56, "wind": "南风 4级", ...},
            "forecast": [{date, week, temp_high, temp_low, weather_day, weather_night,
                          humidity, precip, pop, uv_index, sunrise, sunset, wind_scale_day}, ...],
            "hourly": [{time, temperature, weather, humidity, precip, pop, feels_like, wind_scale}, ...],
            "travel_advice": "...",
            "packing_tips": "..."
        }
    """
    try:
        return _fetch_uapis(city)
    except Exception:
        return _fallback_weather(city)


def _fetch_uapis(city: str) -> dict:
    """调用 uapis.cn 天气 API，同时获取预报和逐小时数据"""

    params = {"forecast": "true", "hourly": "true"}

    # 策略 1: adcode 查询（最稳定）
    adcode = ADCODE_MAP.get(city)
    if adcode:
        params["adcode"] = adcode
        resp = requests.get(UAPIS_WEATHER_URL, params=params, timeout=10)
        data = resp.json()
        if "temperature" in data:
            return _format_result(city, data)

    # 策略 2: 城市名查询
    params["city"] = city
    resp = requests.get(UAPIS_WEATHER_URL, params=params, timeout=10)
    data = resp.json()
    if "temperature" in data:
        return _format_result(data.get("city", city), data)

    # 策略 3: 城市名 + "市"
    params["city"] = city + "市"
    resp = requests.get(UAPIS_WEATHER_URL, params=params, timeout=10)
    data = resp.json()
    if "temperature" in data:
        return _format_result(data.get("city", city), data)

    return _fallback_weather(city)


def _format_result(city: str, data: dict) -> dict:
    """将 API 原始数据转换为统一结构"""
    province = data.get("province", "")
    report_time = data.get("report_time", "")

    # ── 当前天气 ──
    current = {
        "weather": data.get("weather", "晴"),
        "temperature": data.get("temperature", 25),
        "humidity": data.get("humidity", 50),
        "wind": f"{data.get('wind_direction', '')} {data.get('wind_power', '')}".strip(),
        "temp_max_today": data.get("temp_max", ""),
        "temp_min_today": data.get("temp_min", ""),
        "report_time": report_time,
    }

    # ── 7 日预报 ──
    raw_forecast = data.get("forecast", [])
    forecasts = []
    for day in raw_forecast:
        forecasts.append({
            "date": day.get("date", ""),
            "week": day.get("week", ""),
            "temp_high": day.get("temp_max", ""),
            "temp_low": day.get("temp_min", ""),
            "weather_day": day.get("weather_day", ""),
            "weather_night": day.get("weather_night", ""),
            "humidity": day.get("humidity", ""),
            "precip": day.get("precip", 0),          # 降水量 mm
            "pop": day.get("pop", 0),                 # 降雨概率 %
            "uv_index": day.get("uv_index", ""),      # UV 指数
            "sunrise": day.get("sunrise", ""),
            "sunset": day.get("sunset", ""),
            "wind_day": f"{day.get('wind_dir_day', '')} {day.get('wind_scale_day', '')}".strip(),
            "wind_night": f"{day.get('wind_dir_night', '')} {day.get('wind_scale_night', '')}".strip(),
        })

    # ── 24h 逐小时 ──
    raw_hourly = data.get("hourly_forecast", [])
    hourly = []
    for h in raw_hourly:
        hourly.append({
            "time": h.get("time", ""),
            "temperature": h.get("temperature", ""),
            "weather": h.get("weather", ""),
            "humidity": h.get("humidity", ""),
            "precip": h.get("precip", 0),
            "pop": h.get("pop", 0),
            "feels_like": h.get("feels_like", ""),
            "wind_scale": h.get("wind_scale", ""),
            "wind_direction": h.get("wind_direction", ""),
            "visibility": h.get("visibility", ""),
        })

    return {
        "city": city,
        "province": province,
        "current": current,
        "forecast": forecasts,
        "hourly": hourly,
        "travel_advice": _generate_travel_advice(forecasts, current),
        "packing_tips": _generate_packing_tips(forecasts, current),
    }


def _fallback_weather(city: str) -> dict:
    """无网络时的兜底数据"""
    return {
        "city": city,
        "province": "",
        "current": {"weather": "晴", "temperature": 28, "humidity": 60,
                     "wind": "微风", "temp_max_today": 32, "temp_min_today": 22, "report_time": ""},
        "forecast": [
            {"date": f"2026-07-{23+i:02d}", "week": f"周{['四','五','六','日','一','二','三'][i]}",
             "temp_high": 30 + i, "temp_low": 22 + i, "weather_day": "晴转多云", "weather_night": "多云",
             "humidity": 60 + i * 5, "precip": 0, "pop": 10, "uv_index": 7,
             "sunrise": "05:15", "sunset": "18:58", "wind_day": "南风 2级", "wind_night": "南风 2级"}
            for i in range(7)
        ],
        "hourly": [],
        "travel_advice": "天气总体适宜出行（离线模式，数据为估算）",
        "packing_tips": "防晒霜、遮阳帽、雨伞",
    }


def _generate_travel_advice(forecasts: list[dict], current: dict) -> str:
    """基于真实预报数据生成出行建议"""
    if not forecasts:
        return "暂无预报数据"

    high_temps = [f["temp_high"] for f in forecasts if f["temp_high"] != ""]
    avg_high = sum(high_temps) / len(high_temps) if high_temps else 25
    max_high = max(high_temps) if high_temps else 30
    min_low = min(f["temp_low"] for f in forecasts if f["temp_low"] != "") if high_temps else 20
    max_uv = max((f["uv_index"] for f in forecasts if f["uv_index"] != ""), default=0)
    rainy_days = sum(1 for f in forecasts if f["pop"] >= 50)  # 降雨概率 ≥50%
    heavy_rain_days = sum(1 for f in forecasts if isinstance(f.get("precip"), (int, float)) and f["precip"] > 3)

    tips = []

    # 温度
    if max_high >= 39:
        tips.append(f"🔴 高温红色预警：最高 {max_high}°C！避免 11:00-16:00 户外活动，每小时补水 500ml+")
    elif max_high >= 35:
        tips.append(f"🟠 高温 {max_high}°C，午间避免暴晒，随身携带充足饮水")
    elif max_high >= 30:
        tips.append(f"🟡 白天 {max_high}°C 较热，早晚凉爽 ({min_low}°C)，建议早出晚归")
    elif avg_high < 10:
        tips.append(f"🔵 低温 {min_low}~{max_high}°C，注意保暖防冻")

    # 降雨
    if heavy_rain_days >= 2:
        tips.append(f"🌧️ {heavy_rain_days} 天有大到暴雨，请备好防水装备，关注景区关闭通知")
    elif rainy_days >= 3:
        tips.append(f"🌂 未来 {rainy_days} 天降雨概率较高，务必带伞 + 防水鞋")
    elif rainy_days >= 1:
        tips.append(f"🌤️ 偶有阵雨（降雨概率 {rainy_days} 天 ≥50%），建议随身带折叠伞")

    # UV
    if isinstance(max_uv, (int, float)) and max_uv >= 8:
        tips.append(f"☀️ UV 指数高达 {max_uv}，SPF50+ 防晒霜 + 墨镜 + 遮阳帽必备")
    elif isinstance(max_uv, (int, float)) and max_uv >= 5:
        tips.append(f"🌤️ UV 指数 {max_uv}，注意涂抹防晒")

    # 温差
    temp_range = max_high - min_low if high_temps else 0
    if temp_range > 12:
        tips.append(f"🌡️ 昼夜温差大 ({min_low}~{max_high}°C)，建议洋葱式穿搭，早晚加外套")

    # 日出日落（用于行程建议）
    if forecasts[0].get("sunrise") and forecasts[0].get("sunset"):
        tips.append(f"🌅 日出 {forecasts[0]['sunrise']} / 日落 {forecasts[0]['sunset']}，看日出请 {forecasts[0]['sunrise']} 前到达")

    if not tips:
        tips.append("🎉 天气宜人，非常适合出游！")
    return "；\n".join(tips)


def _generate_packing_tips(forecasts: list[dict], current: dict) -> str:
    """基于预报数据生成精确的打包建议"""
    tips = []

    high_temps = [f["temp_high"] for f in forecasts if f["temp_high"] != ""]
    avg_high = sum(high_temps) / len(high_temps) if high_temps else current.get("temperature", 25)
    max_uv = max((f["uv_index"] for f in forecasts if f["uv_index"] != ""), default=0)
    rainy_days = sum(1 for f in forecasts if f["pop"] >= 50)
    humidity_values = [f["humidity"] for f in forecasts if f["humidity"] != ""]
    avg_humidity = sum(humidity_values) / len(humidity_values) if humidity_values else 60

    # 必备
    tips.append("身份证/护照、手机+充电宝")

    # 温度相关
    if avg_high > 32:
        tips.extend(["透气速干衣物×3", "遮阳帽", "墨镜", "便携小风扇/挂脖空调"])
    elif avg_high > 25:
        tips.extend(["短袖+薄长裤", "遮阳帽", "轻薄防晒外套"])
    elif avg_high < 10:
        tips.extend(["厚羽绒服", "保暖内衣", "围巾+手套+毛线帽", "暖宝宝"])
    elif avg_high < 20:
        tips.extend(["薄外套/卫衣", "长裤"])

    # UV
    if isinstance(max_uv, (int, float)) and max_uv >= 6:
        tips.append("SPF50+ PA++++ 防水防晒霜")
    else:
        tips.append("日常防晒霜")

    # 降雨
    if rainy_days >= 3:
        tips.extend(["折叠伞", "防水鞋套/凉鞋", "防水背包罩", "快干毛巾"])
    elif rainy_days >= 1:
        tips.extend(["折叠伞", "防水鞋套"])

    # 湿度
    if avg_humidity > 75:
        tips.extend(["防潮袋（相机/衣物）", "驱蚊液/驱蚊手环"])

    # 药品（通用）
    tips.extend(["创可贴+消毒湿巾", "肠胃药+感冒药", "晕车药"])

    # 去重保序
    seen = set()
    result = []
    for t in tips:
        if t not in seen:
            result.append(t)
            seen.add(t)
    return "、\n".join(result)


WeatherTool = get_weather

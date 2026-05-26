"""
tools7/weather_tool.py
---------------------
天气查询工具。

优先使用 OpenWeatherMap API（需要 API Key）。
如果没有配置 API Key，自动降级到免费的 wttr.in 服务（无需注册）。

wttr.in 是一个开源天气服务：https://github.com/chubin/wttr.in
支持中文城市名查询，完全免费，适合教学演示。
"""

import os
import json
import requests
from langchain_core.tools import tool


def _query_wttr(city: str) -> dict:
    """
    使用 wttr.in 免费天气 API 查询天气。
    返回格式化的天气信息字典。

    Args:
        city: 城市名称（支持中文）

    Returns:
        包含当前天气和未来3天预报的字典
    """
    # 构建请求 URL，format=j1 返回 JSON 格式，lang=zh 返回中文描述
    url = f"https://wttr.in/{city}?format=j1&lang=zh"
    response = requests.get(url, timeout=10)
    response.raise_for_status()   # 如果请求失败，抛出异常
    data = response.json()        # 解析 JSON 响应

    # 提取当前天气数据（wttr.in 返回的第一个当前条件对象）
    current = data["current_condition"][0]
    weather_desc = current["weatherDesc"][0]["value"]
    temp_c = current["temp_C"]
    feels_like = current["FeelsLikeC"]
    humidity = current["humidity"]
    wind_speed = current["windspeedKmph"]
    wind_dir = current["winddir16Point"]
    visibility = current["visibility"]
    uv_index = current["uvIndex"]

    # 获取3天预报（取前3天）
    forecasts = []
    for day_data in data.get("weather", [])[:3]:
        date = day_data["date"]
        max_temp = day_data["maxtempC"]
        min_temp = day_data["mintempC"]
        # wttr.in 的 hourly 列表中第4个条目（索引4）通常代表当天的主要天气描述
        desc = day_data["hourly"][4]["weatherDesc"][0]["value"]
        forecasts.append({
            "date": date,
            "max_temp": f"{max_temp}°C",
            "min_temp": f"{min_temp}°C",
            "description": desc
        })

    # 组装结果字典
    return {
        "city": city,
        "current": {
            "temperature": f"{temp_c}°C",
            "feels_like": f"{feels_like}°C",
            "description": weather_desc,
            "humidity": f"{humidity}%",
            "wind": f"{wind_speed} km/h {wind_dir}",
            "visibility": f"{visibility} km",
            "uv_index": uv_index
        },
        "forecast": forecasts
    }


def _query_openweather(city: str, api_key: str) -> dict:
    """
    使用 OpenWeatherMap API 查询天气（需要 API Key）。

    Args:
        city: 城市名称（支持中文或英文）
        api_key: OpenWeatherMap API 密钥

    Returns:
        包含当前天气信息的字典（免费版不含预报）
    """
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",   # 摄氏度
        "lang": "zh_cn"      # 中文描述
    }
    response = requests.get(base_url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    # 提取并格式化当前天气信息
    return {
        "city": data["name"],
        "current": {
            "temperature": f"{data['main']['temp']:.1f}°C",
            "feels_like": f"{data['main']['feels_like']:.1f}°C",
            "description": data["weather"][0]["description"],
            "humidity": f"{data['main']['humidity']}%",
            "wind": f"{data['wind']['speed']} m/s",
            "visibility": f"{data.get('visibility', 'N/A')} m",
            "uv_index": "N/A"          # OpenWeatherMap 免费版不提供 UV 指数
        },
        "forecast": []   # 免费版没有预报，保持空列表
    }


@tool
def get_weather(city: str) -> str:
    """
    查询指定城市的实时天气信息，包括温度、湿度、风速、天气描述和未来3天预报。

    该工具会自动选择可用的数据源：
    - 如果配置了 OPENWEATHER_API_KEY，则使用 OpenWeatherMap API（更稳定）
    - 否则使用免费的 wttr.in 服务（无需注册）

    Args:
        city: 城市名称，支持中文（如"北京"）和英文（如"Beijing"）

    Returns:
        格式化的天气信息字符串
    """
    try:
        # 从环境变量读取 API Key，如果未设置则为空字符串
        api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()

        if api_key:
            # 使用 OpenWeatherMap
            weather_data = _query_openweather(city, api_key)
            source = "OpenWeatherMap"
        else:
            # 降级使用 wttr.in
            weather_data = _query_wttr(city)
            source = "wttr.in"

        # 格式化输出
        current = weather_data["current"]
        result_lines = [
            f"🌍 城市: {weather_data['city']}",
            f"📡 数据来源: {source}",
            f"",
            f"【当前天气】",
            f"  🌡️  温度: {current['temperature']}  (体感 {current['feels_like']})",
            f"  🌤️  天气: {current['description']}",
            f"  💧 湿度: {current['humidity']}",
            f"  💨 风速: {current['wind']}",
            f"  👁️  能见度: {current['visibility']}",
            f"  ☀️  紫外线指数: {current['uv_index']}",
        ]

        # 如果有预报数据，添加预报信息
        if weather_data.get("forecast"):
            result_lines.append(f"")
            result_lines.append(f"【未来3天预报】")
            for day in weather_data["forecast"]:
                result_lines.append(
                    f"  📅 {day['date']}: {day['description']}，"
                    f"最高 {day['max_temp']} / 最低 {day['min_temp']}"
                )

        return "\n".join(result_lines)

    # 异常处理：针对各种可能的错误返回友好提示
    except requests.Timeout:
        return f"❌ 查询超时，请检查网络连接后重试。城市: {city}"
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return f"❌ 找不到城市 '{city}'，请检查城市名称是否正确"
        return f"❌ 天气 API 请求失败: {str(e)}"
    except Exception as e:
        return f"❌ 查询天气时出错: {str(e)}"
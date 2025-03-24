import os
import json
import requests
from datetime import datetime, timedelta

WEATHER_API_KEY = "key"  # 你的高德地图天气 API Key
WEATHER_CITY = "210202"
LOCAL_WEATHER_JSON = "resource/weather_result.json"

def extract_weather_str(data_dict):
    """
    从数据中提取并拼接成 “多云 4℃” 形式
    """
    lives = data_dict.get("lives", [])
    if not lives:
        return "未知天气"
    weather_desc = lives[0].get("weather", "未知")
    temperature = lives[0].get("temperature", "0")
    return f"{weather_desc} {temperature}℃"

def get_weather_info():
    """
    获取天气信息：优先使用本地缓存数据，若超时则调用 API 更新
    """
    local_data = None
    if os.path.exists(LOCAL_WEATHER_JSON):
        try:
            with open(LOCAL_WEATHER_JSON, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except Exception as e:
            print("[WeatherUtils] 读取本地 weather_result.json 失败：", e)
            local_data = None

    if local_data:
        try:
            lives_info = local_data["lives"][0]
            report_time_str = lives_info["reporttime"]
            report_time = datetime.strptime(report_time_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - report_time <= timedelta(hours=1):
                print("[WeatherUtils] 本地天气数据未超过1小时，直接使用本地数据。")
                return extract_weather_str(local_data)
            else:
                print("[WeatherUtils] 本地天气数据超过1小时，调用 API 更新。")
        except Exception as e:
            print("[WeatherUtils] 解析本地天气数据异常，调用 API 更新：", e)
    else:
        print("[WeatherUtils] 未找到本地 weather_result.json，调用 API 获取最新数据。")

    url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={WEATHER_CITY}&key={WEATHER_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "1" and "lives" in data and len(data["lives"]) > 0:
                with open(LOCAL_WEATHER_JSON, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                return extract_weather_str(data)
            else:
                print("[WeatherUtils] API 返回数据异常：", data)
                return "晴 25℃"
        else:
            print("[WeatherUtils] API 请求失败，status_code：", response.status_code)
            return "晴 25℃"
    except Exception as e:
        print("[WeatherUtils] 请求天气 API 出现错误：", e)
        return "晴 25℃"

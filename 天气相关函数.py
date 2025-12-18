# 在第三步的代码中，添加以下内容：

# 1. 首先在文件顶部添加必要的导入
import requests
import urllib3
from typing import Optional, Dict, Any
from datetime import datetime

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 2. 你的高德API配置
AMAP_API_KEY = "5d8cea4f9a8dfe9f7c3b4307154eef40"  # 建议使用环境变量更安全
AMAP_WEATHER_API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


# 3. 修改get_weather函数 - 关键修复
def get_weather(city_name: str) -> Optional[Dict[str, Any]]:
    """
    调用高德API获取天气数据

    Args:
        city_name: 城市名称，如"北京"、"上海"等

    Returns:
        dict: 包含天气数据的字典，如果失败返回None
    """
    try:
        params = {
            "city": city_name,
            "key": AMAP_API_KEY,
            "output": "json",
            "extensions": "base"  # 使用base获取实时天气
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }

        print(f"🌤️ 正在查询 {city_name} 的天气...")

        # 关键修复：禁用SSL验证
        response = requests.get(
            url=AMAP_WEATHER_API_URL,
            params=params,
            headers=headers,
            timeout=10,
            verify=False  # ⭐ 添加这一行，禁用SSL验证
        )

        # 检查响应状态
        if response.status_code != 200:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            return None

        data = response.json()

        # 检查API返回的状态
        if data.get("status") == "1" and data.get("lives"):
            print(f"✅ {city_name} 天气数据获取成功")
            return data
        else:
            error_info = data.get("info", "未知错误")
            print(f"❌ 高德API返回错误: {error_info}")
            return None

    except requests.exceptions.Timeout:
        print("⏰ 请求超时，请检查网络连接")
        return None

    except requests.exceptions.ConnectionError:
        print("🔌 网络连接错误，请检查网络")
        return None

    except requests.exceptions.RequestException as e:
        print(f"🌐 网络请求异常: {e}")
        return None

    except Exception as e:
        print(f"❓ 未知错误: {e}")
        return None


# 4. 修改parse_weather_data函数，使其与_format_weather_response兼容
def parse_weather_data(api_data: dict) -> dict:
    """
    解析高德API返回的天气数据，适配_format_weather_response函数
    """
    if not api_data or "lives" not in api_data or not api_data["lives"]:
        return {}

    live_data = api_data["lives"][0]

    # 直接返回原始数据格式，保持与_format_weather_response兼容
    return {
        "weather": live_data.get('weather', '未知'),
        "temperature": live_data.get('temperature', '未知'),
        "winddirection": live_data.get('winddirection', '未知'),
        "windpower": live_data.get('windpower', '未知'),
        "humidity": live_data.get('humidity', '未知'),
        "reporttime": live_data.get('reporttime', '未知'),
        "province": live_data.get('province', ''),
        "city": live_data.get('city', '')
    }
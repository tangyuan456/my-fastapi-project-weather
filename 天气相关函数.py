# 在第三步的代码中，添加以下内容：

# 1. 首先在文件顶部添加必要的导入
import requests
from typing import Optional, Dict, Any
from datetime import datetime

# 2. 你的高德API配置
AMAP_API_KEY = "5d8cea4f9a8dfe9f7c3b4307154eef40"  # 建议使用环境变量更安全
AMAP_WEATHER_API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


# 3. 在第三步的get_weather函数中整合你的代码
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

        # 发送请求
        response = requests.get(
            url=AMAP_WEATHER_API_URL,
            params=params,
            headers=headers,
            timeout=10
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


# 4. 添加一个数据解析函数（可选，根据你的需要调整）
def parse_weather_data(api_data: dict) -> dict:
    """
    解析高德API返回的天气数据

    Args:
        api_data: 高德API返回的原始数据

    Returns:
        dict: 格式化后的天气数据
    """
    if not api_data or "lives" not in api_data or not api_data["lives"]:
        return {}

    live_data = api_data["lives"][0]

    # 解析温度（转换为整数）
    temp_str = live_data.get('temperature', '0')
    try:
        temperature = int(float(temp_str))
    except (ValueError, TypeError):
        temperature = 0

    # 解析湿度（去掉百分号）
    humidity_str = live_data.get('humidity', '0')
    try:
        humidity = int(float(humidity_str.split('%')[0]))
    except (ValueError, TypeError):
        humidity = 0

    # 解析风力等级（提取数字）
    wind_str = live_data.get('windpower', '0')
    try:
        wind = int(''.join(filter(str.isdigit, wind_str)))
    except (ValueError, TypeError):
        wind = 0

    # 解析能见度（转换为km）
    vis_str = live_data.get('visibility', '0')
    try:
        visibility = int(float(vis_str.split('k')[0]))
    except (ValueError, TypeError):
        visibility = 0

    # 解析气压（转换为hPa）
    pressure_str = live_data.get('pressure', '0')
    try:
        pressure = int(float(pressure_str.split('h')[0]))
    except (ValueError, TypeError):
        pressure = 0

    # 返回格式化后的数据
    return {
        "city": live_data.get('city', '未知城市'),
        "temperature": temperature,
        "weather": live_data.get('weather', '未知'),
        "humidity": humidity,
        "wind_power": wind,
        "wind_direction": live_data.get('winddirection', '未知'),
        "visibility": visibility,
        "pressure": pressure,
        "report_time": live_data.get('reporttime', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        "data_source": "高德天气"
    }


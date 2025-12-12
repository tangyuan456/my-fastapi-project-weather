'''from http.client import HTTPException
from typing import Optional

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(
    title="真实版天气查询网站",
    description="一个可以实时查询城市天气的网站",
    version="1.0.0",
)


class User(BaseModel):
    city: str


class WeatherRespond(BaseModel):
    city: str
    temperature: int
    weather: str
    humidity: int
    wind: int
    feels_like: str
    visibility: int
    pressure: int
    update_time: datetime
    data_source: str


class ErrorResponse(BaseModel):
    code: int
    error: bool
    message: str
    suggestion: str


# 高德天气API配置 - 使用你刚才获取的API Key
AMAP_API_KEY = "5d8cea4f9a8dfe9f7c3b4307154eef40"
AMAP_WEATHER_API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


# 发出请求 - 高德天气版本
def get_weather(city: str) -> Optional[dict]:
    try:
        params = {
            "city": city,
            "key": AMAP_API_KEY,
            "output": "json",
            "extensions": "base"  # 获取实时天气
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        print(f"🔍 调试信息 - 请求URL: {AMAP_WEATHER_API_URL}")
        print(f"🔍 调试信息 - 请求参数: {params}")

        response = requests.get(AMAP_WEATHER_API_URL, params=params, headers=headers, timeout=10)
        print(f"🔍 调试信息 - 响应状态码: {response.status_code}")
        print(f"🔍 调试信息 - 响应内容: {response.text}")

        if response.status_code != 200:
            print("response的状态码出错，不是200！")
            return None

        data = response.json()

        # 高德API返回格式判断
        if data.get("status") == "1" and data.get("lives"):
            return data
        else:
            print(f"API返回错误数据: {data}")
            return None

    except requests.exceptions.Timeout:
        print("请求超时")
        return None

    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
        return None

    except Exception as e:
        print(f"API不响应: {e}")
        return None


def parse_weather_data(api_data: dict, city: str) -> WeatherRespond:
    """解析高德天气数据"""
    live_data = api_data["lives"][0]  # 高德返回的是lives数组

    # 处理温度，高德返回的是字符串
    temp_str = live_data.get('temperature', '0')
    try:
        temperature = int(float(temp_str))  # 先转float再转int，处理小数
    except (ValueError, TypeError):
        temperature = 0

    # 处理湿度
    humidity_str = live_data.get('humidity', '0')
    try:
        humidity = int(humidity_str.rstrip('%'))  # 去掉百分号
    except (ValueError, TypeError):
        humidity = 0

    # 处理风速（高德没有直接的风速等级，用windpower）
    wind_power = live_data.get('windpower', '0级')
    try:
        # 尝试提取数字，如"3级" -> 3
        wind = int(''.join(filter(str.isdigit, wind_power)))
    except (ValueError, TypeError):
        wind = 0

    # 处理气压
    pressure_str = live_data.get('pressure', '0')
    try:
        pressure = int(pressure_str)
    except (ValueError, TypeError):
        pressure = 0

    # 处理能见度
    visibility_str = live_data.get('visibility', '0')
    try:
        visibility = int(visibility_str)
    except (ValueError, TypeError):
        visibility = 0

    return WeatherRespond(
        city=live_data.get("city", city),
        temperature=temperature,
        weather=live_data.get("weather", "未知"),
        humidity=humidity,
        wind=wind,
        feels_like=f"{temperature}°C",  # 高德没有体感温度，用实际温度代替
        visibility=visibility,
        pressure=pressure,
        update_time=datetime.now(),
        data_source="高德天气"
    )


@app.get("/")
async def root():
    return {
        "message": "欢迎来到天气查询中心！",
        "description": "一个基于高德天气的可以实时查询天气变化的API服务。",
        "tips": {
            "查看文档": "/docs",
            "具体查询": "/weather",
            "健康检测": "/healthy"
        },
        "version": "1.0.0",
    }


@app.get("/healthy")
async def healthy():
    return {
        "message": "ok",
        "version": "1.0.0",
        "status": "well",
    }


@app.post("/weather",
          response_model=WeatherRespond,
          responses={500: {"model": ErrorResponse}}
          )
async def weather_real(city_search: User):
    city = city_search.city.strip()

    if not city:
        raise HTTPException(
            status_code=400,
            detail="城市输入不可以为空"
        )
    if len(city) > 50:
        raise HTTPException(
            status_code=400,
            detail="城市名字过长了，不可以大于50"
        )

    api_data = get_weather(city)
    if api_data:
        return parse_weather_data(api_data, city)
    else:
        raise HTTPException(
            status_code=404,
            detail="无法获取天气信息，请检查城市名称是否正确"
        )


@app.get("/weather")
async def get_weather_two(city_name: str):
    city_date = User(city=city_name)
    return await weather_real(city_date)


@app.get("/weather/batch")
async def get_weather_batch(city_list: str):
    cities = city_list.split(",")
    city_result = []
    for city in cities:
        city = city.strip()
        if city:
            try:
                city_data = User(city=city)
                city_result.append(await weather_real(city_data))
            except HTTPException:
                # 如果某个城市查询失败，跳过继续查询其他城市
                continue
    return city_result


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8008)
'''
import json
import requests

# 假设你的 api_key 和 url 在另一个文件中定义



class Qwen:
    def __init__(self, Qwen_api_key):
        self.Qwen_api_key = Qwen_api_key
        self.Qwen_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Qwen_api_key}"
        }
        self.history = []

    def chat(self, usr_question):
        # 添加用户消息到历史
        self.history.append({"role": "user", "content": usr_question})

        # 根据通义千问 API 文档调整数据格式
        data = {
            "model": "qwen-turbo",  # 注意：模型名可能是 qwen-turbo 而不是 qwen_turbo
            "input": {
                "messages": self.history  # 注意：这里可能是 "messages" 而不是 "message"
            },
            "parameters": {  # 注意：这里是 "parameters" 不是 "parameter"
                "result_format": "message"
            }
        }

        try:
            response = requests.post(
                self.Qwen_url,  # 使用 self.Qwen_url
                headers=self.headers,
                data=json.dumps(data),
                timeout=30
            )

            # 检查响应状态
            if response.status_code != 200:
                print(f"请求失败，状态码：{response.status_code}")
                print(f"响应内容：{response.text}")
                return f"请求失败：{response.status_code}"

            result_json = response.json()

            # 根据通义千问 API 实际响应结构调整
            # 可能需要查看实际响应结构
            print("API响应:", json.dumps(result_json, indent=2, ensure_ascii=False))

            # 常见的响应结构
            if "output" in result_json and "choices" in result_json["output"]:
                answer = result_json["output"]["choices"][0]["message"]["content"]
            elif "output" in result_json and "text" in result_json["output"]:
                answer = result_json["output"]["text"]
            else:
                # 尝试其他可能的字段
                answer = str(result_json)

            # 添加 AI 回复到历史
            self.history.append({"role": "assistant", "content": answer})
            return answer

        except Exception as e:
            print(f"出错了: {e}")
            return f"请求出错：{str(e)}"


if __name__ == '__main__':
    api_key="sk-346cd33207e54d4298fc8c5e64210eca"

    # 创建实例
    qwen = Qwen(api_key)

    # 测试一个简单请求来验证 API 密钥
    test_response = qwen.chat("你好")
    print(f"测试响应: {test_response}")

    # 开始对话
    while True:
        user_question = input("你：")
        if user_question.lower() in ["退出", "exit", "quit"]:
            print("对话结束")
            break
        else:
            answer = qwen.chat(user_question)  # 正确调用实例方法
            print(f"AI: {answer}")
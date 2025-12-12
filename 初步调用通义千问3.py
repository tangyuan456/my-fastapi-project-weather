from typing import Optional

import requests
from openai import OpenAI
from datetime import datetime
import json
import os
import random




# 初始化客户端
client = OpenAI(
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    api_key="sk-346cd33207e54d4298fc8c5e64210eca",
    # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
# 模拟用户问题
USER_QUESTION = "北京天气咋样"
# 定义工具列表
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "当你想查询指定城市的天气时非常有用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市或县区，比如北京市、杭州市、余杭区等。",
                    }
                },
                "required": ["location"],
            },
        },
    },
]


# 模拟天气查询工具
AMAP_API_KEY = "5d8cea4f9a8dfe9f7c3b4307154eef40"
AMAP_WEATHER_API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

def get_weather(city: str) -> Optional[dict]:
    try:
        params={
            "city": city,  # ✅ 改为 city
            "key": AMAP_API_KEY,
            "output": "json",  # ✅ 添加输出格式
            "extensions": "base"
        }
        headers = {
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        print(f"& 发送申请，其中URL={AMAP_WEATHER_API_URL}")
        print(f"& 用于申请的params={params}")

        response = requests.get(url=AMAP_WEATHER_API_URL, params=params,headers=headers,timeout=10)

        print(response.status_code)
        print(f"响应的内容为：{response.text}")

        data = response.json()

        if data.get("status")=="1" and data.get("lives"):
            return data
        else:
            print(f"API返回错误数据{data}")
            return None

    except requests.exceptions.Timeout:
        print("请求超时")

    except requests.exceptions.RequestException:
        print(f"网络请求超时")
        return None

    except Exception as e:
        print(f"API不响应:{e}")
        return None
'''def get_current_weather(arguments):
    weather_conditions = ["晴天", "多云", "雨天"]
    random_weather = random.choice(weather_conditions)
    location = arguments["location"]
    return f"{location}今天是{random_weather}。"
'''

# 封装模型响应函数
def get_response(messages):
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=messages,
        tools=tools,
    )
    return completion


messages = [{"role": "user", "content": USER_QUESTION}]
response = get_response(messages)
assistant_output = response.choices[0].message
if assistant_output.content is None:
    assistant_output.content = ""
messages.append(assistant_output)
# 如果不需要调用工具，直接输出内容
if assistant_output.tool_calls is None:
    print(f"无需调用天气查询工具，直接回复：{assistant_output.content}")
else:
    # 进入工具调用循环
    while assistant_output.tool_calls is not None:
        tool_call = assistant_output.tool_calls[0]
        tool_call_id = tool_call.id
        func_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"正在调用工具 [{func_name}]，参数：{arguments}")
        # 执行工具
        tool_result = get_weather(arguments)
        # 构造工具返回信息
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": tool_result,  # 保持原始工具输出
        }
        print(f"工具返回：{tool_message['content']}")
        messages.append(tool_message)
        # 再次调用模型，获取总结后的自然语言回复
        response = get_response(messages)
        assistant_output = response.choices[0].message
        if assistant_output.content is None:
            assistant_output.content = ""
        messages.append(assistant_output)
    print(f"助手最终回复：{assistant_output.content}")
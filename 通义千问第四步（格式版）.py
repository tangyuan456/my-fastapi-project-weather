from openai import OpenAI
import requests
import json
from 天气相关函数 import get_weather,parse_weather_data

class OfficialWeatherBot:
    """官方风格的工具调用天气机器人"""

    def __init__(self, qwen_api_key: str):
        self.qwen_api_key = qwen_api_key

        # 初始化OpenAI客户端（兼容阿里云）
        self.client = OpenAI(
            api_key=qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        # 定义工具
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "查询指定城市的实时天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名称，如北京、上海、深圳",
                            }
                        },
                        "required": ["city"],
                    },
                },
            }
        ]

        self.history = []
    '''
    def _query_gaode_weather(self, city: str) -> str:
        """查询高德天气API"""
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "key": self.gaode_api_key,
            "city": city,
            "extensions": "base"
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if data.get("status") == "1" and data.get("lives"):
                weather_info = data["lives"][0]
                return f"""
{city}的天气信息：
• 天气状况：{weather_info.get('weather', '未知')}
• 实时温度：{weather_info.get('temperature', '未知')}℃
• 空气湿度：{weather_info.get('humidity', '未知')}%
• 风向风力：{weather_info.get('winddirection', '未知')} {weather_info.get('windpower', '未知')}
"""
            else:
                return f"查询失败：{data.get('info', '未知错误')}"

        except Exception as e:
            return f"查询错误：{str(e)}"
    '''
    def chat(self, user_input: str) -> str:
        """主聊天函数"""
        print(f"\n用户: {user_input}")

        # 1. 添加用户消息
        self.history.append({"role": "user", "content": user_input})

        # 2. 第一次调用AI
        response = self.client.chat.completions.create(
            model="qwen-turbo",
            messages=self.history,
            tools=self.tools,
        )

        ai_message = response.choices[0].message
        self.history.append(ai_message)

        # 3. 检查工具调用
        if ai_message.tool_calls:
            print("AI决定查询天气！")

            for tool_call in ai_message.tool_calls:
                # 解析参数
                arguments = json.loads(tool_call.function.arguments)
                city = arguments.get("city", "深圳")

                # 查询天气
                weather_data = get_weather(city)  # 获取原始数据
                formatted_weather = parse_weather_data(weather_data)  # 解析
                weather_result = self._format_weather_response(city, formatted_weather)  # 格式化

                # 添加工具响应
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": weather_result,
                })

            # 第二次调用AI
            second_response = self.client.chat.completions.create(
                model="qwen-turbo",
                messages=self.history,
            )

            final_message = second_response.choices[0].message
            final_reply = final_message.content
        else:
            final_reply = ai_message.content

        # 4. 记录并返回
        self.history.append({"role": "assistant", "content": final_reply})
        return final_reply


    def _format_weather_response(self, city: str, weather_data: dict) -> str:
        """格式化天气数据为字符串"""
        if not weather_data:
            return f"无法获取{city}的天气信息"

        return f"""
{city}的实时天气信息：
• 天气状况：{weather_data.get('weather', '未知')}
• 实时温度：{weather_data.get('temperature', '未知')}℃
• 空气湿度：{weather_data.get('humidity', '未知')}%
• 风向风力：{weather_data.get('winddirection', '未知')}风 {weather_data.get('windpower', '未知')}级
• 发布时间：{weather_data.get('reporttime', '未知')}
"""


# 测试函数
def test_official_bot():
    """测试官方版机器人"""
    qwen_api_key = "sk-346cd33207e54d4298fc8c5e64210eca"
    first = OfficialWeatherBot(qwen_api_key)
    while True:
        usr_input = input("你：")
        if usr_input == "退出":
            break
        else:
            answer = first.chat(usr_input)
            print(f"AI:{answer}")

if __name__ == "__main__":
    test_official_bot()
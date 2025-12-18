import httpx
import ssl
from openai import OpenAI
import requests
import json
import urllib3
from 天气相关函数 import get_weather, parse_weather_data

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OfficialWeatherBot:
    """官方风格的工具调用天气机器人"""

    def __init__(self, qwen_api_key: str):
        self.qwen_api_key = qwen_api_key

        # 创建不验证SSL的HTTP客户端
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # 创建自定义HTTP客户端
        http_client = httpx.Client(
            verify=ssl_context,  # 禁用SSL验证
            timeout=30.0
        )

        # 初始化OpenAI客户端（兼容阿里云）
        self.client = OpenAI(
            api_key=qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            http_client=http_client,  # 使用自定义客户端
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

    def chat(self, user_input: str) -> str:
        """主聊天函数"""
        print(f"\n{'=' * 50}")
        print(f"用户: {user_input}")

        # 1. 添加用户消息
        self.history.append({"role": "user", "content": user_input})

        # 2. 第一次调用AI
        print("🤖 调用AI分析用户意图...")
        response = self.client.chat.completions.create(
            model="qwen-turbo",
            messages=self.history,
            tools=self.tools,
        )

        ai_message = response.choices[0].message
        self.history.append(ai_message)

        # 3. 检查工具调用
        if ai_message.tool_calls:
            print("🔧 AI决定查询天气！")

            for tool_call in ai_message.tool_calls:
                # 解析参数
                arguments = json.loads(tool_call.function.arguments)
                city = arguments.get("city", "深圳")
                print(f"📍 查询城市: {city}")

                # 查询天气 - 添加详细的调试信息
                print(f"📡 调用get_weather('{city}')...")
                weather_data = get_weather(city)  # 获取原始数据

                if weather_data:
                    print(f"✅ 成功获取原始天气数据")
                    print(f"📊 原始数据: {json.dumps(weather_data, ensure_ascii=False)[:200]}...")

                    formatted_weather = parse_weather_data(weather_data)  # 解析
                    print(f"📋 解析后数据: {formatted_weather}")

                    weather_result = self._format_weather_response(city, formatted_weather)  # 格式化
                    print(f"📝 格式化结果: {weather_result}")
                else:
                    print(f"❌ 获取天气数据失败")
                    weather_result = f"无法获取{city}的天气信息"

                # 添加工具响应
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": weather_result,
                })

            # 第二次调用AI
            print("🤖 AI整合天气信息生成回复...")
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
        print(f"AI: {final_reply}")
        print(f"{'=' * 50}")
        return final_reply

    def _format_weather_response(self, city: str, weather_data: dict) -> str:
        """格式化天气数据为字符串"""
        if not weather_data:
            return f"无法获取{city}的天气信息"

        # 安全获取数据
        weather = weather_data.get('weather', '未知')
        temperature = weather_data.get('temperature', '未知')
        humidity = weather_data.get('humidity', '未知')
        winddirection = weather_data.get('winddirection', '未知')
        windpower = weather_data.get('windpower', '未知')
        reporttime = weather_data.get('reporttime', '未知')

        return f"""
{city}的实时天气信息：
• 天气状况：{weather}
• 实时温度：{temperature}℃
• 空气湿度：{humidity}%
• 风向风力：{winddirection}风 {windpower}
• 发布时间：{reporttime}
"""


# 测试函数
def test_official_bot():
    """测试官方版机器人"""
    qwen_api_key = "sk-346cd33207e54d4298fc8c5e64210eca"

    print("🚀 启动天气查询机器人...")
    print("💡 输入'退出'结束对话")
    print("=" * 50)

    first = OfficialWeatherBot(qwen_api_key)

    # 先测试一个简单查询
    print("\n🧪 测试简单查询...")
    answer = first.chat("今天茂名天气如何")
    print(f"测试结果: {answer}")

    while True:
        try:
            usr_input = input("\n你：")
            if usr_input.lower() in ["退出", "exit", "quit"]:
                print("👋 再见！")
                break
            elif usr_input.strip():
                answer = first.chat(usr_input)
            else:
                print("请输入内容")
        except KeyboardInterrupt:
            print("\n👋 用户中断")
            break
        except Exception as e:
            print(f"❌ 错误: {str(e)}")


if __name__ == "__main__":
    test_official_bot()
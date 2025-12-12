import requests
from 天气相关函数 import get_weather,parse_weather_data

class Qwen:
    def __init__(self, Qwen_api_key):
        self.Qwen_api_key = Qwen_api_key
        self.Qwen_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Qwen_api_key}"
        }
        self.history = []

    def chat_smarter(self, user_input: str) -> str:
        """更智能的版本：让AI自己提取城市名"""

        self.history.append({"role": "user", "content": user_input})

        # 系统消息：让AI不仅决定是否查询，还要提取城市
        system_message = {
            "role": "system",
            "content": """你是一个智能助手，可以查询天气。
    规则：
    1. 如果用户询问天气，回复格式：查询天气[城市名]
    2. 如果不需要查询天气，正常聊天
    
    示例：
    用户：北京今天热吗？ → 你：查询天气[北京]
    用户：你好 → 你：你好！需要什么帮助？
    用户：深圳下雨吗？ → 你：查询天气[深圳]"""
        }

        messages = [system_message] + self.history

        data = {
            "model": "qwen-turbo",
            "input": {"messages": messages}
        }

        response = requests.post(self.Qwen_url, headers=self.headers, json=data)
        result = response.json()
#        print(result)
        ai_response = result["output"]["text"]

#        print(f"AI回复：{ai_response}")

        # 检查是否包含"查询天气["
        if "查询天气[" in ai_response:
            # 提取城市名："查询天气[北京]" → "北京"
            start = ai_response.find("[") + 1
            end = ai_response.find("]")
            city = ai_response[start:end]

            print(f"AI想查询{city}的天气")

            # 调用API
            weather_info = get_weather(city)

            second_message=[{"role": "user",
                             "content":f"用户的问题是{usr_input}，你查找到的相关天气信息为{weather_info}，据次回答用户的问题。"
                             }]

            # 可以更自然地回复
            second_data = {
                "model": "qwen-turbo",
                "input": {"messages":second_message}
            }
            second_response = requests.post(self.Qwen_url, headers=self.headers, json=second_data)
            second_result = second_response.json()
#            print(second_result)
            final_reply = second_result["output"]["text"]
        else:
            final_reply = ai_response


        self.history.append({"role": "assistant", "content": final_reply})
        return final_reply

if __name__ == '__main__':
    qwen_api_key = "sk-346cd33207e54d4298fc8c5e64210eca"
    first = Qwen(qwen_api_key)
    while True:
        usr_input = input("你：")
        if usr_input=="退出":
            break
        else:
            answer = first.chat_smarter(usr_input)
            print(f"AI:{answer}")
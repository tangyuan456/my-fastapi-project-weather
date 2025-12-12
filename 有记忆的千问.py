import json

import requests


class QWenChat:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.history = []  # 这个列表用来记住所有对话

    def chat(self, user_input):
        # 1. 把用户的话加入历史
        self.history.append({"role": "user", "content": user_input})

        # 2. 准备请求数据，这次发送的是整个历史
        data = {
            "model": "qwen-turbo",
            "input": {"messages": self.history},
            "parameters": {
                "result_format": "message"  # 确保返回格式正确
            }
        }

        # 3. 发送请求（同上一步）
        response = requests.post(self.url, headers=self.headers, data=json.dumps(data))
        result = response.json()
        ai_reply = result["output"]["choices"][0]["message"]["content"]

        # 4. 把AI的回复也加入历史
        self.history.append({"role": "assistant", "content": ai_reply})
        return ai_reply


# 测试
if __name__ == "__main__":
    api_key = "sk-346cd33207e54d4298fc8c5e64210eca"
    bot = QWenChat(api_key)

    print("开始对话（输入'退出'结束）:")
    while True:
        user_msg = input("你: ")
        if user_msg == "退出":
            break
        reply = bot.chat(user_msg)
        print("AI:", reply)
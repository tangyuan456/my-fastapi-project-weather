
'''
import dashscope
from dashscope import Generation

# 最基础的调用方式
dashscope.api_key = "sk-346cd33207e54d4298fc8c5e64210eca"

try:
    response = Generation.call(
        model='qwen-turbo',
        prompt='介绍一下你自己',
        stream=False
    )
    print("状态:", response.status_code)
    print("回复:", response.output.text if hasattr(response.output, 'text') else response.message)
except Exception as e:
    print("错误:", e)
'''
import requests
import json

# 1. 设置你的API Key和请求URL - 就像你设置高德的Key和天气URL一样
api_key = "sk-346cd33207e54d4298fc8c5e64210eca"  # 请替换成你的真实API Key
url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# 2. 设置请求头 - 这里和通义千问的认证方式有关，固定这么写就行
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"  # 这里使用了Bearer Token认证方式
}

# 3. 构造请求数据（Body） - 这是和大模型“对话”的核心
# 这里的“messages”列表，就是你与AI的对话历史
data = {
    "model": "qwen-turbo",  # 指定使用通义千问Turbo模型
    "input": {
        "messages": [
            {
                "role": "user",  # 角色是“用户”
                "content": "你是深圳技术大学人工智能专业的一名大一新生，但是在网上听说你这个专业双非院校的学生很难在本科毕业后找到AI相关的就业岗位。你现在正在学习AI Agent相关的内容，但是现在有人建议你去学Java或者前端才更好就业，现在一步一步分析，做一份未来发展计划。 "# 这是你问AI的问题
            },{
                "role": "user",  # 角色是“用户”
                "content": "帮你制定一份**详细的课程表**、**项目清单**、**学习资源推荐**"
            }
        ]
    },
    "parameters": {
        # 这里可以设置一些参数，比如让回答不那么随机
        "result_format": "message"
    }
}

# 4. 发送POST请求 - 这一步你非常熟悉了！
try:
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()  # 检查请求是否成功

    # 5. 解析返回的JSON数据并打印出AI的回复
    result_json = response.json()
    # 从复杂的JSON结构中提取出我们最需要的“AI回复文本”
    ai_reply = result_json["output"]["choices"][0]["message"]["content"]
    print("通义千问的回复：")
    print(ai_reply)

except requests.exceptions.RequestException as e:
    print(f"请求出错：{e}")
except json.JSONDecodeError as e:
    print(f"解析JSON出错：{e}")
except KeyError as e:
    print(f"在返回数据中找不到预期的字段：{e}")
    print("完整的返回数据是：", response.text)
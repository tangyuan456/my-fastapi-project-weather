import json
from idlelib.rpc import response_queue
from multiprocessing.connection import answer_challenge

import requests
from fastapi import params

from 天气相关函数 import get_weather,parse_weather_data

class Qwen:
    def __init__(self,Qwen_api_key):
        self.Qwen_api_key = Qwen_api_key
        self.Qwen_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Qwen_api_key}"
        }
        self.history=[]

    def chat(self,usr_question_first):
        if "天气" in usr_question_first:
            city = usr_question_first.replace("天气", "").strip()
            if city:
                weather_info = get_weather(city)
                # 把天气信息“喂”给AI，让它来组织语言
                #print(weather_info)
                usr_question= f"用户问了：{usr_question_first}。我查到的数据是：{weather_info}。请根据这个数据回答用户。"
        else:
            usr_question=usr_question_first
        self.history.append({"role":"user","content":usr_question})

        data = {
            "model":"qwen-turbo",
            "input":{"messages":self.history,},
             "parameters":{
                "result_format":"message"
            }
        }

        try:
            response=requests.post(self.Qwen_url,headers=self.headers,data=json.dumps(data))
            response.raise_for_status()  # 检查HTTP状态码

            result_json = response.json()

            # 检查响应是否包含output字段
            if "output" not in result_json or "choices" not in result_json["output"]:
                print(f"API响应格式异常：{result_json}")
                return "抱歉，我暂时无法处理您的请求。"

            question=result_json["output"]["choices"][0]["message"]["content"]

            self.history.append({"role":"user","content":question})
            return question
        except Exception as e:
            print(f"出错了,is{e}")


if __name__ == '__main__':
    qwen_api_key="sk-346cd33207e54d4298fc8c5e64210eca"
    first=Qwen(qwen_api_key)

    while True:
        user_question=input("你：")
        if user_question=="退出":
            break
        else:
            answer=first.chat(user_question)
            print(f"AI:{answer}")



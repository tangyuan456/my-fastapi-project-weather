from typing import Optional
from http.client import HTTPException
import requests
import uvicorn
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from datetime import datetime

from starlette import status

app = FastAPI(
    title="一个可以查询天气的网站",
    description="可以通过调用高德进行天气查询",
    version="1.0.0",
)

class User(BaseModel):
    city:str

class WeatherRespond(BaseModel):
    city: str
    temperature: int
    weather: str
    humidity: int
    wind: int
    visibility: int
    pressure: int
    update_time: datetime
    data_source: str

class ErrorRespond(BaseModel):
    status_code: int
    error: str
    suggest:str

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

def prase_weather(api_data:dict, city: str) -> Optional[WeatherRespond]:
    live_data=api_data["lives"][0]
    temp_str = live_data.get('temperature','0')
    try:
        temperature=int(float(temp_str))
    except (ValueError,TypeError):
        temperature=0

    humidity_str=live_data.get('humidity','0')
    try:
        humidity=int(float(humidity_str.split('%')[0]))
    except (ValueError,TypeError):
        humidity=0

    wind_str=live_data.get('windpower','0')
    try:
        wind=int(''.join(filter(str.isdigit,wind_str)))
    except (ValueError,TypeError):
        wind=0

    vis_str=live_data.get('visibility','0')
    try:
        visibility=int(float(vis_str.split('k')[0]))
    except (ValueError,TypeError):
        visibility=0

    pressure_str=live_data.get('pressure','0')
    try:
        pressure=int(float(pressure_str.split('h')[0]))
    except (ValueError,TypeError):
        pressure=0

    return WeatherRespond(
        city=live_data.get('city',city),
        temperature=temperature,
        weather=live_data.get('weather',''),
        humidity=humidity,
        wind=wind,
        visibility=visibility,
        pressure=pressure,
        update_time=datetime.now(),
        data_source="高德"
    )

@app.get("/")
async def root():
    return {
        "status": "success",
        "massage":"欢迎来到天气查询系统",
        "tips": {
            "/docs            查看文档",
            "/weather         查看天气",
            "/weather/batch   批量查看天气",
            "/healthy         查看天气",
        }
    }

@app.get("/healthy")
async def healthy():
    return {
        "status": "success",
        "healthy":"ok",
    }

@app.get("/weather")
async def search_weather(
        city_search: str=Query(...,description="输入城市查询天气"),
):
    print("我要开始对输入的城市进行处理")
    city=city_search.strip()
    if not city:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="输入城市不可为空"
        )
    if len(city)>20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="输入的城市名字过长"
        )
    api_data=get_weather(city)
    if api_data:
        return prase_weather(api_data, city)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法获取天气信息，请检查城市名称是否正确。"
        )

@app.post("/weather")
async def weather(city:User):
    city=city.city.strip()
    return await search_weather(city)

@app.get("/weather/batch")
async def batch_weather(city_list: str):
    cities=city_list.split(",")
    city_results=[]
    for city in cities:
        city=city.strip()
        if city:
            try:
                api_data=get_weather(city)
                if api_data:
                    city_results.append(prase_weather(api_data, city))
            except Exception as e:
                print(f"查询城市 {city} 失败: {e}")
                continue
    return {
        "status": "success",
        "count": len(city_results),
        "results": city_results
    }


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8007)

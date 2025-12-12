#虚拟天气查询系统（无法实时更新）
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import random

app = FastAPI(
    title="天气查询",
    description="可以模拟查询天气",
    version="1.0.0",
)

class WeatherRespond(BaseModel):
    city: str
    temper: int
    type: str
    windy_speed: float

city1={"beijing":"北京","shanghai":"上海","sichuan":"四川","guangdong":"广东"}

weather_type=["晴天","小雨","阴天","多云","暴雨"]

@app.get("/")
async def root():
    return {"message":"Welcome to weather_check API!",
            "status":"success",}

@app.get("/Weather")
async def get_weather(city_name:str):           #查询城市的天气
    if city_name not in city1:
        return {
            "status":"fail",
            "message":f"找不到{city_name}相关数据",
            "available_city":list(city1.keys())
        }

    weather_description=WeatherRespond(
        city=city1[city_name],
        temper=random.randint(-5,30),
        type=random.choice(weather_type),
        windy_speed=random.randint(50,100)
    )

    return {
        "status":"success",
        "Weather_description":weather_description,
        "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)
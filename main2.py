#在 FastAPI 中，可以将 Pydantic 模型用作请求体（Request Body），以自动验证和解析客户端发送的数据。
from fastapi import FastAPI, Query
from pydantic import BaseModel    #引用模块

app = FastAPI()

class Item(BaseModel):             #创建一个新的名为Item的Pydantic模型
    name: str
    description: str=None          #一定要包含name，price
    price: float                   #description和tax是可选字段，默认值为None
    tax: float=None

'''@app.post("/items/")
def items(item: Item):     #create_item 路由处理函数接受一个名为 item 的参数，其类型是 Item 模型。
    return item'''         #FastAPI 将自动验证传入的 JSON 数据是否符合模型的定义，并将其转换为 Item 类型的实例。
@app.post("/items/")
def read_item(item: Item, q: str = Query(..., max_length=10)):
    return {"item":Item,"q":q}


import requests
import json


def test_gaode_api():
    # 你的高德API密钥
    gaode_key = "5d8cea4f9a8dfe9f7c3b4307154eef40"
    city = "茂名"

    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {
        "key": gaode_key,
        "city": city,
        "extensions": "base",
        "output": "JSON"
    }

    try:
        # 禁用SSL验证
        response = requests.get(url, params=params, verify=False, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应内容:\n{json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"错误: {str(e)}")

def get_valid_number_input(prompt: str, min_val: float, max_val: float) -> float:
    """
    获取有效的数字输入

    参数:
        prompt: 提示文本
        min_val: 最小值
        max_val: 最大值

    返回值:
        float: 有效的数字
    """
    while True:
        try:
            value = float(input(prompt))
            if min_val <= value <= max_val:
                print(value)
                return value
            else:
                print(f"请输入 {min_val} 到 {max_val} 之间的数字")
        except ValueError:
            print("请输入有效的数字")


if __name__ == "__main__":
    get_valid_number_input("输入你的体重",30,200)
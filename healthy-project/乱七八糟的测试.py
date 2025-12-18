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


if __name__ == "__main__":
    test_gaode_api()
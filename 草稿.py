import requests

# 简单的测试
response = requests.get('https://httpbin.org/json')
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    print("✅ requests 安装成功！")
    data = response.json()
    print("测试请求成功，返回数据格式正确")
else:
    print("❌ 请求失败")
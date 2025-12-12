import requests

# 1. 发送 GET 请求
username = 'torvalds'  # Linux 之父 Linus Torvalds 的 GitHub 用户名
url = f'https://api.github.com/users/{username}'
response = requests.get(url)

# 2. 检查请求是否成功
if response.status_code == 200:
    # 3. 解析返回的 JSON 数据
    user_data = response.json()

    # 4. 提取我们需要的信息
    print(f"用户名： {user_data['name']}")
    print(f"公司： {user_data['company']}")
    print(f"博客： {user_data['blog']}")
    print(f"公开仓库数： {user_data['public_repos']}")
else:
    print('获取用户信息失败！')
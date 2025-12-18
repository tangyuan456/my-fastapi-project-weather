from idlelib import history

import httpx
import ssl
from openai import OpenAI
import json
import urllib3
import io
from contextlib import redirect_stdout
from 初次录入 import (load_profiles, save_profiles, create_user_profile, delete_user_profile,
                      display_user_profile, update_user_weight, calculate_bmi, USER_PROFILES)

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HealthAssistantBot:
    """健康减肥助手机器人（一对一版本）"""

    def __init__(self, qwen_api_key: str):
        self.qwen_api_key = qwen_api_key
        self.current_user = None  # 当前登录的用户

        # 创建不验证SSL的HTTP客户端
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # 创建自定义HTTP客户端
        http_client = httpx.Client(
            verify=ssl_context,  # 禁用SSL验证
            timeout=30.0
        )

        # 初始化OpenAI客户端（兼容阿里云）
        self.client = OpenAI(
            api_key=qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            http_client=http_client,  # 使用自定义客户端
        )

        # 加载用户数据
        self.users = load_profiles()

        # 定义工具 - 健康减肥相关功能
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_health_profile",
                    "description": "创建健康档案，收集用户的基本健康信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "执行的动作，固定为'create'",
                                "enum": ["create"]
                            }
                        },
                        "required": ["action"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_user_weight",
                    "description": "更新当前用户的体重信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "new_weight": {
                                "type": "number",
                                "description": "新的体重值（kg）",
                            }
                        },
                        "required": ["new_weight"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "display_my_profile",
                    "description": "查看当前用户的健康档案详情",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "执行的动作，固定为'view'",
                                "enum": ["view"]
                            }
                        },
                        "required": ["action"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_bmi",
                    "description": "计算BMI指数并给出健康建议",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "weight": {
                                "type": "number",
                                "description": "体重（kg）",
                            },
                            "height": {
                                "type": "number",
                                "description": "身高（cm）",
                            }
                        },
                        "required": ["weight", "height"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_my_profile",
                    "description": "删除当前用户的健康档案",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "执行的动作，固定为'delete'",
                                "enum": ["delete"]
                            }
                        },
                        "required": ["action"],
                    },
                },
            }
        ]

        self.history = [
            {
                "role": "system",
                "content": """你是一对一健康减肥助手AI。你的任务是专门为当前用户管理健康档案、跟踪减肥进度、提供健康建议。

                你专门服务当前用户，功能包括：
                1. 创建个人健康档案（如果用户还没有档案）
                2. 更新个人体重信息
                3. 查看个人健康数据
                4. 计算BMI指数
                5. 提供个性化减肥建议
                6. 删除个人档案

                请以亲密、专业的个人健康教练身份与用户交流，使用友好、鼓励的中文交流。
                始终关注当前用户的个人健康数据，提供个性化建议。"""
            }
        ]

    def check_user_exists(self) -> bool:
        """检查是否有用户档案存在"""
        return len(self.users) > 0

    def get_current_user(self) -> str:
        """获取当前用户昵称（如果有的话）"""
        if not self.users:
            return None
        # 取第一个用户（一对一应用只有一个用户）
        return list(self.users.keys())[0]

    def _execute_tool(self, function_name: str, arguments: dict) -> str:
        """执行工具函数并返回结果"""
        print(f"🔧 执行工具: {function_name}")
        print(f"📋 参数: {arguments}")

        try:
            if function_name == "create_health_profile":
                # 创建健康档案
                if self.check_user_exists():
                    user_nickname = self.get_current_user()
                    return f"您已经有健康档案了！当前用户是：{user_nickname}。如需重新创建，请先删除现有档案。"

                user_data = create_user_profile()     #
                if user_data:
                    # 更新本地用户数据
                    self.users = load_profiles()
                    self.current_user = user_data.get('nickname')
                    return f"✅ 成功创建您的个人健康档案！欢迎 {self.current_user}，从现在开始我会陪伴您的健康减肥之旅！"
                else:
                    return "❌ 创建健康档案失败或您取消了操作。"           #

            elif function_name == "update_user_weight":
                # 更新体重
                if not self.check_user_exists():
                    return "您还没有创建健康档案，请先创建档案再来更新体重。"

                user_nickname = self.get_current_user()
                new_weight = arguments.get("new_weight", 0)

                if new_weight <= 0:
                    return "请输入有效的体重值。"

                # 调用update_user_weight函数（注意：原函数需要nickname参数）
                success = update_user_weight(user_nickname)
                if success:
                    self.users = load_profiles()  # 重新加载数据
                    current_weight = self.users[user_nickname]['current_weight_kg']
                    bmi = self.users[user_nickname]['bmi']
                    status = self.users[user_nickname]['status']
                    return f"✅ 体重更新成功！\n📊 当前体重: {current_weight}kg\n📈 BMI: {bmi} ({status})"
                else:
                    return "❌ 更新体重失败。"

            elif function_name == "display_my_profile":
                # 查看个人档案
                if not self.check_user_exists():
                    return "您还没有创建健康档案，请先创建档案。"

                user_nickname = self.get_current_user()
                user_data = self.users.get(user_nickname)

                # 调用显示函数并捕获输出
                f = io.StringIO()
                with redirect_stdout(f):
                    display_user_profile(user_data)
                output = f.getvalue()
                return f"📋 您的个人健康档案详情：\n{output}"

            elif function_name == "calculate_bmi":
                # 计算BMI
                weight = arguments.get("weight", 0)
                height = arguments.get("height", 0)

                if weight <= 0 or height <= 0:
                    return "请输入有效的体重和身高值。"

                bmi_info = calculate_bmi(weight, height)
                return f"""📊 BMI计算结果：
                • 体重: {weight}kg
                • 身高: {height}cm
                • BMI指数: {bmi_info.get('bmi')}
                • 健康状态: {bmi_info.get('status')}
                • 建议: {bmi_info.get('suggestion')}"""

            elif function_name == "delete_my_profile":
                # 删除个人档案
                if not self.check_user_exists():
                    return "您还没有创建健康档案。"

                user_nickname = self.get_current_user()

                success = delete_user_profile(user_nickname)
                if success:
                    self.users = load_profiles()  # 重新加载数据
                    self.current_user = None
                    return f"✅ 您的健康档案已删除。如需重新开始，可以创建新的健康档案。"
                else:
                    return f"❌ 删除档案失败。"

            else:
                return f"未知的工具函数: {function_name}"

        except Exception as e:
            print(f"❌ 工具执行错误: {e}")
            return f"执行操作时出现错误: {str(e)}"

    def chat(self, user_input: str) -> str:
        """主聊天函数"""
        print(f"\n{'=' * 50}")
        print(f"用户: {user_input}")

        # 1. 添加用户消息
        self.history.append({"role": "user", "content": user_input})

        # 2. 第一次调用AI
        print("🤖 AI分析用户需求...")
        response = self.client.chat.completions.create(
            model="qwen-turbo",
            messages=self.history,
            tools=self.tools,
            tool_choice="auto"
        )

        ai_message = response.choices[0].message
        self.history.append(ai_message)

        # 3. 检查工具调用
        if ai_message.tool_calls:
            print("🔧 AI决定调用工具！")

            for tool_call in ai_message.tool_calls:
                # 解析参数
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                # 执行工具
                tool_result = self._execute_tool(function_name, arguments)
                print(f"✅ 工具执行结果: {tool_result[:100]}...")

                # 添加工具响应
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

            # 第二次调用AI（整合结果）
            print("🤖 AI整合信息生成回复...")
            second_response = self.client.chat.completions.create(
                model="qwen-turbo",
                messages=self.history,
            )

            final_message = second_response.choices[0].message
            final_reply = final_message.content
        else:
            final_reply = ai_message.content

        # 4. 记录并返回
        self.history.append({"role": "assistant", "content": final_reply})
        print(f"AI: {final_reply[:100]}...")
        print(f"{'=' * 50}")
        return final_reply

    def interactive_chat(self):
        """交互式聊天"""
        print("🚀 启动一对一健康减肥助手...")
        print("💡 我是您的专属健康教练，可以帮您：")
        print("  1. 创建个人健康档案")
        print("  2. 更新体重信息")
        print("  3. 查看健康数据")
        print("  4. 计算BMI指数")
        print("  5. 获取个性化减肥建议")
        print("  6. 删除个人档案（重新开始）")

        # 检查是否有现有用户
        if self.check_user_exists():
            user_nickname = self.get_current_user()
            print(f"\n👋 欢迎回来，{user_nickname}！")
            self.history.append({
                "role": "system",
                "content": f"当前用户是：{user_nickname}。请以专属健康教练的身份为他/她服务。"
            })
        else:
            print("\n👋 欢迎新朋友！您还没有健康档案，让我们一起来创建档案吧。")
            user_data = create_user_profile()
            if user_data:
                # 更新本地用户数据
                self.users = load_profiles()
                self.current_user = user_data.get('nickname')
                print(f"✅ 成功创建您的个人健康档案！欢迎 {self.current_user}，从现在开始我会陪伴您的健康减肥之旅！")
            else:
                print("❌ 创建健康档案失败或您取消了操作。")

        print("💡 输入'退出'结束对话,'菜单'可以查看服务列表，'清空'可以清空掉所有聊天记录，'查看聊天历史'可以查看你和小助手的所有对话，")
        print("=" * 50)

        while True:
            try:
                user_input = input("\n您：").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["退出", "exit", "quit", "bye"]:
                    print("👋 期待下次继续陪伴您的健康之旅，再见！")
                    break

                # 处理特殊命令
                if user_input == "菜单":
                    self.show_menu()
                    continue
                elif user_input == "帮助":
                    self.show_help()
                    continue
                elif user_input == "查看聊天历史":
                    self.display_history()
                    continue
                elif user_input == "清空":
                    self.clear_history()
                    print("🗑️ 对话历史已清空")
                    continue

                # 调用AI聊天
                response = self.chat(user_input)
                print(f"\n助手：{response}")

            except KeyboardInterrupt:
                print("\n\n👋 下次见，记得坚持健康生活哦！")
                break
            except Exception as e:
                print(f"\n❌ 错误: {str(e)}")
                print("💡 请重新输入或输入'帮助'查看帮助")

    def show_menu(self):
        """显示功能菜单"""
        if self.check_user_exists():
            user_nickname = self.get_current_user()
            menu = f"""
            📋 {user_nickname}的专属健康教练菜单：

            1. 📝 查看我的档案
               • 输入："查看我的档案"
               • 输入："显示我的健康信息"

            2. ⚖️ 更新体重
               • 输入："更新体重"
               • 输入："记录今天体重"
               • 输入："我现在的体重是65kg"

            3. 📊 计算BMI
               • 输入："计算我的BMI"
               • 输入："帮我算一下BMI"

            4. 💪 获取建议
               • 输入："给我一些减肥建议"
               • 输入："怎么减肚子"
               • 输入："健康饮食建议"

            5. 🔄 重新开始
               • 输入："删除档案"
               • 输入："重新开始"

            其他命令：
            • "菜单" - 显示此菜单
            • "帮助" - 查看帮助
            • "清空" - 清空对话历史
            • "退出" - 结束对话
            """
        else:
            menu = """
            📋 健康减肥助手菜单：

            1. 📝 创建健康档案
               • 输入："创建档案"
               • 输入："开始健康记录"
               • 输入："注册健康档案"

            2. 📊 计算BMI
               • 输入："帮我计算BMI"
               • 输入："身高175体重70的BMI是多少"

            其他命令：
            • "菜单" - 显示此菜单
            • "帮助" - 查看帮助
            • "清空" - 清空对话历史
            • "退出" - 结束对话
            """
        print(menu)

    def show_help(self):
        """显示帮助信息"""
        help_text = """
        🆘 一对一健康减肥助手使用帮助：

        👤 我是您的专属健康教练：
        • 专门为您一个人服务
        • 管理您的个人健康档案
        • 跟踪您的体重变化
        • 提供个性化健康建议

        💬 您可以这样和我交流：
        • 创建档案："我想创建健康档案"
        • 日常记录："今天体重65.5kg"
        • 寻求建议："我想减肥，有什么好方法？"
        • 查看进度："我的减肥进度怎么样？"

        🔧 专属功能：
        1. 个人档案 - 创建、查看、删除您的健康信息
        2. 体重跟踪 - 记录您的体重变化趋势
        3. BMI计算 - 评估您的身体健康状况
        4. 个性化建议 - 基于您的数据提供专属建议

        📝 示例对话：
        您：创建档案
        助手：好的，现在为您创建个人健康档案...

        您：今天体重70.5kg
        助手：已记录您的体重！当前BMI是...

        您：给我一些饮食建议
        助手：根据您的档案，我建议...
        """
        print(help_text)

    def display_history(self):
        if history:
            print(history)
        else:
            print("can't find history")

    def clear_history(self):
        """清空对话历史"""
        if self.check_user_exists():
            user_nickname = self.get_current_user()
            self.history = [
                {
                    "role": "system",
                    "content": f"""你是一对一健康减肥助手AI，专门为{user_nickname}服务。

                    你专门服务当前用户{user_nickname}，功能包括：
                    1. 管理个人健康档案
                    2. 更新个人体重信息
                    3. 查看个人健康数据
                    4. 计算BMI指数
                    5. 提供个性化减肥建议
                    6. 删除个人档案

                    请以亲密、专业的个人健康教练身份与{user_nickname}交流，使用友好、鼓励的中文交流。
                    始终关注{user_nickname}的个人健康数据，提供个性化建议。"""
                }
            ]
        else:
            self.history = [
                {
                    "role": "system",
                    "content": """你是一对一健康减肥助手AI。你的任务是专门为当前用户管理健康档案、跟踪减肥进度、提供健康建议。

                    你专门服务当前用户，功能包括：
                    1. 创建个人健康档案（如果用户还没有档案）
                    2. 更新个人体重信息
                    3. 查看个人健康数据
                    4. 计算BMI指数
                    5. 提供个性化减肥建议
                    6. 删除个人档案

                    请以亲密、专业的个人健康教练身份与用户交流，使用友好、鼓励的中文交流。
                    始终关注当前用户的个人健康数据，提供个性化建议。"""
                }
            ]


def test_basic_functions():
    """测试基本功能"""
    print("🧪 测试健康减肥助手基本功能...")

    # 这里需要替换成你的API Key
    qwen_api_key = "sk-346cd33207e54d4298fc8c5e64210eca"

    bot = HealthAssistantBot(qwen_api_key)

    # 测试创建档案
    print("\n1. 测试创建健康档案...")
    test_input = "我想创建一个健康档案"
    print(f"测试输入: {test_input}")
    response = bot.chat(test_input)
    print(f"响应: {response[:100]}...")

    # 测试其他功能
    print("\n2. 测试查看档案...")
    test_input = "查看我的档案"
    print(f"测试输入: {test_input}")
    response = bot.chat(test_input)
    print(f"响应: {response[:100]}...")

    print("\n3. 测试计算BMI...")
    test_input = "计算BMI，体重70，身高175"
    print(f"测试输入: {test_input}")
    response = bot.chat(test_input)
    print(f"响应: {response[:100]}...")


def main():
    """主函数"""
    import sys

    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_basic_functions()
            return
        elif sys.argv[1] == "api":
            # 这里替换成你的API Key
            qwen_api_key = "sk-346cd33207e54d4298fc8c5e64210eca"
            bot = HealthAssistantBot(qwen_api_key)
            bot.interactive_chat()
            return

    # 交互式选择模式
    print("🏥 一对一健康减肥助手")
    print("=" * 50)
#    print("1. 🧪 测试模式 - 快速测试基本功能")
    print("2. 💬 对话模式 - 交互式专属健康教练")
    print("3. 🚪 退出")
    print("=" * 50)

    choice = input("请选择模式 (1-3): ").strip()

#    if choice == "1":
#        test_basic_functions()
    if choice == "2":
        # 这里需要替换成你的API Key
        qwen_api_key = "sk-346cd33207e54d4298fc8c5e64210eca"
        bot = HealthAssistantBot(qwen_api_key)
        bot.interactive_chat()
    elif choice == "3":
        print("👋 再见！")
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    main()
import httpx
import ssl
from openai import OpenAI
import json
import urllib3
from 初次录入 import (load_profiles,save_profiles, create_user_profile,
                    display_user_profile, update_user_weight, calculate_bmi)

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HealthAssistantBot:
    """健康减肥助手机器人"""

    def __init__(self, qwen_api_key: str):
        self.qwen_api_key = qwen_api_key

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
                    "description": "创建新的健康档案，收集用户的基本健康信息",
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
                    "name": "update_weight",
                    "description": "更新用户的体重信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "nickname": {
                                "type": "string",
                                "description": "用户的昵称",
                            },
                            "new_weight": {
                                "type": "number",
                                "description": "新的体重值（kg）",
                            }
                        },
                        "required": ["nickname", "new_weight"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "view_profile",
                    "description": "查看用户的健康档案详情",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "nickname": {
                                "type": "string",
                                "description": "用户的昵称",
                            }
                        },
                        "required": ["nickname"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_users",
                    "description": "列出所有注册用户",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "执行的动作，固定为'list'",
                                "enum": ["list"]
                            }
                        },
                        "required": ["action"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_statistics",
                    "description": "获取健康数据统计信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "执行的动作，固定为'stats'",
                                "enum": ["stats"]
                            }
                        },
                        "required": ["action"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_bmi_tool",
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
            }
        ]

        self.history = [
            {
                "role": "system",
                "content": """你是一个专业的健康减肥助手AI。你的任务是帮助用户管理健康档案、跟踪减肥进度、提供健康建议。

                你可以帮助用户：
                1. 创建健康档案
                2. 更新体重信息
                3. 查看健康数据
                4. 计算BMI指数
                5. 提供减肥建议

                请友好、专业地回应用户的需求，使用中文交流。"""
            }
        ]

    def _execute_tool(self, function_name: str, arguments: dict) -> str:
        """执行工具函数并返回结果"""
        print(f"🔧 执行工具: {function_name}")
        print(f"📋 参数: {arguments}")

        try:
            if function_name == "create_health_profile":
                # 创建健康档案
                user_data = create_user_profile()
                if user_data:
                    # 更新本地用户数据
                    self.users = load_profiles()
                    return f"成功创建用户 '{user_data.get('nickname')}' 的健康档案！"
                else:
                    return "创建健康档案失败或用户取消了操作。"

            elif function_name == "update_weight":
                # 更新体重
                nickname = arguments.get("nickname", "")
                new_weight = arguments.get("new_weight", 0)

                if nickname not in self.users:
                    return f"用户 '{nickname}' 不存在，请先创建健康档案。"

                success = update_user_weight(nickname)
                if success:
                    self.users = load_profiles()  # 重新加载数据
                    return f"成功更新用户 '{nickname}' 的体重信息！"
                else:
                    return f"更新用户 '{nickname}' 体重失败。"

            elif function_name == "view_profile":
                # 查看档案
                nickname = arguments.get("nickname", "")
                profile = get_user_profile(nickname)
                if profile:
                    # 调用显示函数并捕获输出
                    import io
                    from contextlib import redirect_stdout

                    f = io.StringIO()
                    with redirect_stdout(f):
                        display_user_profile(profile)
                    output = f.getvalue()
                    return f"用户 '{nickname}' 的健康档案详情：\n{output}"
                else:
                    return f"用户 '{nickname}' 不存在。"

            elif function_name == "list_users":
                # 列出用户
                import io
                from contextlib import redirect_stdout

                f = io.StringIO()
                with redirect_stdout(f):
                    list_all_users()
                output = f.getvalue()
                return f"所有注册用户列表：\n{output}"

            elif function_name == "get_statistics":
                # 获取统计
                import io
                from contextlib import redirect_stdout

                f = io.StringIO()
                with redirect_stdout(f):
                    display_statistics()
                output = f.getvalue()
                return f"健康数据统计信息：\n{output}"

            elif function_name == "calculate_bmi_tool":
                # 计算BMI
                weight = arguments.get("weight", 0)
                height = arguments.get("height", 0)

                if weight <= 0 or height <= 0:
                    return "请输入有效的体重和身高值。"

                bmi_info = calculate_bmi(weight, height)
                return f"""BMI计算结果：
                • 体重: {weight}kg
                • 身高: {height}cm
                • BMI指数: {bmi_info.get('bmi')}
                • 健康状态: {bmi_info.get('status')}
                • 建议: {bmi_info.get('suggestion')}"""

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
        print("🚀 启动AI健康减肥助手...")
        print("💡 我可以帮您：")
        print("  1. 创建健康档案")
        print("  2. 更新体重信息")
        print("  3. 查看健康数据")
        print("  4. 计算BMI指数")
        print("  5. 获取减肥建议")
        print("💡 输入'退出'结束对话")
        print("=" * 50)

        while True:
            try:
                user_input = input("\n您：").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["退出", "exit", "quit", "bye"]:
                    print("👋 感谢使用健康减肥助手，再见！")
                    break

                # 处理特殊命令
                if user_input == "菜单":
                    self.show_menu()
                    continue
                elif user_input == "帮助":
                    self.show_help()
                    continue
                elif user_input == "清空":
                    self.clear_history()
                    print("🗑️ 对话历史已清空")
                    continue

                # 调用AI聊天
                response = self.chat(user_input)
                print(f"\n助手：{response}")

            except KeyboardInterrupt:
                print("\n\n👋 用户中断，正在退出...")
                break
            except Exception as e:
                print(f"\n❌ 错误: {str(e)}")
                print("💡 请重新输入或输入'帮助'查看帮助")

    def show_menu(self):
        """显示功能菜单"""
        menu = """
        📋 健康减肥助手功能菜单：

        1. 📝 创建健康档案
           • 输入："我想创建一个健康档案"
           • 输入："帮我记录健康信息"

        2. ⚖️ 更新体重
           • 输入："更新我的体重"
           • 输入："记录今天体重65kg"

        3. 👤 查看档案
           • 输入："查看我的健康档案"
           • 输入："张三的健康情况"

        4. 👥 查看所有用户
           • 输入："有哪些用户"
           • 输入："显示所有用户"

        5. 📊 查看统计
           • 输入："统计数据"
           • 输入："健康报告"

        6. 🧮 计算BMI
           • 输入："帮我计算BMI"
           • 输入："身高175体重70的BMI"

        7. 💪 减肥建议
           • 输入："如何减肥"
           • 输入："给我一些健康建议"

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
        🆘 健康减肥助手使用帮助：

        🤖 我是一个AI健康助手，可以：
        • 管理您的健康档案
        • 跟踪体重变化
        • 计算健康指标
        • 提供个性化建议

        💬 您可以这样和我交流：
        • 自然语言对话："我想减肥，有什么建议吗？"
        • 具体指令："为李四创建一个健康档案"
        • 查询信息："查看王五的BMI"

        🔧 支持的功能：
        1. 档案管理 - 创建、查看、更新健康信息
        2. 体重跟踪 - 记录体重变化趋势
        3. BMI计算 - 评估身体健康状况
        4. 数据分析 - 查看健康统计报告
        5. 个性化建议 - 基于您的数据提供建议

        📝 示例对话：
        您：帮我创建一个健康档案
        助手：好的，现在为您创建健康档案...

        您：我的身高175，体重75，BMI多少？
        助手：根据您的数据计算得出...

        您：显示所有用户
        助手：以下是所有注册用户...
        """
        print(help_text)

    def clear_history(self):
        """清空对话历史"""
        self.history = [
            {
                "role": "system",
                "content": """你是一个专业的健康减肥助手AI。你的任务是帮助用户管理健康档案、跟踪减肥进度、提供健康建议。

                你可以帮助用户：
                1. 创建健康档案
                2. 更新体重信息
                3. 查看健康数据
                4. 计算BMI指数
                5. 提供减肥建议

                请友好、专业地回应用户的需求，使用中文交流。"""
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
    test_inputs = [
        "我想创建一个健康档案",
        "帮我记录一下健康信息",
        "开始记录我的健康数据",
        "新建一个减肥档案"
    ]

    for test_input in test_inputs[:1]:  # 只测试第一个
        print(f"\n测试输入: {test_input}")
        response = bot.chat(test_input)
        print(f"响应: {response[:100]}...")

    # 测试其他功能
    print("\n2. 测试其他功能...")
    other_tests = [
        "查看所有用户",
        "计算BMI，体重70，身高175",
        "获取健康统计"
    ]

    for test in other_tests:
        print(f"\n测试: {test}")
        response = bot.chat(test)
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
    print("🏥 AI健康减肥助手")
    print("=" * 50)
    print("1. 🧪 测试模式 - 快速测试基本功能")
    print("2. 💬 对话模式 - 交互式AI助手")
    print("3. 🚪 退出")
    print("=" * 50)

    choice = input("请选择模式 (1-3): ").strip()

    if choice == "1":
        test_basic_functions()
    elif choice == "2":
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
import datetime
from idlelib import history

import httpx
import ssl
from openai import OpenAI
import json
import urllib3
import io
from contextlib import redirect_stdout

from websocket import continuous_frame

from 初次录入 import (load_profiles, save_profiles, create_user_profile, delete_user_profile,
                      search_user_profile, update_user_weight, calculate_bmi, USER_PROFILES)
from 每日记录相关函数 import DailyHealthRecorder

from 饮食相关函数 import (update_meal_status,get_daily_plan)

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HealthAssistantBot:
    """健康减肥助手机器人（一对一版本）"""

    def __init__(self, qwen_api_key: str):
        self.qwen_api_key = qwen_api_key
        self.current_user = None  # 当前登录的用户
        self.recorder = DailyHealthRecorder()
        self.update_meal_status = update_meal_status.__get__(self, HealthAssistantBot)
        self.get_daily_plan = get_daily_plan.__get__(self, HealthAssistantBot)
        self.save_profiles_func = save_profiles

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
        # 在 __init__ 方法中修改工具描述
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_my_profile",
                    "description": "【必须优先调用】获取用户的完整健康档案数据，包括身高、体重、BMI、体脂率等。当需要用户的健康信息来回答问题时，必须首先调用此工具获取基础数据。",
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
                    "description": "【经常与search_my_profile一起调用】计算用户的BMI指数。在获取用户档案数据后，通常需要调用此工具计算最新的BMI。",
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
                    "name": "update_user_weight",
                    "description": "更新当前用户的体重信息。调用此工具后会触发重新计算BMI。",
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
            },
            {
                "type": "function",
                "function": {
                    "name": "update_meal_status",
                    "description": "【重要！用户报告用餐情况时必须调用】当用户报告吃了早餐/午餐/晚餐时，自动识别时间并更新对应餐次的状态。调用此工具可以记录用户的用餐情况。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_input": {
                                "type": "string",
                                "description": "用户描述用餐情况的完整输入文本",
                            },
                            "meal_type": {
                                "type": "string",
                                "description": "用餐类型。如果用户明确说了就传入明确值；如果不确定，让AI自行判断并传入'auto'",
                                "enum": ["早餐", "午餐", "晚餐", "auto"]
                            }
                        },
                        "required": ["user_input", "meal_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_daily_plan",
                    "description": "获取用户当前时间段对应的饮食和运动计划。工具会根据当前时间自动判断是早餐、午餐还是晚餐时间，并返回相应的计划。也可以查看饮水目标和运动计划。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "view_type": {
                                "type": "string",
                                "description": "查看的类型：'current_meal'只查看当前餐次的计划，'next_meal'查看下一餐的计划，'all'查看全天计划，'drink'查看饮水计划，'exercise'查看运动计划",
                                "enum": ["current_meal", "next_meal", "all", "drink", "exercise"]
                            }
                        },
                        "required": ["view_type"],
                    },
                },
            }
        ]

        # 修改系统提示
        self.history = [
            {
                "role": "system",
                "content": """你是一对一健康减肥助手AI。你的任务是专门为当前用户管理健康档案、跟踪减肥进度、提供健康建议。

        **重要指令：**
        1. **多工具调用策略**：当用户的问题需要多个数据时，你应该一次性调用多个工具。例如：
           - 用户问"我的健康状况怎么样？" → 同时调用 `search_my_profile` 和 `calculate_bmi`
           - 用户提供新体重"今天体重65kg" → 调用 `update_user_weight`，然后自动调用 `calculate_bmi`

        2. **工具调用顺序**：
           a. 首先检查是否需要用户数据 → 调用 `search_my_profile`
           b. 然后检查是否需要计算 → 调用 `calculate_bmi`
           c. 最后生成个性化建议

        3. **执行流程**：
           - 检查当前日期文件是否存在
           - 获取用户问题
           - 分析需要哪些数据
           - 一次性调用所有必要的工具
           - 整合所有工具结果
           - 生成最终回复

        4. **工具依赖关系**：
           - `search_my_profile` 通常是第一步
           - `calculate_bmi` 通常需要身高体重数据
           - `update_user_weight` 后通常需要重新计算BMI
           
        **重要时间判断规则：**
        1. **用餐时间判断**（基于北京时间）：
           - 早餐时间：5:00-10:59（早上5点到10点59分）
           - 午餐时间：11:00-15:59（上午11点到下午3点59分）
           - 晚餐时间：16:00-21:59（下午4点到晚上9点59分）
           - 宵夜时间：22:00-4:59（晚上10点到第二天凌晨4点59分）
        
        2. **当前时间判断**：你需要根据对话发生的实际时间来判断用餐类型。
        
        **工具调用规则：**
        1. 当用户报告用餐情况时，必须调用 `update_meal_status` 工具
        2. 根据当前时间自动判断meal_type：
           - 如果当前时间在晚餐时间，meal_type传"晚餐"
           - 如果当前时间在宵夜时间，meal_type传"auto"（让函数自动判断为"宵夜"）

        请以亲密、专业的个人健康教练身份与用户交流，使用友好、鼓励的中文交流。
        始终关注当前用户的个人健康数据，提供个性化建议。"""
            }
        ]

    def _init_daily_system(self):
        """初始化每日系统"""
        print("📅 正在初始化今日健康系统...")

        # 检查是否有今日记录
        if not self.recorder.check_today_record_exists():
            print("📝 创建新的一日记录")

        # 获取用户档案（如果有的话）
            user_profile = None
            if self.check_user_exists():
                user_nickname = self.get_current_user()
                if user_nickname in self.users:
                    user_profile = self.users[user_nickname]

            # 自动生成今日计划（使用大模型）
            success = self.recorder.auto_generate_daily_plan(self.client, user_profile)

            if success:
                print("🎯 AI已为您生成个性化健康计划！")
            else:
                print("⚠️ 自动生成计划失败，您可以手动设置或使用默认计划")

        # 显示当前喝水状态
        data = self.recorder.load_today_record()
        print(f"💧 今日喝水目标: {data.get('drink_plan', 8)}杯")

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

        if function_name == "update_meal_status":
            print(f"🕐 当前时间：{datetime.datetime.now().strftime('%H:%M:%S')}")
            print(f"🔍 检查方法是否存在：{hasattr(self, 'update_meal_status')}")

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
                success = update_user_weight(user_nickname, new_weight)
                if success:
                    self.users = load_profiles()  # 重新加载数据
                    current_weight = self.users[user_nickname]['current_weight_kg']
                    bmi = self.users[user_nickname]['bmi']
                    status = self.users[user_nickname]['status']
                    return f"✅ 体重更新成功！\n📊 当前体重: {current_weight}kg\n📈 BMI: {bmi} ({status})"
                else:
                    return "❌ 更新体重失败。"

            elif function_name == "search_my_profile":
                # 查看个人档案
                if not self.check_user_exists():
                    return "您还没有创建健康档案，请先创建档案。"

                user_nickname = self.get_current_user()
                user_data = self.users.get(user_nickname)

                # 调用显示函数并捕获输出
                f = io.StringIO()
                with redirect_stdout(f):
                    search_user_profile(user_data)
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

            elif function_name == "update_meal_status":
                # 调用update_meal_status方法
                if hasattr(self, 'update_meal_status'):

                    # 获取参数
                    user_input = arguments.get("user_input", "")
                    meal_type = arguments.get("meal_type", "auto")
                    print(f"🔍 传入参数：user_input='{user_input}', meal_type='{meal_type}'")

                    # 调用方法
                    print(f"🔍 开始调用 self.update_meal_status()...")
                    result = self.update_meal_status(user_input, meal_type)
                    print(f"🔍 update_meal_status返回结果类型：{type(result)}")
                    print(f"🔍 update_meal_status返回结果内容：{result}")

                    # 格式化返回结果
                    if isinstance(result, dict):
                        # 构建友好回复
                        response = result.get("message", "✅ 用餐状态已更新")
                        if "current_status" in result:
                            status = result["current_status"]
                            response += f"\n\n📊 当前用餐状态："
                            for meal, stat in status.items():
                                response += f"\n  • {meal}: {stat}"
                        if "next_action" in result:
                            response += f"\n\n{result['next_action']}"

                        if result.get("success"):
                            print(f"✅ update_meal_status执行成功！")
                            # 重新加载用户数据检查
                            self.users = load_profiles()
                            user_nickname = self.get_current_user()
                            if user_nickname and self.users.get(user_nickname):
                                user_profile = self.users[user_nickname]
                                print(f"🔍 检查档案更新：早餐状态={user_profile.get('早餐状态', '没吃')}, "
                                      f"午餐状态={user_profile.get('午餐状态', '没吃')}, "
                                      f"晚餐状态={user_profile.get('晚餐状态', '没吃')}")

                        return response
                    else:
                        return str(result)
                else:
                    return "❌ update_meal_status工具不可用"

            elif function_name == "get_daily_plan":
                # 调用get_daily_plan方法
                if hasattr(self, 'get_daily_plan'):
                    # 获取参数
                    view_type = arguments.get("view_type", "current_meal")

                    # 调用方法
                    result = self.get_daily_plan(view_type)

                    # 格式化返回结果
                    if isinstance(result, dict):
                        if result.get("success"):
                            response = result.get("message", "📋 您的计划：")
                            if "plan" in result:
                                plan = result["plan"]
                                if isinstance(plan, list):
                                    for item in plan:
                                        response += f"\n  • {item}"
                                else:
                                    response += f"\n  • {plan}"
                            if "meal_status" in result:
                                status = result["meal_status"]
                                response += f"\n\n🍽️ 用餐状态："
                                for meal, stat in status.items():
                                    response += f"\n  • {meal}: {stat}"
                            return response
                        else:
                            return result.get("message", "❌ 获取计划失败")
                    else:
                        return str(result)
                else:
                    return "❌ get_daily_plan工具不可用"

            else:
                return f"未知的工具函数: {function_name}"

        except Exception as e:
            print(f"❌ 工具执行错误: {e}")
            return f"执行操作时出现错误: {str(e)}"

    def chat(self, user_input: str) -> str:
        """主聊天函数"""
        print(f"\n{'=' * 50}")
        print(f"用户: {user_input}")

        # 添加用户消息
        self.history.append({"role": "user", "content": user_input})

        if user_input == "查看聊天历史":
            print(self.display_history())
            return "这是您的聊天历史..."

        # 使用流式处理，支持多轮工具调用
        max_iterations = 3  # 防止无限循环
        iteration_count = 0

        while iteration_count < max_iterations:
            iteration_count += 1
            print(f"\n🤖 AI思考第{iteration_count}轮...")

            # 调用AI
            response = self.client.chat.completions.create(
                model="qwen-turbo",
                messages=self.history,
                tools=self.tools,
                tool_choice="auto"
            )

            ai_message = response.choices[0].message
            self.history.append(ai_message)

            # 如果没有工具调用，直接返回
            if not ai_message.tool_calls:
                final_reply = ai_message.content
                self.history.append({"role": "assistant", "content": final_reply})
                print(f"AI: {final_reply[:100]}...")
                print(f"{'=' * 50}")
                return final_reply

            # 执行所有工具调用
            print(f"🔧 AI决定调用{len(ai_message.tool_calls)}个工具！")
            all_tool_results = []

            for tool_call in ai_message.tool_calls:
                # 解析参数
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                # 执行工具
                tool_result = self._execute_tool(function_name, arguments)
                print(f"✅ 工具[{function_name}]执行完成")

                # 收集结果
                all_tool_results.append({
                    "tool_call_id": tool_call.id,
                    "function_name": function_name,
                    "result": tool_result
                })

                # 添加工具响应到历史
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

            # 如果是最后一轮，让AI整合结果
            if iteration_count >= max_iterations :
                print("🤖 AI整合所有工具结果生成回复...")
                final_response = self.client.chat.completions.create(
                    model="qwen-turbo",
                    messages=self.history,
                )
                final_reply = final_response.choices[0].message.content
                self.history.append({"role": "assistant", "content": final_reply})
                print(f"AI: {final_reply[:100]}...")
                print(f"{'=' * 50}")
                return final_reply

        # 达到最大轮次，返回默认回复
        return "我已经为您处理了相关数据，还有什么可以帮助您的吗？"

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
            current_time = datetime.datetime.now().strftime("%Y-%m-%d")
            self.history.append({
                "role": "system",
                "content": f"当前用户是：{user_nickname}。今天的时间是：{current_time}，请以专属健康教练的身份为他/她服务。"
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

        self._init_daily_system()

        print("💡 输入'退出'结束对话,'菜单'可以查看服务列表，'清空'可以清空掉所有聊天记录，'查看聊天历史'可以查看你和小助手的所有对话，")
        print("=" * 50)
        try:
            # 获取当前时间
            current_time = datetime.datetime.now()
            current_hour = current_time.hour

            # 判断时间段
            if 5 <= current_hour < 11:
                index=0
                current_meal = "早餐"
                greeting = "早上好！新的一天开始了！ ☀️"
                question = "一定要记得吃营养早餐哦！吃饱了才有力气迎接今天的挑战！"
            elif 11 <= current_hour < 16:
                index = 1
                current_meal = "午餐"
                greeting = "中午好！午间时光~ 🌞"
                question = "不要因为忙碌就忘记吃饭！好好吃饭才能保持下午的精力充沛。"
            elif 16 <= current_hour < 22:
                index = 2
                current_meal = "晚餐"
                greeting = "晚上好！今天一天幸苦啦~ 🌙"
                question = "晚上要吃清淡一些，但营养也不能少哦！好好享受晚餐时光，犒劳一下辛苦一天的自己。"
            else:
                index = 3
                current_meal = "宵夜"
                greeting = "这么晚了怎么还没睡呢？ 🌃"
                question = "要早点休息哦！长期熬夜对身体的影响很大：\n皮肤变差：会让皮肤暗沉、长痘痘\n记忆力下降：大脑得不到充分休息\n心脏负担：增加心血管疾病风险\n容易发胖：代谢会紊乱\n快放下手机，好好休息吧！ 😴\n晚安，好梦~明天见！"

            # 从每日档案中获取当前用餐状态
            try:
                # 加载今日档案
                today_data = self.recorder.load_today_record()

                # 获取当前用餐状态
                status_field = f"{current_meal}状态"
                current_meal_status = today_data.get(status_field, "没吃")

                print(f"{greeting}")

                # 根据状态决定是否询问
                if current_meal_status == "吃了":
                    # 如果已经吃了，显示确认信息
                    if index != 3:
                        print(f"✅ 很好！看到你已经吃过{current_meal}了。可以告诉我你吃了什么吗？我将为你进行详细的营养分析哦！")
                    else:
                        print(f"{question}")

                else:
                    # 如果还没吃，询问用户
                    print(f"{question}")

                    # 显示今日计划
                    if "daily_plan" in today_data:
                        food_plan = today_data["daily_plan"].get("food", [])
                        print(f"\n📋 今日{current_meal}计划：{food_plan[index]}")


            except Exception as e:
                # 如果读取档案失败，使用默认的询问方式
                print(f"{greeting}")
                print(f"{question}")
                print(f"你吃{current_meal}了吗？")

            while True:
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
                elif user_input == "清空":
                    self.clear_history()
                    print("🗑️ 对话历史已清空")
                    continue

                # 调用AI聊天
                response = self.chat(user_input)
                print(f"\n助手：{response}")

        except KeyboardInterrupt:
            print("\n\n👋 下次见，记得坚持健康生活哦！")
            return
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
        """显示所有聊天历史记录"""
        if not self.history:
            print("暂无聊天历史记录")
            return

        print("\n" + "=" * 60)
        print("📜 聊天历史记录")
        print("=" * 60)

        for i, message in enumerate(self.history):
            try:
                # 跳过系统消息
                if isinstance(message, dict):
                    role = message.get("role", "")
                    if role == "system":
                        continue

                    if role == "user":
                        content = message.get("content", "")
                        print(f"\n👤 您: {content}")
                    elif role == "assistant":
                        content = message.get("content", "")
                        if not content and "tool_calls" in message:
                            print(f"\n🤖 助手: [调用了工具]")
                        elif content:
                            if len(content) > 200:
                                content = content[:200] + "..."
                            print(f"\n🤖 助手: {content}")
                    elif role == "tool":
                        content = message.get("content", "")
                        if len(content) > 100:
                            content = content[:100] + "..."
                        print(f"\n🔧 工具结果: {content}")

                # 处理OpenAI对象格式
                elif hasattr(message, 'role'):
                    if message.role == "system":
                        continue

                    if message.role == "user":
                        content = getattr(message, 'content', '')
                        print(f"\n👤 您: {content}")
                    elif message.role == "assistant":
                        content = getattr(message, 'content', '')
                        if not content and hasattr(message, 'tool_calls') and message.tool_calls:
                            print(f"\n🤖 助手: [调用了工具]")
                        elif content:
                            if len(content) > 200:
                                content = content[:200] + "..."
                            print(f"\n🤖 助手: {content}")
                    elif message.role == "tool":
                        content = getattr(message, 'content', '')
                        if len(content) > 100:
                            content = content[:100] + "..."
                        print(f"\n🔧 工具结果: {content}")

            except Exception as e:
                print(f"\n⚠️  消息{i}显示异常: {e}")
                print(f"消息内容: {message}")

        print("=" * 60 + "\n")

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

                    **重要指令：**
                    1. **多工具调用策略**：当用户的问题需要多个数据时，你应该一次性调用多个工具。例如：
                       - 用户问"我的健康状况怎么样？" → 同时调用 `search_my_profile` 和 `calculate_bmi`
                       - 用户提供新体重"今天体重65kg" → 调用 `update_user_weight`，然后自动调用 `calculate_bmi`

                    2. **工具调用顺序**：
                       a. 首先检查是否需要用户数据 → 调用 `search_my_profile`
                       b. 然后检查是否需要计算 → 调用 `calculate_bmi`
                       c. 最后生成个性化建议

                    3. **执行流程**：
                       - 获取用户问题
                       - 分析需要哪些数据
                       - 一次性调用所有必要的工具
                       - 整合所有工具结果
                       - 生成最终回复

                    4. **工具依赖关系**：
                       - `search_my_profile` 通常是第一步
                       - `calculate_bmi` 通常需要身高体重数据
                       - `update_user_weight` 后通常需要重新计算BMI

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
            qwen_api_key = "sk-346cd33207e54d4298fc8c5e64210eca"
            bot = HealthAssistantBot(qwen_api_key)
            bot.interactive_chat()
            return

    # 交互式选择模式
    print("🏥 一对一健康减肥助手")
    print("=" * 50)
    qwen_api_key = "sk-346cd33207e54d4298fc8c5e64210eca"
    bot = HealthAssistantBot(qwen_api_key)
    bot.interactive_chat()


if __name__ == "__main__":
    main()
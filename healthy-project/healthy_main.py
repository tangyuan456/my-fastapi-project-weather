import datetime
from idlelib import history
import os
import httpx
import ssl
from openai import OpenAI
import json
import urllib3
import io
from contextlib import redirect_stdout
from user_manager_sqlite import UserManagerSQLite
from database_bridge import db_bridge
import logging

from websocket import continuous_frame

from First_Entry import (load_profiles, save_profiles, create_user_profile, delete_user_profile,
                         search_user_profile, update_user_weight, calculate_bmi, USER_PROFILES)
from Daily_Recorder import DailyHealthRecorder

from Diet import (update_meal_status, get_daily_plan, DietFunctions)

from History_Summary import HistorySummaryManager

from Exercise import ExerciseFunctions

from Negative_Factor import NegativeFactorManager

from ending import WeightLossJourneyAnalyzer

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置开关
USE_DATABASE = True  # 设置为True使用数据库，False使用JSON

# 编码环境显示日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
# 生产环境关闭日志
#logging.getLogger("httpx").setLevel(logging.WARNING)

class HealthAssistantBot:
    """健康减肥助手机器人（一对一版本）"""

    def __init__(self, qwen_api_key: str):
        self.qwen_api_key = qwen_api_key
        self.current_user = None  # 当前登录的用户
        # ========== 新增：数据库状态展示 ==========
        print("\n" + "=" * 50)
        print("🗄️  数据库系统状态")
        print("=" * 50)
        if db_bridge.connected:
            user_count = db_bridge.get_user_count()
            print(f"✅ 数据库连接成功")
            print(f"📊 数据库中有 {user_count} 个用户")

            # 可选：显示数据库中的用户
            if user_count > 0:
                print("👥 数据库用户列表:")
                # 这里可以添加显示逻辑
        else:
            print("⚠️  数据库未连接，使用纯JSON系统")
        print("=" * 50 + "\n")
        # ========== 新增结束 ==========
        self.recorder = DailyHealthRecorder()
        self.users = load_profiles()
        self.update_meal_status = update_meal_status.__get__(self, HealthAssistantBot)
        self.get_daily_plan = get_daily_plan.__get__(self, HealthAssistantBot)
        self.save_profiles_func = save_profiles
        self.history_summary = HistorySummaryManager(self.recorder)
        self.exercise_functions = ExerciseFunctions(
            self.recorder,
            self.users.get(self.get_current_user()) if self.get_current_user() else None
        )
        self.negative_factor_manager = NegativeFactorManager(self.recorder)

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

        self.diet_functions = DietFunctions(client=self.client, api_key=qwen_api_key)
        self.journey_analyzer = WeightLossJourneyAnalyzer(self.client)
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
                    "description": "当用户的输入包含现在的体重信息时必须调用！用于更新当前用户的体重信息。调用此工具后会触发重新计算BMI。",
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
                    "description": "【当用户表达出要去吃饭或者进行运动时自动调用，给出进食或者运动计划】获取用户当前时间段对应的饮食和运动计划。工具会根据当前时间自动判断是早餐、午餐还是晚餐时间，并返回相应的计划。也可以查看饮水目标和运动计划。",
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
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_food_calories",
                    "description": "【重要！用户描述吃了什么食物时必须调用】分析用户吃的食物热量和营养成分。当用户报告具体吃了什么时，调用此工具计算热量。如果描述模糊，会自动追问细节。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_input": {
                                "type": "string",
                                "description": "用户描述食物的完整输入文本",
                            },
                            "meal_type": {
                                "type": "string",
                                "description": "用餐类型。如果用户明确说了就传入明确值；如果不确定，传'auto'",
                                "enum": ["早餐", "午餐", "晚餐", "宵夜", "auto"]
                            }
                        },
                        "required": ["user_input"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_exercise_status",
                    "description": "【重要！用户报告运动情况时必须调用】当用户报告进行了运动时，自动识别运动类型并更新运动状态。调用此工具可以记录用户的运动情况。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_input": {
                                "type": "string",
                                "description": "用户描述运动情况的完整输入文本",
                            },
                            "exercise_type": {
                                "type": "string",
                                "description": "运动类型。如果用户明确说了就传入明确值；如果不确定，让AI自行判断并传入'auto'",
                                "enum": ["跑步", "步行", "骑行", "游泳", "跳绳", "瑜伽", "健身", "羽毛球", "篮球",
                                         "足球", "auto"]
                            }
                        },
                        "required": ["user_input"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_exercise_calories",
                    "description": "【重要！用户描述运动后必须调用】分析用户运动的卡路里消耗。当用户报告具体运动情况时，调用此工具计算消耗的热量。如果描述模糊，会自动追问细节。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_input": {
                                "type": "string",
                                "description": "用户描述运动的完整输入文本",
                            },
                            "exercise_type": {
                                "type": "string",
                                "description": "运动类型。如果用户明确说了就传入明确值；如果不确定，传'auto'",
                                "enum": ["跑步", "步行", "骑行", "游泳", "跳绳", "瑜伽", "健身", "羽毛球", "篮球",
                                         "足球", "auto"]
                            },
                            "record_index": {
                                "type": "integer",
                                "description": "要计算的记录索引，0表示最新记录，1表示上一次，以此类推。默认0",
                                "minimum": 0
                            }
                        },
                        "required": ["user_input"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_and_record_negative_factors",
                    "description": "【重要！用户描述不适情况时必须调用】自动检测用户输入中的负面因子（如受伤、生病、情绪问题等），评估严重程度并记录。会判断是否适合继续运动。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_input": {
                                "type": "string",
                                "description": "用户描述不适情况的完整输入文本",
                            }
                        },
                        "required": ["user_input"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "mark_negative_factor_recovered",
                    "description": "【重要！用户报告康复时必须调用】当用户报告负面因子已康复（如'我好了'、'不疼了'）时，调用此工具标记对应的负面因子为已康复状态，停止自动复制。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_input": {
                                "type": "string",
                                "description": "用户报告康复的完整输入文本",
                            },
                            "factor_id": {
                                "type": "integer",
                                "description": "要标记的因子ID（可选，如果不指定，系统会尝试自动选择）",
                            }
                        },
                        "required": ["user_input"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "show_database_info",
                    "description": "【演示功能】显示数据库系统信息和统计，展示数据库集成成果。在答辩或演示时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "执行的动作，固定为'show'",
                                "enum": ["show"]
                            }
                        },
                        "required": ["action"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "record_drink_water",
                    "description": "【喝水记录】当用户说喝了水时调用此工具。可以自动识别用户说的喝水杯数，默认增加一杯。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "count": {
                                "type": "integer",
                                "description": "喝水杯数。如果用户明确说了数量就用用户说的，否则默认1",
                                "minimum": 1,
                                "maximum": 10,
                                "default": 1
                            }
                        },
                        "required": [],
                    },
                },
            }
        ]

        # 修改系统提示
        self.history = [
            {
                "role": "system",
                "content": """#  一对一健康减肥助手AI - 完整操作指南

## 你的身份
你是用户专属的健康教练，负责：
1. **健康档案管理** - 创建、查看、更新、删除
2. **饮食跟踪分析** - 记录用餐、计算热量、分析营养
3. **减肥进度监控** - 跟踪体重、计算BMI、评估进度
4. **个性化建议** - 基于用户数据提供专属方案
5. **日常计划指导** - 饮食计划、运动计划、饮水提醒

## 时间判断规则（北京时间）
- **早餐时间**: 05:00-10:59
- **午餐时间**: 11:00-15:59  
- **晚餐时间**: 16:00-21:59
- **宵夜时间**: 22:00-04:59

## 工具调用规则（按优先级排序）

### 饮食相关场景
**场景1：用户报告用餐**
1. **第一步**：调用 `update_meal_status`
   - 根据当前时间自动传入正确的 meal_type
   - 示例：晚上19点 → meal_type="晚餐"
   
2. **第二步**：调用 `calculate_food_calories`
   - 自动传入用户的完整描述
   - meal_type与上一步保持一致
   - **注意**：如果热量计算返回追问问题，直接显示给用户
   
### 运动相关场景
**场景2：用户报告运动**
1.**第一步**：调用 `update_exercise_status`
2.**第二步**：调用 `calculate_exercise_calories`


### 健康数据场景
**场景3：用户需要健康建议**
1. **第一步**：调用 `search_my_profile`（获取基础数据）
2. **第二步**：如果需要BMI数据 → 调用 `calculate_bmi`
3. **第三步**：整合数据提供建议

**场景4：用户更新体重**
要求：一旦用户输入信息包含体重的改变，立即调用
1. 调用 `update_user_weight`（更新体重）
2. 自动调用 `calculate_bmi`（重新计算BMI）

### 负面因子相关场景
**场景：用户描述不适**
1. **必须调用** `detect_and_record_negative_factors`
   - 当用户提到受伤、生病、情绪低落等情况时
   - 工具会自动评估严重程度并给出运动建议

**场景：用户询问能否运动**
1. 先调用 `detect_and_record_negative_factors`（如果有不适）
2. 然后基于工具返回的建议回答

### 日常计划场景
**场景5：用户询问计划或用户表示即将去吃饭/喝水/运动**
1. 调用 `get_daily_plan`
2. view_type选择规则：
   - 问"现在该吃什么" → "current_meal"
   - 问"下一餐" → "next_meal"
   - 问"全天计划" → "all"
   - 问"喝水" → "drink"
   - 问"运动" → "exercise"

示例：用户输入：我接下来要去运动
1. 调用 `get_daily_plan`
2. view_type选择"exercise"
3.告诉用户今日运动计划

**场景：用户报告喝水**
- 调用 `record_drink_water`
- count参数规则：
  - 用户说"喝了水"、"喝水了" → count=1（默认）
  - 用户说"喝了两杯水"、"喝了3杯水" → count=2或3
  - 用户说"喝了好多水" → AI自行判断count=2或3

示例：
- "我喝水了" → record_drink_water(count=1)
- "刚才喝了两杯水" → record_drink_water(count=2)
- "下午喝了3杯水" → record_drink_water(count=3)

### 账户管理场景
**场景6：新用户注册**
- 调用 `create_health_profile`

**场景7：用户想重新开始**
- 调用 `delete_my_profile`

## 完整执行流程

### 第1步：分析用户意图
判断属于哪种场景，选择对应的工具调用策略。

### 第2步：批量调用工具
**重要**：一次性调用所有需要的工具，不要分开调用！
- 示例：用户说"我今天吃了200克米饭"
  - 同时调用：`update_meal_status` + `calculate_food_calories`
- 示例：用户说"帮我看看健康状况"
  - 同时调用：`search_my_profile` + `calculate_bmi`

### 第3步：整合工具结果
将所有工具返回的数据整合起来，形成完整信息。

### 第4步：生成个性化回复
**回复要求**：
1. **语气**：温暖、专业、鼓励
2. **内容**：具体、详细、可操作
3. **个性化**：基于用户数据定制
4. **鼓励性**：时刻给予正向反馈
5. **最后询问**：如果这样项服务已经结束，询问用户接下来要干什么

## 🌟 最佳实践示例

### 示例1：晚餐报告
用户："我吃了番茄炒蛋和一碗米饭"
AI行动：
1. 同时调用：
   - `update_meal_status`(user_input="...", meal_type="晚餐")
   - `calculate_food_calories`(user_input="...", meal_type="晚餐")
2. 整合结果：
   - 确认用餐状态
   - 显示热量分析
   - 给出营养建议

### 示例2：体重更新
用户："今天体重65kg"
AI行动：
1. 同时调用：
   - `update_user_weight`(new_weight=65)
   - `calculate_bmi`(weight=65, height=从档案获取)
2. 整合结果：
   - 显示新体重
   - 显示新BMI
   - 分析变化趋势

### 示例3：健康咨询
用户："我该怎么减肥？"
AI行动：
1. 同时调用：
   - `search_my_profile`(action="view")
   - `calculate_bmi`(weight=当前体重, height=身高)
2. 整合结果：
   - 基于BMI给出减肥建议
   - 基于档案定制方案

## 🎨 沟通风格要求

1. **称呼**：使用用户昵称，如"小明"、"亲爱的"
2. **表情**：适当使用表情符号增加亲和力
3. **分段**：重要信息分点说明
4. **鼓励**：每个回复都要有鼓励话语
5. **具体**：建议要具体可行，不说空话

记住：你是用户的专属教练，陪伴他/她完成整个减肥旅程！"""
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
                    # ========== 新增：同步到数据库 ==========
                    if db_bridge.connected:
                        # 提取昵称（假设user_data格式为 {'昵称': 'xxx', ...}）
                        nickname = user_data.get('昵称') or user_data.get('nickname')
                        if nickname:
                            db_bridge.sync_user_creation(nickname, user_data)
                            print(f"✅ 用户数据已同步到数据库: {nickname}")
                    # ========== 新增结束 ==========
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

                success = update_user_weight(user_nickname, new_weight)
                if success:
                    self.users = load_profiles()  # 重新加载数据
                    current_weight = self.users[user_nickname]['current_weight_kg']
                    bmi = self.users[user_nickname]['bmi']
                    status = self.users[user_nickname]['status']
                    # ========== 新增：同步到数据库 ==========
                    if db_bridge.connected:
                        db_bridge.sync_weight_update(user_nickname, new_weight)
                        print(f"✅ 体重更新已同步到数据库")
                    # ========== 新增结束 ==========
                    summary = self.journey_analyzer.check_and_generate_summary(new_weight)
                    if summary:
                        print("\n" + "🎉" * 30)
                        print("🎉 恭喜！检测到你已经达到目标体重！ 🎉")
                        print("🎉" * 30)
                        print("\n你的坚持和努力得到了回报！这是一份为你准备的特别总结：\n")

                        # 保存总结，稍后可以显示
                        self.last_weight_loss_summary = summary

                        # 询问用户是否要查看完整总结
                        print("💡 我已经为你生成了完整的减肥历程总结报告！")
                        print("   输入'查看减肥总结'可以查看详细报告")
                        print("   报告已自动保存到文件，你可以随时查看")
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
                    #print(f"🔍 开始调用 self.update_meal_status()...")
                    result = self.update_meal_status(user_input, meal_type)
                    #print(f"🔍 update_meal_status返回结果类型：{type(result)}")
                    #print(f"🔍 update_meal_status返回结果内容：{result}")

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
                                print(f"🔍 检查档案更新：早餐状态={user_profile.get('早餐状态', ('没吃', ''))[0]}, "
                                      f"午餐状态={user_profile.get('午餐状态', ('没吃', ''))[0]}, "
                                      f"晚餐状态={user_profile.get('晚餐状态', ('没吃', ''))[0]}")

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
                            if "movement_plan" in result:
                                movement_plan = result["movement_plan"]
                                if isinstance(movement_plan, list):
                                    for item in movement_plan:
                                        response += f"\n  • {item}"
                            elif "plan" in result:
                                plan = result["plan"]
                                if isinstance(plan, list):
                                    for item in plan:
                                        response += f"\n  • {item}"
                                else:
                                    response += f"\n  • {plan}"

                            elif "food_plan" in result:
                                food_plan = result["food_plan"]
                                if isinstance(food_plan, list):
                                    response += "\n🍽️ **饮食计划**:"
                                    for item in food_plan:
                                        response += f"\n  • {item}"

                                if "movement_plan" in result:
                                    movement_plan = result["movement_plan"]
                                    if isinstance(movement_plan, list):
                                        response += "\n\n🏃 **运动计划**:"
                                        for item in movement_plan:
                                            response += f"\n  • {item}"

                            if "meal_status" in result:
                                status = result["meal_status"]
                                response += f"\n\n🍽️ 用餐状态："
                                for meal, stat in status.items():
                                    response += f"\n  • {meal}: {stat}"
                            #print(f"今日计划：{response}")
                            return response
                        else:
                            return result.get("message", "❌ 获取计划失败")
                    else:
                        return str(result)
                else:
                    return "❌ get_daily_plan工具不可用"


            elif function_name == "calculate_food_calories":
                # 获取参数
                user_input = arguments.get("user_input", "")
                meal_type = arguments.get("meal_type", "auto")
                print(f"🔍 开始热量分析：'{user_input}' (用餐类型: {meal_type})")

                try:
                    # 获取最近的对话历史
                    recent_history = self.recorder.get_daily_history(10)

                    # 查找之前是否问过热量问题
                    previous_food_input = None
                    for i in range(len(recent_history) - 1, 0, -1):
                        if recent_history[i].get("role") == "assistant" and "热量" in recent_history[i].get("content",""):

                            # 往前找用户的回复
                            for j in range(i - 1, -1, -1):
                                if recent_history[j].get("role") == "user":
                                    previous_food_input = recent_history[j].get("content")
                                    break
                            break
                    print(f"🔍 找到之前的输入：{previous_food_input}")

                    # 判断当前输入是否是补充信息
                    is_followup = previous_food_input and any(
                        word in user_input for word in ["包含", "大概", "大约", "左右", "酱料", "克", "g"])
                    if is_followup:

                        # 结合两次输入
                        combined_input = f"{previous_food_input}。补充：{user_input}"
                        print(f"🔍 合并输入：{combined_input}")
                    else:
                        combined_input = user_input

                    # 使用饮食功能类分析热量
                    result = self.diet_functions.get_calorie_analysis(combined_input)

                    # 检查是否有错误
                    if "error" in result:
                        return f"❌ 热量分析失败: {result['error']}\n请重新描述食物。"

                    # 处理需要追问的情况
                    if result.get("needs_clarification", False) and not is_followup:
                        response = result.get("message", "需要更多信息来准确计算热量：")
                        questions = result.get("questions", [])
                        for i, question in enumerate(questions, 1):
                            response += f"\n{i}. {question}"
                        response += f"\n\n{result.get('suggestion', '请回答上述问题，我会为您重新分析。')}"
                        return response

                    # 处理成功的情况
                    elif result.get("success", False):
                        # 构建详细回复
                        response = f"""🍎 **食物热量分析完成！**
                            {result.get('explanation', '')}

                            📝 **详细成分**："""
                        for detail in result.get("details", []):
                            response += f"\n• {detail['name']}：{detail['calories']}大卡"
                            if detail.get('protein_g'):
                                response += f" (蛋白质{detail['protein_g']}g)"

                        # 添加综合建议
                        total_cal = result.get('total_calories', 0)
                        protein_g = result.get('protein_g', 0)

                        # 根据总热量给出建议
                        if total_cal > 0:
                            daily_percent = round(total_cal / 2000 * 100)
                            protein_suggestion = "充足" if protein_g > 20 else "稍低，建议补充"
                            response += f"""
                                💡 **综合建议**：
                                • 这餐热量占每日推荐摄入的约{daily_percent}%（按2000大卡计算）
                                • 蛋白质摄入{protein_suggestion} 
                                • 记得保持均衡饮食，搭配适量运动！"""

                        # 自动检测并保存食物详情
                        # 1. 首先确定是哪个餐次（从上下文或自动判断）
                        detected_meal = meal_type

                        # 如果meal_type是auto，尝试从user_input判断
                        if meal_type == "auto":
                            # 简单判断逻辑
                            if any(word in user_input for word in ["早餐", "早饭", "早点"]):
                                detected_meal = "早餐"
                            elif any(word in user_input for word in ["午餐", "午饭", "中午"]):
                                detected_meal = "午餐"
                            elif any(word in user_input for word in ["晚餐", "晚饭", "晚上"]):
                                detected_meal = "晚餐"
                            else:
                                # 根据时间判断
                                current_hour = datetime.datetime.now().hour
                                if 5 <= current_hour < 11:
                                    detected_meal = "早餐"
                                elif 11 <= current_hour < 16:
                                    detected_meal = "午餐"
                                elif 16 <= current_hour < 22:
                                    detected_meal = "晚餐"
                                else:
                                    detected_meal = "宵夜"

                        # 2. 准备食物信息
                        food_info = {
                            "description": user_input,
                            "total_calories": total_cal,
                            "protein_g": protein_g,
                            "carbs_g": result.get('carbs_g', 0),
                            "fat_g": result.get('fat_g', 0),
                            "details": result.get('details', [])
                        }

                        # 3. 更新餐次状态并保存食物详情
                        if detected_meal in ["早餐", "午餐", "晚餐", "宵夜"]:
                            try:
                                # 使用update_meal_status来更新状态并保存食物信息
                                update_result = self.update_meal_status(
                                    user_input=user_input,
                                    meal_type=detected_meal,
                                    food_info=food_info
                                )

                                if update_result.get("success", False):
                                    print(f"✅ 已保存{detected_meal}的食物详情")
                                else:
                                    print(f"⚠️ 保存食物详情失败：{update_result.get('message', '未知错误')}")
                            except Exception as e:
                                print(f"⚠️ 调用update_meal_status失败: {e}")

                        return response
                    # 处理失败情况
                    else:
                        return result.get("message", "❌ 热量分析失败，请重新描述食物。")
                except Exception as e:
                    print(f"❌ 热量计算异常: {e}")
                    return f"❌ 热量分析时出现错误: {str(e)}\n请重新描述食物。"

            elif function_name == "update_exercise_status":
                # 更新运动状态
                user_input = arguments.get("user_input", "")
                exercise_type = arguments.get("exercise_type", "auto")

                result = self.exercise_functions.update_exercise_status(user_input, exercise_type)

                # 格式化返回结果
                if isinstance(result, dict):
                    if result.get("success"):
                        response = result.get("message", "✅ 运动状态已更新")

                        # 如果需要计算卡路里，提示下一步
                        if result.get("needs_calorie_calculation"):
                            response += f"\n\n🔢 检测到您进行了{result.get('exercise_type', '运动')}，正在为您计算消耗的卡路里..."

                        return response
                    else:
                        # 处理追问情况
                        if result.get("needs_clarification"):
                            response = result.get("message", "需要更多信息来记录运动：")
                            questions = result.get("questions", [])
                            for i, question in enumerate(questions, 1):
                                response += f"\n{i}. {question}"
                            response += f"\n\n{result.get('suggestion', '请回答上述问题，我会为您记录这次运动。')}"
                            return response
                        else:
                            return result.get("message", "❌ 更新运动状态失败")
                else:
                    return str(result)

            elif function_name == "calculate_exercise_calories":
                # 计算运动卡路里
                user_input = arguments.get("user_input", "")
                exercise_type = arguments.get("exercise_type", "auto")
                record_index = arguments.get("record_index", 0)

                result = self.exercise_functions.calculate_exercise_calories(
                    user_input, exercise_type, record_index
                )

                # 格式化返回结果
                if isinstance(result, dict):
                    if result.get("success"):
                        total_cal = result.get("total_calories", 0)
                        exercise_type = result.get("exercise_type", "运动")
                        explanation = result.get("explanation", "")

                        response = f"""🔥 **运动卡路里计算完成！**

            🏃 **运动类型**：{exercise_type}
            💪 **消耗热量**：**{total_cal}大卡**
            📊 **计算方法**：{result.get('calculation_method', '估算')}
            📈 **计算依据**：{explanation}"""

                        # 添加今日总计
                        today_total = result.get("today_total", 0)
                        if today_total > 0:
                            response += f"\n\n📅 **今日运动总计**：{today_total}大卡"
                        return response
                    else:
                        # 处理追问情况
                        if result.get("needs_clarification"):
                            response = result.get("message", "需要更多信息来计算卡路里：")
                            questions = result.get("questions", [])
                            for i, question in enumerate(questions, 1):
                                response += f"\n{i}. {question}"
                            response += f"\n\n{result.get('suggestion', '请回答上述问题，我会为您计算卡路里。')}"
                            return response
                        else:
                            return result.get("message", "❌ 计算卡路里失败")
                else:
                    return str(result)

            elif function_name == "detect_and_record_negative_factors":
                # 检测并记录负面因子
                user_input = arguments.get("user_input", "")

                result = self.negative_factor_manager.analyze_and_record(user_input)

                if result.get("success"):
                    if result.get("has_negative_factor"):
                        response = f"{result.get('message', '检测到负面因子')}"
                        if "suggestion" in result:
                            response += f"\n\n{result['suggestion']}"

                        # 如果是新的因子，添加特别提醒
                        if result.get("is_new", False):
                            factor_info = result.get("factor_info", {})
                            severity = factor_info.get("severity", "轻")
                            if severity == "重":
                                response += f"\n\n⚠️ **重要提醒**：检测到重度{result.get('type', '问题')}，请务必注意休息，如有需要请及时就医！"

                        return response
                    else:
                        return result.get("message", "未检测到负面因子，保持良好的状态！")
                else:
                    return result.get("message", "负面因子分析失败")

            elif function_name == "mark_negative_factor_recovered":
                # 标记负面因子为已康复
                user_input = arguments.get("user_input", "")
                factor_id = arguments.get("factor_id")

                result = self.negative_factor_manager.mark_as_recovered(user_input, factor_id)

                if result.get("success"):
                    response = f"{result.get('message', '标记成功')}"
                    if "summary" in result:
                        response += f"\n\n📊 当前状态：\n{result['summary']}"
                    if "suggestion" in result:
                        response += f"\n\n{result['suggestion']}"
                    return response
                elif result.get("needs_clarification"):
                    # 需要用户澄清选择哪个因子
                    response = result.get("message", "需要更多信息：")
                    questions = result.get("questions", [])
                    for question in questions:
                        response += f"\n{question}"
                    response += f"\n\n{result.get('suggestion', '请回复对应编号')}"
                    return response
                else:
                    return result.get("message", "标记康复失败")

            elif function_name == "show_database_info":
                """演示数据库功能（新增工具，可选）"""
                if not db_bridge.connected:
                    return "❌ 数据库未连接"

                try:
                    # 获取数据库信息
                    user_count = db_bridge.get_user_count()

                    # 获取表信息
                    db_bridge.db.cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' 
                        ORDER BY name
                    """)
                    tables = db_bridge.db.cursor.fetchall()

                    response = f"""🗄️ **数据库系统信息**

            📊 **基础信息**
            • 数据库状态: ✅ 已连接
            • 用户数量: {user_count} 个
            • 数据库文件: health_assistant.db

            📋 **数据表结构**
            """
                    for table in tables:
                        response += f"• {table['name']}\n"

                    response += f"""
            💡 **技术特点**
            • 使用SQLite轻量级数据库
            • 与JSON系统双向同步
            • 支持快速查询和统计
            • 为未来扩展奠定基础

            🎯 **答辩展示**
            此项功能展示了我在7天内学习并集成的数据库技术！"""

                    return response

                except Exception as e:
                    return f"❌ 获取数据库信息失败: {e}"

            elif function_name == "record_drink_water":
                # 记录喝水 - 支持多杯
                try:
                    count = arguments.get("count", 1)

                    if count < 1:
                        return "❌ 请输入有效的喝水杯数"

                    success = self.recorder.add_drink(count)

                    if success:
                        # 获取更新后的数据
                        data = self.recorder.load_today_record()
                        current = data.get("drink_number", 0)
                        target = data.get("drink_plan", 8)

                        # 根据杯数使用不同的表达
                        if count == 1:
                            drink_text = "一杯水"
                        else:
                            drink_text = f"{count}杯水"

                        return f"""✅ 已记录喝了{drink_text}！

            💧 今日喝水进度：{current}/{target}杯

            💡 {'继续补充水分哦！' if current < target else '太棒了！已完成今日目标！🎉'}"""
                    else:
                        return "❌ 记录喝水失败"

                except Exception as e:
                    return f"❌ 记录喝水时出错: {str(e)}"

            else:
                return f"未知的工具函数: {function_name}"

        except Exception as e:
            print(f"❌ 工具执行错误: {e}")
            return f"执行操作时出现错误: {str(e)}"

    def _format_archive_response(self, archive_info: dict, view_type: str) -> str:
        """格式化档案信息的响应"""
        try:
            date = archive_info.get("date", "未知日期")

            if view_type == "summary":
                # 摘要信息格式化
                meal_status = archive_info.get("meal_status", {})
                exercise_status = archive_info.get("exercise_status", "未知")
                drink_progress = archive_info.get("drink_progress", "0/8杯")
                health_summary = archive_info.get("health_factors", "🎉 健康状况良好")

                # 构建自然语言的摘要
                meal_summary = []
                for meal, status in meal_status.items():
                    if status != "没吃":
                        meal_summary.append(f"{meal}: {status}")

                meal_text = "、".join(meal_summary) if meal_summary else "今日还未进食"

                response = f"""📊 **今日健康档案摘要** ({date})

🍽️ **餐次状态**: {meal_text}
🏃 **运动状态**: {exercise_status}
💧 **饮水进度**: {drink_progress}

🩺 **健康状态**:
{health_summary}"""

                # 如果有今日总结，也加上
                if "summary" in archive_info and archive_info["summary"]:
                    response += f"\n\n📝 **今日总结**: {archive_info['summary']}"

                return response

            elif view_type == "meals":
                # 餐次详细信息
                meals = archive_info.get("meals", {})

                response = f"🍽️ **今日餐次详情** ({date})\n\n"

                for meal, info in meals.items():
                    status = info.get("status", "没吃")
                    food_info = info.get("food_info", {})

                    response += f"**{meal}**: {status}\n"

                    if status != "没吃":
                        if isinstance(food_info, dict):
                            if "description" in food_info:
                                desc = food_info.get("description", "")
                                response += f"   食物: {desc[:50]}\n"
                            if "total_calories" in food_info and food_info["total_calories"] > 0:
                                response += f"   热量: {food_info.get('total_calories', 0)}大卡\n"
                            if "record_count" in food_info:
                                response += f"   进食次数: {food_info['record_count']}次\n"

                return response

            elif view_type == "plan":
                # 计划信息
                food_plan = archive_info.get("food_plan", [])
                movement_plan = archive_info.get("movement_plan", [])

                response = f"📋 **今日健康计划** ({date})\n\n"

                if food_plan:
                    response += "🍽️ **饮食计划**:\n"
                    for i, plan in enumerate(food_plan, 1):
                        response += f"{i}. {plan}\n"
                    response += "\n"

                if movement_plan:
                    response += "🏃 **运动计划**:\n"
                    for i, plan in enumerate(movement_plan, 1):
                        response += f"{i}. {plan}\n"

                return response

            elif view_type == "health":
                # 健康信息
                health = archive_info.get("health", {})
                factor_summary = health.get("factor_summary", "暂无信息")
                exercise_check = health.get("exercise_check", {})

                response = f"🩺 **今日健康状况** ({date})\n\n"
                response += "⚠️ **健康问题**:\n"
                response += factor_summary + "\n"

                if exercise_check:
                    can_exercise = exercise_check.get("can_exercise", True)
                    suggestion = exercise_check.get("suggestion", "")

                    response += f"\n🏃 **运动建议**: "
                    response += "✅ 可以运动" if can_exercise else "❌ 建议休息"
                    if suggestion:
                        response += f"（{suggestion}）"

                return response

            else:
                return f"📁 获取了 {view_type} 类型的档案信息"

        except Exception as e:
            return f"❌ 格式化档案信息失败: {str(e)}"

    def chat(self, user_input: str) -> str:
        """主聊天函数"""
        print(f"\n{'=' * 50}")
        print(f"用户: {user_input}")

        # 1. 保存用户对话到每日记录
        self.recorder.add_daily_history("user", user_input)

        # 2. 添加到主历史记录
        self.history.append({"role": "user", "content": user_input})

        if user_input == "查看聊天历史":
            print(self.display_history())
            return "这是您的聊天历史..."

        # 使用流式处理，支持多轮工具调用
        max_iterations = 3
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

                # 保存助手回复到每日记录
                self.recorder.add_daily_history("assistant", final_reply)

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
            if iteration_count >= max_iterations:
                print("🤖 AI整合所有工具结果生成回复...")
                final_response = self.client.chat.completions.create(
                    model="qwen-turbo",
                    messages=self.history,
                )
                final_reply = final_response.choices[0].message.content

                # 保存助手回复到每日记录
                self.recorder.add_daily_history("assistant", final_reply)

                print(f"AI: {final_reply[:100]}...")
                print(f"{'=' * 50}")
                return final_reply

        # 达到最大轮次
        default_reply = "我已经为您处理了相关数据，还有什么可以帮助您的吗？"
        self.recorder.add_daily_history("assistant", default_reply)
        return default_reply

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

        today = datetime.datetime.now().strftime("%Y-%m-%d")

        # 构建文件路径（假设文件在当前目录下）
        daily_records_dir = "daily_records"
        file_path = os.path.join(daily_records_dir, f"{today}.json")

        # 检查文件是否存在并输出
        if not os.path.exists(file_path):
            # 处理最近未总结的记录
            date_str, summary, is_new = self.history_summary.process_latest_unsummarized_record(
                ai_client=self.client,  # 传入AI客户端用于生成智能总结
                max_days_back=30  # 最多回溯30天
            )

            if date_str and summary:
                print("\n" + "=" * 60)
                if is_new:
                    print(f"📊 {date_str} 表现总结（新生成）")
                else:
                    print(f"📊 {date_str} 表现回顾")
                print("=" * 60)
                print(summary)
                print("=" * 60 + "\n")

                # 可选：清理历史记录以节省空间（7天前的记录）
                if date_str != datetime.datetime.now().strftime("%Y-%m-%d"):
                    try:
                        check_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                        days_ago = (datetime.datetime.now() - check_date).days

                        if days_ago >= 7:  # 7天前的记录可以清理
                            print(f"🗑️  清理{date_str}的历史记录以节省空间...")
                            self.history_summary.clear_history_for_date(
                                date_str=date_str,
                                keep_summary=True  # 保留总结，只清理详细对话记录
                            )
                    except Exception as e:
                        print(f"⚠️ 日期处理失败: {e}")
            else:
                print("📭 没有需要总结的历史记录")

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
                current_meal_tuple = today_data.get(status_field, ("没吃", ""))
                current_meal_status = current_meal_tuple[0]

                print(f"{greeting}")
                self.history.append({"role": "assistant", "content": greeting})

                # 根据状态决定是否询问
                if current_meal_status == "吃了":
                    # 如果已经吃了，显示确认信息
                    if index != 3:
                        print(f"✅ 很好！看到你已经吃过{current_meal}了。你接下来要做什么呢？告诉我然后我会一直陪伴着你哦。")
                        self.recorder.add_daily_history("assistant", f"✅ 很好！看到你已经吃过{current_meal}了。你接下来要做什么呢？告诉我然后我会一直陪伴着你哦。")
                    else:
                        print(f"{question}")
                        self.history.append({"role": "assistant", "content": question})

                else:
                    # 如果还没吃，询问用户
                    print(f"{question}")
                    self.history.append({"role": "assistant", "content": question})

                    # 显示今日计划
                    if "daily_plan" in today_data:
                        food_plan = today_data["daily_plan"].get("food", [])
                        print(f"\n📋 今日{current_meal}计划：{food_plan[index]}")
                        plan_text = f"📋 今日{current_meal}计划：{food_plan[index]}"
                        self.history.append({"role": "assistant", "content": plan_text})
                        self.recorder.add_daily_history("assistant", plan_text)  # 新增这一行

            except Exception as e:
                # 如果读取档案失败，使用默认的询问方式
                print(f"{greeting}")
                self.history.append({"role": "assistant", "content": greeting})
                self.recorder.add_daily_history("assistant", greeting)

                print(f"{question}")
                self.history.append({"role": "assistant", "content": question})
                self.recorder.add_daily_history("assistant", question)

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
               
            6. 数据库演示功能：
               • "查看数据库信息" - 展示数据库集成成果

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
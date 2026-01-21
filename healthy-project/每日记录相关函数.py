import os
import json
import datetime
from typing import Dict, Any, List, Optional
import re


class DailyHealthRecorder:
    """每日健康记录管理器"""

    def __init__(self, base_dir: str = "daily_records"):
        """
        初始化记录器

        Args:
            base_dir: 记录文件的存储目录
        """
        self.base_dir = base_dir
        self.ensure_directory()

    def ensure_directory(self):
        """确保存储目录存在"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_today_filename(self) -> str:
        """获取今天的文件名"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.base_dir, f"{today}.json")

    def get_date_filename(self, date_str: str) -> str:
        """获取指定日期的文件名"""
        return os.path.join(self.base_dir, f"{date_str}.json")

    def check_today_record_exists(self) -> bool:
        """检查今天的记录文件是否存在"""
        return os.path.exists(self.get_today_filename())

    def create_today_record(self, initial_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        创建今天的记录文件

        Args:
            initial_data: 初始数据

        Returns:
            文件路径
        """
        filename = self.get_today_filename()

        if initial_data is None:
            initial_data = {
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "created_at": datetime.datetime.now().isoformat(),
                "daily_plan": {
                    "food": [],  # 饮食计划
                    "movement": []  # 运动计划
                },
                "drink_number": 0,  # 当前喝水杯数
                "drink_plan": 8,  # 目标喝水杯数（假设8杯）
                "早餐状态": ("没吃",""),
                "午餐状态": ("没吃",""),
                "晚餐状态": ("没吃",""),
                "宵夜状态": ("没吃",""),
                "运动状态": ("没运动",""),
                "daily_history": [],  # 当日对话历史
                "summary": "",  # 当日总结
                "last_updated": datetime.datetime.now().isoformat()
            }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 创建今日记录文件: {filename}")

        # 然后复制前一天的负面因子
        self.copy_active_factors_from_previous_day()

        # 重新加载文件以包含复制的因子
        return self.load_today_record()

    def load_today_record(self) -> Dict[str, Any]:
        """
        加载今天的记录文件

        Returns:
            记录数据字典
        """
        filename = self.get_today_filename()

        if not os.path.exists(filename):
            return self.create_today_record()

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 更新最后修改时间
            data['last_updated'] = datetime.datetime.now().isoformat()
            return data

        except Exception as e:
            print(f"❌ 加载记录文件失败: {e}")
            return self.create_today_record()

    def load_date_record(self, date_str: str) -> Dict[str, Any]:
        """
        加载指定日期的记录文件

        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD

        Returns:
            记录数据字典，如果文件不存在返回空字典
        """
        filename = self.get_date_filename(date_str)

        if not os.path.exists(filename):
            return {}

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"❌ 加载记录文件失败 {date_str}: {e}")
            return {}

    def save_today_record(self, data: Dict[str, Any]) -> bool:
        """
        保存今天的记录文件

        Args:
            data: 要保存的数据

        Returns:
            是否成功
        """
        try:
            filename = self.get_today_filename()
            data['last_updated'] = datetime.datetime.now().isoformat()

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"❌ 保存记录文件失败: {e}")
            return False

    def update_drink_number(self, drink_number: int, note: str = "") -> bool:
        """更新喝水杯数"""
        try:
            data = self.load_today_record()
            data["drink_number"] = drink_number

            if note:
                # 记录喝水历史
                if "drink_history" not in data:
                    data["drink_history"] = []
                data["drink_history"].append({
                    "drink_number": drink_number,
                    "note": note,
                    "timestamp": datetime.datetime.now().isoformat()
                })

            return self.save_today_record(data)

        except Exception as e:
            print(f"❌ 更新喝水记录失败: {e}")
            return False

    def add_drink(self) -> bool:
        """增加一杯水"""
        try:
            data = self.load_today_record()
            current = data.get("drink_number", 0)
            data["drink_number"] = current + 1

            # 记录喝水时间
            if "drink_times" not in data:
                data["drink_times"] = []
            data["drink_times"].append({
                "time": datetime.datetime.now().isoformat(),
                "count": current + 1
            })

            return self.save_today_record(data)

        except Exception as e:
            print(f"❌ 增加喝水失败: {e}")
            return False

    # 在 DailyHealthRecorder 类中添加这个方法
    def set_daily_plan(self, food_plan: List[str], movement_plan: List[str]) -> bool:
        """
        设置今日计划

        Args:
            food_plan: 饮食计划列表
            movement_plan: 运动计划列表

        Returns:
            是否成功
        """
        try:
            data = self.load_today_record()

            data["daily_plan"] = {
                "food": food_plan,
                "movement": movement_plan,
                "created_at": datetime.datetime.now().isoformat()
            }

            return self.save_today_record(data)
        except Exception as e:
            print(f"❌ 设置今日计划失败: {e}")
            return False

    def get_three_day_summary(self) -> str:
        """
        获取前三天的摘要

        Returns:
            三天摘要的合并文本
        """
        try:
            three_days_data = []

            for i in range(1, 4):  # 前1-3天
                date = datetime.datetime.now() - datetime.timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                record = self.load_date_record(date_str)

                if record:
                    # 提取关键信息
                    day_info = {
                        "date": date_str,
                        "summary": record.get("summary", ""),
                        "daily_plan": record.get("daily_plan", {}),
                        "drink_completed": record.get("drink_number", 0),
                        "drink_plan": record.get("drink_plan", 8)
                    }
                    three_days_data.append(day_info)

            if not three_days_data:
                return "暂无前三天的历史记录。"

            # 构建摘要文本
            summary_lines = ["前三日健康记录摘要："]

            for day in three_days_data:
                summary_lines.append(f"\n📅 {day['date']}:")

                if day['summary']:
                    summary_lines.append(f"   总结: {day['summary'][:100]}")

                daily_plan = day.get('daily_plan', {})
                food_plan = daily_plan.get('food', [])
                movement_plan = daily_plan.get('movement', [])

                if food_plan:
                    summary_lines.append(f"   饮食计划: {', '.join(food_plan[:3])}")
                if movement_plan:
                    summary_lines.append(f"   运动计划: {', '.join(movement_plan[:3])}")

                drink_status = f"喝水: {day['drink_completed']}/{day['drink_plan']}杯"
                summary_lines.append(f"   {drink_status}")

            return "\n".join(summary_lines)

        except Exception as e:
            print(f"❌ 获取三天摘要失败: {e}")
            return "获取历史记录时出错。"

    def get_historical_records(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取历史记录

        Args:
            days: 获取最近多少天的记录

        Returns:
            历史记录列表
        """
        records = []

        for i in range(days):
            date = datetime.datetime.now() - datetime.timedelta(days=i)
            filename = os.path.join(self.base_dir, f"{date.strftime('%Y-%m-%d')}.json")

            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    records.append(data)
                except:
                    continue

        return records

    def get_today_summary(self) -> str:
        """获取今日总结"""
        data = self.load_today_record()
        return data.get("summary", "")

    def update_summary(self, summary: str) -> bool:
        """更新今日总结"""
        try:
            data = self.load_today_record()
            data["summary"] = summary
            return self.save_today_record(data)
        except Exception as e:
            print(f"❌ 更新总结失败: {e}")
            return False

    def get_important_notes_summary(self, days: int = 3) -> str:
        """
        获取近期重要笔记

        Args:
            days: 最近多少天的笔记

        Returns:
            摘要字符串
        """
        records = self.get_historical_records(days)

        if not records:
            return "暂无重要记录"

        summary_lines = []

        for record in records:
            date = record.get("date", "未知日期")
            important_notes = record.get("important_notes", [])

            if important_notes:
                summary_lines.append(f"【{date}】")

                for note in important_notes[:5]:  # 每天最多显示5条重要笔记
                    note_type = note.get("type", "笔记")
                    content = note.get("content", "")
                    importance = "★" * note.get("importance", 3)

                    summary_lines.append(f"  {importance} {note_type}: {content}")

                summary_lines.append("")

        return "\n".join(summary_lines) if summary_lines else "暂无重要记录"

    def print_today_plan(self):
        """打印今日计划"""
        try:
            data = self.load_today_record()
            daily_plan = data.get("daily_plan", {})

            if not daily_plan.get("food") and not daily_plan.get("movement"):
                print("📋 今日暂无计划")
                return

            print("\n" + "=" * 50)
            print("📋 今日健康计划")
            print("=" * 50)

            if daily_plan.get("food"):
                print("\n🍽️ 饮食计划：")
                for i, item in enumerate(daily_plan["food"], 1):
                    print(f"  {i}. {item}")

            if daily_plan.get("movement"):
                print("\n🏃 运动计划：")
                for i, item in enumerate(daily_plan["movement"], 1):
                    print(f"  {i}. {item}")

            drink_plan = data.get("drink_plan", 8)
            print(f"\n💧 喝水目标：{drink_plan}杯（当前：{data.get('drink_number', 0)}杯）")
            print("=" * 50)

        except Exception as e:
            print(f"❌ 打印计划失败: {e}")

    def create_today_plan_with_ai(self, three_day_summary: str, openai_client, user_profile: Dict[str, Any] = None) -> \
    Dict[str, List[str]]:
        """
        使用大模型基于前三天摘要生成今日详细计划

        Args:
            three_day_summary: 前三天的摘要
            openai_client: OpenAI客户端实例
            user_profile: 用户档案数据（可选）

        Returns:
            今日计划字典，包含food和movement
        """
        try:
            # 构建用户档案信息
            user_info = ""
            if user_profile:
                user_info = f"""
    用户信息：
    - 昵称：{user_profile.get('nickname', '用户')}
    - 身高：{user_profile.get('height_cm', '')}cm
    - 当前体重：{user_profile.get('current_weight_kg', '')}kg
    - BMI：{user_profile.get('bmi', '')}
    - 减肥目标：{user_profile.get('goal', '')}
    - 饮食偏好：{user_profile.get('diet_preferences', '')}
    - 过敏原：{user_profile.get('allergens', '')}
    - 运动偏好：{user_profile.get('move_prefer', '')}
    """

            # 获取当前负面因子信息
            #negative_factors_summary = self.get_factor_impact_summary()
            active_factors = self.get_active_negative_factors()

            # 构建负面因子详细描述
            negative_factors_info = ""
            if active_factors:
                negative_factors_info = "当前健康问题（负面因子）- 已考虑恢复进度：\n"
                for factor in active_factors:
                    factor_type = factor.get('type', '未知')
                    description = factor.get('description', '')
                    severity = factor.get('severity', '轻')
                    original_severity = factor.get('original_severity', severity)
                    duration = factor.get('duration_days', 1)
                    should_exercise = factor.get('should_exercise', True)
                    recovery_progress = factor.get('recovery_progress', 0)
                    estimated_days = factor.get('estimated_recovery_days', 0)

                    # 添加恢复状态信息
                    status = factor.get('status', 'active')
                    status_text = ""
                    if status == "recovering":
                        status_text = "（正在恢复中，建议确认是否已康复）"
                    elif status == "recovered":
                        status_text = "（已康复）"

                    # 如果严重程度自动减轻了，特别说明
                    reduction_info = ""
                    if factor.get('auto_reduced', False):
                        reduction_info = f"【已从{original_severity}自动减轻为{severity}】"

                    exercise_advice = "可以适当运动" if should_exercise else "建议休息"

                    negative_factors_info += f"- {factor_type}：{description}{status_text}\n"
                    negative_factors_info += f"  • 当前严重程度：{severity}{reduction_info}\n"
                    negative_factors_info += f"  • 已持续：{duration}天（恢复进度：{recovery_progress}%）\n"
                    if estimated_days > 0:
                        negative_factors_info += f"  • 预计还需：约{estimated_days}天恢复\n"
                    negative_factors_info += f"  • 运动建议：{exercise_advice}\n"
            else:
                negative_factors_info = "当前健康问题：无负面因子，健康状况良好。\n"

            # 获取运动能力判断
            exercise_check = self.can_user_exercise_today()

            # 构建运动限制说明
            exercise_restrictions = ""
            if not exercise_check.get('can_exercise', True):
                exercise_restrictions = f"""
            ⚠️ 重要运动限制：
            - 原因：{exercise_check.get('reason', '存在健康问题')}
            - 建议：{exercise_check.get('suggestion', '建议休息')}
            - 当前不适合进行剧烈运动，请制定适合当前身体状况的运动计划。
            """
            else:
                exercise_restrictions = "✅ 当前身体状况适合运动，可以制定正常运动计划。\n"

            # 构建大模型提示词
            prompt = f"""你是一个专业的健康营养师和健身教练。请根据以下信息为用户制定今日的健康计划。

    {user_info}

    前三天健康记录摘要：
    {three_day_summary}
    
    {negative_factors_info}

    {exercise_restrictions}

    请制定一个详细、可执行的今日健康计划，特别要考虑用户的当前健康问题：

    1. 饮食计划（food）[必须考虑用户的健康问题][不能和前三天一摸一样，要变换花样，且要丰盛]：
       - 早餐（具体食物、分量）[如果有生病，考虑易消化食物]
       - 午餐（具体食物、分量）[如果有受伤，考虑促进恢复的食物]
       - 晚餐（具体食物、分量）[如果有情绪问题，考虑提升情绪的食物]
       - 加餐建议
       - 饮水提醒

    2.运动计划（movement）[必须严格考虑恢复进度和运动限制]：
       - 运动类型（根据健康问题的恢复进度调整，考虑自动减轻后的严重程度）
       - 运动时长（根据恢复进度和体能调整）
       - 运动强度（根据当前严重程度和持续时间调整）
       - 注意事项（特别提醒：考虑问题已持续的时间，可能需要渐进恢复）
       - 鼓励话语（根据恢复进度给予适当鼓励，如"已经恢复XX%了，继续加油"）
       - 鼓励话语，要温暖，让用户有动力

    请用JSON格式回复，严格遵循以下结构：
    {{
      "food": [
        "早餐：具体的早餐建议",
        "午餐：具体的午餐建议", 
        "晚餐：具体的晚餐建议",
        "加餐建议",
        "饮水提醒"
      ],
      "movement": [
        "运动类型和时长",
        "运动强度说明",
        "对应运动教程（如果有受伤要避免某些动作）",
        "注意事项（必须包含健康问题相关的注意事项）",
        "鼓励"
      ]
    }}

    基本要求：
    1. 基于前三天的记录进行个性化调整，
    2. 计划要具体、可执行、且强度要适中
    3. 考虑营养均衡、运动安全和用户偏好
    4. 要给出该运动的对应文字教程，以便用户更好的学习，教程包括该运动的正确姿势教学、该运动技巧教学等
    6. 语气温和且专业，尽量说的详细一点，防止用户听不懂
    7. 用中文回复
    
    特殊要求：
    1. 如果有负面因子，计划必须适应这些健康问题
    2. 如果有受伤：避免使用受伤部位，建议替代运动
    3. 如果有生病：建议易消化、营养丰富的食物
    4. 如果有情绪问题：建议温和运动，如散步、瑜伽
    5. 运动计划必须安全第一，不能加重现有问题"""

            # 调用大模型
            response = openai_client.chat.completions.create(
                model="qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是专业的健康管理专家，擅长制定个性化的饮食和运动计划。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            result_text = response.choices[0].message.content.strip()

            # 提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)

            if json_match:
                try:
                    today_plan = json.loads(json_match.group())

                    # 验证数据结构
                    if "food" in today_plan and "movement" in today_plan:
                        print("✅ AI已生成详细健康计划")
                        self._validate_plan_against_factors(today_plan, active_factors)
                        return today_plan
                    else:
                        print("⚠️ AI返回的计划格式不完整，使用默认计划")

                except json.JSONDecodeError:
                    print("❌ AI返回的JSON格式错误，使用默认计划")

            # 如果AI生成失败，返回默认计划
            return self._get_default_plan_with_factors(user_profile, active_factors)
        except Exception as e:
            print(f"❌ 使用AI生成计划失败: {e}")
            # 返回默认计划
            return self._get_default_plan_with_factors(user_profile, self.get_active_negative_factors())

    def _get_default_plan(self, user_profile: Dict[str, Any] = None) -> Dict[str, List[str]]:
        """获取默认计划（AI生成失败时的备用）"""
        return {
            "food": [
                "早餐：全麦面包2片+鸡蛋1个+牛奶200ml",
                "午餐：糙米饭150g+鸡胸肉100g+蔬菜沙拉200g",
                "晚餐：清蒸鱼150g+西兰花150g+豆腐汤",
                "加餐：苹果1个或酸奶1杯",
                "饮水：确保喝足8杯水（约2000ml）"
            ],
            "movement": [
                "有氧运动：快走或慢跑30分钟",
                "力量训练：俯卧撑3组×10次+深蹲3组×15次",
                "注意事项：运动前热身5分钟，运动后拉伸10分钟"
            ]
        }

    # 修改 auto_generate_daily_plan 方法
    def auto_generate_daily_plan(self, openai_client, user_profile: Dict[str, Any] = None) -> bool:
        """
        自动生成今日计划（整合功能）

        Args:
            openai_client: OpenAI客户端实例
            user_profile: 用户档案数据（可选）

        Returns:
            是否成功
        """
        try:
            # 1. 获取前三天摘要
            three_day_summary = self.get_three_day_summary()
            print(f"📊 前三天摘要：\n{three_day_summary[:200]}...")

            # 2. 获取当前负面因子状态
            negative_summary = self.get_factor_impact_summary()
            print(f"⚠️ 当前健康问题：\n{negative_summary}")

            # 3. 检查运动能力
            exercise_check = self.can_user_exercise_today()
            if not exercise_check.get("can_exercise", True):
                print(f"🚫 运动限制：{exercise_check.get('reason', '')}")
                print(f"💡 建议：{exercise_check.get('suggestion', '')}")

            # 4. 使用大模型基于摘要生成今日详细计划
            print("🤖 正在使用AI生成个性化健康计划...")
            today_plan = self.create_today_plan_with_ai(three_day_summary, openai_client, user_profile)

            # 5. 保存计划
            success = self.set_daily_plan(today_plan["food"], today_plan["movement"])

            if success:
                print("✅ 已自动生成今日详细健康计划！")
                self.print_today_plan()

                #特别提醒
                active_factors = self.get_active_negative_factors()
                if active_factors:
                    print("\n💡 温馨提示：")
                    print("由于您当前有健康问题，计划已特别调整。")
                    print("请务必注意安全，如有不适立即停止。")

            return success

        except Exception as e:
            print(f"❌ 自动生成计划失败: {e}")
            return False

    def add_daily_history(self, role: str, content: str) -> bool:
        """
        添加对话到每日历史记录

        Args:
            role: 角色 ('user' 或 'assistant')
            content: 内容

        Returns:
            是否成功
        """
        try:
            data = self.load_today_record()

            # 确保 daily_history 存在
            if "daily_history" not in data:
                data["daily_history"] = []

            # 添加新记录
            history_entry = {
                "role": role,
                "content": content,
                "timestamp": datetime.datetime.now().isoformat()
            }
            data["daily_history"].append(history_entry)

            # 限制历史记录长度，避免文件过大
            if len(data["daily_history"]) > 100:
                data["daily_history"] = data["daily_history"][-50:]

            # 更新最后修改时间
            data["last_updated"] = datetime.datetime.now().isoformat()

            # 保存文件
            self.save_today_record(data)
            return True

        except Exception as e:
            print(f"❌ 添加对话历史失败: {e}")
            return False

    def get_daily_history(self, limit: int = 10) -> List[Dict]:
        """
        获取最近的每日历史记录

        Args:
            limit: 返回的记录条数限制

        Returns:
            历史记录列表
        """
        try:
            data = self.load_today_record()
            history = data.get("daily_history", [])

            # 返回最近的记录
            return history[-limit:]

        except Exception as e:
            print(f"❌ 获取对话历史失败: {e}")
            return []

    def get_conversation_context(self) -> str:
        """
        获取对话上下文（用于大模型）

        Returns:
            格式化的对话上下文
        """
        history = self.get_daily_history(20)  # 获取最近20条记录

        if not history:
            return "今天是全新的一天，还没有对话记录。"

        # 格式化历史记录
        context_lines = []
        for entry in history:
            role = entry.get("role", "")
            content = entry.get("content", "")

            if role == "user":
                context_lines.append(f"用户: {content}")
            elif role == "assistant":
                context_lines.append(f"助手: {content}")

        return "\n".join(context_lines)

    def update_meal_with_details(self, meal: str, status: str,
                                 food_info: Dict[str, Any] = None) -> bool:
        """
        更新餐次状态并包含食物详情

        Args:
            meal: 餐次名称（早餐/午餐/晚餐/宵夜）
            status: 状态（吃了/没吃）
            food_info: 食物详情信息（可选）

        Returns:
            是否成功
        """
        try:
            data = self.load_today_record()
            status_field = f"{meal}状态"

            # 准备食物信息字典
            food_details = {}
            if food_info:
                food_details = {
                    "description": food_info.get("description", ""),
                    "total_calories": food_info.get("total_calories", 0),
                    "protein_g": food_info.get("protein_g", 0),
                    "carbs_g": food_info.get("carbs_g", 0),
                    "fat_g": food_info.get("fat_g", 0),
                    "analysis_time": datetime.datetime.now().isoformat(),
                    "details": food_info.get("details", [])
                }

            # 更新状态（状态文本 + 食物详情）
            data[status_field] = (status, food_details)

            return self.save_today_record(data)

        except Exception as e:
            print(f"❌ 更新餐次详情失败: {e}")
            return False

    def get_meal_food_info(self, meal: str) -> Dict[str, Any]:
        """
        获取餐次的食物信息

        Args:
            meal: 餐次名称

        Returns:
            食物信息字典
        """
        try:
            data = self.load_today_record()
            status_field = f"{meal}状态"

            current_status = data.get(status_field, ("没吃", {}))

            if isinstance(current_status, tuple) and len(current_status) > 1:
                food_info = current_status[1]
                if isinstance(food_info, dict):
                    return food_info

            return {}

        except Exception as e:
            print(f"❌ 获取餐次食物信息失败: {e}")
            return {}

    def _get_default_negative_factors(self) -> dict:
        """获取默认的负面因子结构"""
        return {
            "factors": [],  # 负面因子列表
            "total_impact": 0,  # 总影响力评分（0-10）
            "should_exercise": True,  # 是否适合运动
            "created_at": datetime.datetime.now().isoformat(),
            "last_updated": datetime.datetime.now().isoformat()
        }

    def add_negative_factor(self, factor_type: str, description: str,
                            severity: str = "轻", duration_days: int = 1,
                            notes: str = "", should_exercise: bool = True) -> bool:
        """
        添加负面因子记录

        Args:
            factor_type: 因子类型（"受伤"、"生病"、"情绪"、"其他"）
            description: 详细描述
            severity: 严重程度（"轻"、"中"、"重"）
            duration_days: 持续时间（天数）
            notes: 额外备注
            should_exercise: 是否适合运动

        Returns:
            是否成功
        """
        try:
            data = self.load_today_record()

            # 初始化负面因子模块
            if "negative_factors" not in data:
                data["negative_factors"] = self._get_default_negative_factors()

            # 创建新的负面因子记录
            new_factor = {
                "id": len(data["negative_factors"]["factors"]) + 1,
                "type": factor_type,
                "description": description,
                "severity": severity,
                "severity_level": self._get_severity_level(severity),
                "duration_days": duration_days,
                "start_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "notes": notes,
                "should_exercise": should_exercise,
                "status": "active",  # active, recovering, recovered
                "created_at": datetime.datetime.now().isoformat(),
                "last_updated": datetime.datetime.now().isoformat()
            }

            data["negative_factors"]["factors"].append(new_factor)

            # 更新总影响力评分
            self._update_total_impact(data)

            # 更新是否适合运动
            data["negative_factors"]["should_exercise"] = should_exercise
            data["negative_factors"]["last_updated"] = datetime.datetime.now().isoformat()

            return self.save_today_record(data)

        except Exception as e:
            print(f"❌ 添加负面因子失败: {e}")
            return False

    def _get_severity_level(self, severity: str) -> int:
        """将严重程度转换为数值"""
        severity_map = {
            "轻": 1,
            "中": 2,
            "重": 3
        }
        return severity_map.get(severity, 1)

    def _update_total_impact(self, data: dict) -> None:
        """更新总影响力评分"""
        if "negative_factors" not in data or not data["negative_factors"]["factors"]:
            data["negative_factors"]["total_impact"] = 0
            return

        total = 0
        for factor in data["negative_factors"]["factors"]:
            if factor.get("status") == "active":
                severity_level = factor.get("severity_level", 1)
                total += severity_level

        # 限制在0-10分
        data["negative_factors"]["total_impact"] = min(total, 10)

    def update_factor_duration(self, factor_id: int, new_duration: int) -> bool:
        """
        更新负面因子持续时间

        Args:
            factor_id: 因子ID
            new_duration: 新的持续天数

        Returns:
            是否成功
        """
        try:
            data = self.load_today_record()

            if "negative_factors" not in data:
                return False

            # 查找并更新对应的因子
            for factor in data["negative_factors"]["factors"]:
                if factor.get("id") == factor_id:
                    factor["duration_days"] = new_duration
                    factor["last_updated"] = datetime.datetime.now().isoformat()

                    # 重新计算影响力
                    self._update_total_impact(data)
                    data["negative_factors"]["last_updated"] = datetime.datetime.now().isoformat()

                    return self.save_today_record(data)

            return False

        except Exception as e:
            print(f"❌ 更新因子持续时间失败: {e}")
            return False

    def mark_factor_recovered(self, factor_id: int, recovery_notes: str = "") -> bool:
        """
        标记负面因子为已康复

        Args:
            factor_id: 因子ID
            recovery_notes: 康复备注

        Returns:
            是否成功
        """
        try:
            data = self.load_today_record()

            if "negative_factors" not in data:
                return False

            # 查找并标记对应的因子
            for factor in data["negative_factors"]["factors"]:
                if factor.get("id") == factor_id:
                    factor["status"] = "recovered"
                    factor["recovery_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
                    factor["recovery_notes"] = recovery_notes
                    factor["last_updated"] = datetime.datetime.now().isoformat()

                    # 重新计算影响力
                    self._update_total_impact(data)
                    data["negative_factors"]["last_updated"] = datetime.datetime.now().isoformat()

                    return self.save_today_record(data)

            return False

        except Exception as e:
            print(f"❌ 标记康复失败: {e}")
            return False

    def copy_active_factors_from_previous_day(self) -> bool:
        """
        从昨天的记录中复制活跃的负面因子到今日，并增加天数

        Returns:
            是否成功
        """
        try:
            # 获取昨天的日期
            yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
            yesterday_str = yesterday.strftime("%Y-%m-%d")

            # 加载昨天的记录
            yesterday_data = self.load_date_record(yesterday_str)

            if not yesterday_data or "negative_factors" not in yesterday_data:
                return True  # 没有负面因子可复制

            # 加载今天的记录
            today_data = self.load_today_record()

            # 初始化今天的负面因子模块
            if "negative_factors" not in today_data:
                today_data["negative_factors"] = self._get_default_negative_factors()

            # 复制昨天的活跃因子
            active_factors_copied = 0
            yesterday_factors = yesterday_data["negative_factors"].get("factors", [])

            for factor in yesterday_factors:
                if factor.get("status") == "active":
                    # 创建副本，天数+1
                    new_factor = factor.copy()
                    new_factor["duration_days"] = factor.get("duration_days", 1) + 1
                    new_factor["copied_from"] = yesterday_str
                    new_factor["last_updated"] = datetime.datetime.now().isoformat()

                    # 根据持续时间和严重程度自动调整
                    self._auto_reduce_severity(new_factor)

                    # 添加到今天的记录
                    today_data["negative_factors"]["factors"].append(new_factor)
                    active_factors_copied += 1

            if active_factors_copied > 0:
                # 更新总影响力
                self._update_total_impact(today_data)
                today_data["negative_factors"]["last_updated"] = datetime.datetime.now().isoformat()

                print(f"📝 已从昨天复制了 {active_factors_copied} 个活跃负面因子到今日")

            return self.save_today_record(today_data)

        except Exception as e:
            print(f"❌ 复制负面因子失败: {e}")
            return False

    def get_active_negative_factors(self) -> list:
        """
        获取当前活跃的负面因子

        Returns:
            活跃负面因子列表
        """
        try:
            data = self.load_today_record()

            if "negative_factors" not in data:
                return []

            active_factors = []
            for factor in data["negative_factors"].get("factors", []):
                if factor.get("status") == "active":
                    active_factors.append(factor)

            return active_factors

        except Exception as e:
            print(f"❌ 获取活跃负面因子失败: {e}")
            return []

    def get_factor_impact_summary(self) -> str:
        """
        获取负面因子影响摘要

        Returns:
            摘要字符串
        """
        try:
            data = self.load_today_record()

            if "negative_factors" not in data or not data["negative_factors"].get("factors"):
                return "🎉 今日无负面因子记录！保持良好的状态哦~"

            active_factors = self.get_active_negative_factors()

            if not active_factors:
                return "✨ 今日无活跃负面因子，所有问题都已解决！"

            # 构建摘要
            summary_lines = ["⚠️ 当前活跃负面因子："]

            for factor in active_factors:
                factor_type = factor.get("type", "未知")
                description = factor.get("description", "")
                severity = factor.get("severity", "轻")
                duration = factor.get("duration_days", 1)

                summary_lines.append(
                    f"• {factor_type}：{description} "
                    f"（严重程度：{severity}，已持续{duration}天）"
                )

            # 添加总影响力评分
            total_impact = data["negative_factors"].get("total_impact", 0)
            should_exercise = data["negative_factors"].get("should_exercise", True)

            summary_lines.append(f"\n📊 总影响力评分：{total_impact}/10")
            summary_lines.append(f"🏃 是否适合运动：{'✅ 可以运动' if should_exercise else '❌ 建议休息'}")

            # 根据评分给出建议
            if total_impact <= 3:
                summary_lines.append("\n💡 建议：影响较小，保持正常活动即可")
            elif total_impact <= 6:
                summary_lines.append("\n💡 建议：中度影响，适当调整运动强度")
            else:
                summary_lines.append("\n💡 建议：影响较大，建议充分休息或就医")

            return "\n".join(summary_lines)

        except Exception as e:
            print(f"❌ 获取负面因子摘要失败: {e}")
            return "获取负面因子信息失败"

    def can_user_exercise_today(self) -> dict:
        """
        判断用户今日是否适合运动

        Returns:
            包含判断结果和建议的字典
        """
        try:
            data = self.load_today_record()

            if "negative_factors" not in data:
                return {
                    "can_exercise": True,
                    "reason": "无负面因子记录",
                    "suggestion": "可以正常进行运动",
                    "factors": []
                }

            # 获取配置的适合运动标志
            should_exercise = data["negative_factors"].get("should_exercise", True)
            active_factors = self.get_active_negative_factors()

            if not active_factors:
                return {
                    "can_exercise": True,
                    "reason": "无活跃负面因子",
                    "suggestion": "可以正常进行运动",
                    "factors": []
                }

            # 检查是否有重度因子
            severe_factors = []
            for factor in active_factors:
                if factor.get("severity") == "重":
                    severe_factors.append(factor)

            if severe_factors:
                return {
                    "can_exercise": False,
                    "reason": f"存在{len(severe_factors)}个重度负面因子",
                    "suggestion": "建议充分休息或就医，暂停剧烈运动",
                    "factors": severe_factors
                }

            # 如果没有重度因子，使用配置的标志
            if should_exercise:
                return {
                    "can_exercise": True,
                    "reason": "负面因子影响较小",
                    "suggestion": "可以进行轻度到中度运动",
                    "factors": active_factors
                }
            else:
                return {
                    "can_exercise": False,
                    "reason": "系统建议休息",
                    "suggestion": "建议休息或进行极轻度活动",
                    "factors": active_factors
                }

        except Exception as e:
            print(f"❌ 判断运动能力失败: {e}")
            return {
                "can_exercise": True,
                "reason": "判断失败，请谨慎运动",
                "suggestion": "建议根据自身感觉决定",
                "factors": []
            }

    def _get_default_plan_with_factors(self, user_profile: Dict[str, Any] = None, active_factors: List[Dict] = None) -> \
    Dict[str, List[str]]:
        """
        获取基于负面因子的默认计划

        Args:
            user_profile: 用户档案
            active_factors: 活跃负面因子列表

        Returns:
            考虑负面因子的默认计划
        """
        if not active_factors:
            # 没有负面因子，返回标准计划
            return {
                "food": [
                    "早餐：全麦面包2片+鸡蛋1个+牛奶200ml",
                    "午餐：糙米饭150g+鸡胸肉100g+蔬菜沙拉200g",
                    "晚餐：清蒸鱼150g+西兰花150g+豆腐汤",
                    "加餐：苹果1个或酸奶1杯",
                    "饮水：确保喝足8杯水（约2000ml）"
                ],
                "movement": [
                    "有氧运动：快走或慢跑30分钟",
                    "力量训练：俯卧撑3组×10次+深蹲3组×15次",
                    "注意事项：运动前热身5分钟，运动后拉伸10分钟"
                ]
            }

        # 根据负面因子类型调整计划
        has_injury = any(factor.get('type') == '受伤' for factor in active_factors)
        has_illness = any(factor.get('type') == '生病' for factor in active_factors)
        has_emotion = any(factor.get('type') == '情绪' for factor in active_factors)

        # 饮食计划调整
        food_plan = []

        if has_illness:
            # 生病时的易消化食物
            food_plan = [
                "早餐：白粥1碗+蒸蛋1个+清淡小菜",
                "午餐：软米饭半碗+清蒸鱼100g+冬瓜汤",
                "晚餐：面条1小碗+蒸鸡胸肉80g+蔬菜泥",
                "加餐：香蕉1根或温蜂蜜水",
                "饮水：多喝温水，可以加少量柠檬"
            ]
        elif has_injury:
            # 受伤时的恢复食物
            food_plan = [
                "早餐：燕麦粥+水煮蛋+牛奶",
                "午餐：糙米饭+炖牛肉+菠菜（补充蛋白质和铁）",
                "晚餐：鱼肉+豆腐+西兰花（促进伤口愈合）",
                "加餐：橙子1个（补充维生素C）",
                "饮水：充足饮水，帮助代谢"
            ]
        elif has_emotion:
            # 情绪问题的安慰食物
            food_plan = [
                "早餐：香蕉燕麦粥+坚果（香蕉提升情绪）",
                "午餐：三文鱼+糙米饭+深绿色蔬菜（Omega-3改善情绪）",
                "晚餐：鸡肉+红薯+蘑菇（色氨酸帮助放松）",
                "加餐：黑巧克力一小块（提升情绪）",
                "饮水：花草茶帮助放松"
            ]
        else:
            # 标准健康饮食
            food_plan = [
                "早餐：全麦面包2片+鸡蛋1个+牛奶200ml",
                "午餐：糙米饭150g+鸡胸肉100g+蔬菜沙拉200g",
                "晚餐：清蒸鱼150g+西兰花150g+豆腐汤",
                "加餐：苹果1个或酸奶1杯",
                "饮水：确保喝足8杯水（约2000ml）"
            ]

        # 运动计划调整
        movement_plan = []

        if has_injury:
            # 受伤时的替代运动
            severity = "重"
            for factor in active_factors:
                if factor.get('type') == '受伤':
                    severity = factor.get('severity', '轻')
                    break

            if severity == "重":
                movement_plan = [
                    "运动类型：完全休息",
                    "运动时长：0分钟（需要充分休息）",
                    "运动强度：无",
                    "注意事项：受伤部位绝对休息，不要勉强运动",
                    "鼓励：好好休息是为了更快恢复，身体需要时间修复哦！"
                ]
            elif severity == "中":
                movement_plan = [
                    "运动类型：上肢运动或核心训练（避免使用受伤部位）",
                    "运动时长：20-30分钟",
                    "运动强度：低强度",
                    "注意事项：避免任何涉及受伤部位的动作，如有疼痛立即停止",
                    "鼓励：保护受伤部位的同时保持其他部位运动，很棒的选择！"
                ]
            else:
                movement_plan = [
                    "运动类型：轻度有氧（如散步、固定自行车）",
                    "运动时长：20-30分钟",
                    "运动强度：低到中等强度",
                    "注意事项：注意受伤部位感觉，稍有不适就停止",
                    "鼓励：慢慢来，给身体适应的时间，你会逐渐恢复的！"
                ]
        elif has_illness:
            # 生病时的运动建议
            movement_plan = [
                "运动类型：休息或极轻度活动",
                "运动时长：根据体力决定，不要勉强",
                "运动强度：非常低",
                "注意事项：生病期间以休息为主，等康复后再恢复运动",
                "鼓励：身体正在对抗病菌，好好休息是最佳选择！"
            ]
        elif has_emotion:
            # 情绪问题时的温和运动
            movement_plan = [
                "运动类型：瑜伽、散步、太极等温和运动",
                "运动时长：20-40分钟",
                "运动强度：温和",
                "注意事项：选择让你感到舒适和放松的运动",
                "鼓励：运动可以释放快乐激素，让心情变得更好哦！"
            ]
        else:
            # 标准运动计划
            movement_plan = [
                "有氧运动：快走或慢跑30分钟",
                "力量训练：俯卧撑3组×10次+深蹲3组×15次",
                "注意事项：运动前热身5分钟，运动后拉伸10分钟"
            ]

        return {
            "food": food_plan,
            "movement": movement_plan
        }

    def _validate_plan_against_factors(self, plan: Dict[str, List[str]], active_factors: List[Dict]):
        """
        验证计划是否考虑了负面因子

        Args:
            plan: AI生成的计划
            active_factors: 活跃负面因子列表
        """
        if not active_factors:
            print("✅ 计划验证：无负面因子，计划通过")
            return

        movement_plan = " ".join(plan.get("movement", []))
        food_plan = " ".join(plan.get("food", []))

        warnings = []

        for factor in active_factors:
            factor_type = factor.get('type', '')
            severity = factor.get('severity', '轻')
            description = factor.get('description', '')

            if factor_type == "受伤":
                # 检查是否提到了受伤注意事项
                injury_keywords = ["受伤", "避免", "保护", "休息", "疼痛", "停止"]
                if not any(keyword in movement_plan for keyword in injury_keywords):
                    warnings.append(f"⚠️ 运动计划可能未充分考虑受伤问题：{description}")

                # 检查是否建议了促进恢复的食物
                if severity in ["中", "重"]:
                    recovery_foods = ["蛋白质", "维生素C", "锌", "胶原蛋白"]
                    if not any(food in food_plan for food in recovery_foods):
                        warnings.append(f"⚠️ 饮食计划可能未包含受伤恢复所需营养")

            elif factor_type == "生病":
                # 检查是否建议了易消化食物
                if "易消化" not in food_plan and "清淡" not in food_plan:
                    warnings.append(f"⚠️ 生病期间建议更易消化的食物")

            elif factor_type == "情绪":
                # 检查是否建议了温和运动
                gentle_exercise = ["瑜伽", "散步", "太极", "温和", "放松"]
                if not any(exercise in movement_plan for exercise in gentle_exercise):
                    warnings.append(f"⚠️ 情绪问题建议更温和的运动方式")

        if warnings:
            print("🔍 计划验证警告：")
            for warning in warnings:
                print(f"  {warning}")
        else:
            print("✅ 计划验证：已充分考虑所有负面因子")

        def _auto_reduce_severity(self, factor: Dict[str, Any]) -> None:
            """
            根据持续时间自动减轻负面因子的严重程度

            规则：
            - 轻度问题：3天后自动减轻或建议康复
            - 中度问题：5天后自动减轻
            - 重度问题：7天后自动减轻
            - 超过14天：自动标记为"恢复中"
            - 超过30天：自动康复
            """
            duration = factor.get("duration_days", 1)
            current_severity = factor.get("severity", "轻")
            factor_type = factor.get("type", "")

            # 不同类型的问题有不同的恢复时间
            recovery_timelines = {
                "受伤": {"轻": 3, "中": 7, "重": 14},
                "生病": {"轻": 3, "中": 5, "重": 10},
                "情绪": {"轻": 2, "中": 4, "重": 7},
                "疲劳": {"轻": 2, "中": 3, "重": 5},
                "其他": {"轻": 3, "中": 5, "重": 7}
            }

            # 获取该类型问题的恢复时间
            timeline = recovery_timelines.get(factor_type, recovery_timelines["其他"])
            recovery_days = timeline.get(current_severity, 3)

            # 记录原始值，用于大模型参考
            if "original_severity" not in factor:
                factor["original_severity"] = current_severity
            if "original_start_date" not in factor:
                factor["original_start_date"] = factor.get("start_date", "")

            # 判断是否需要调整严重程度
            if current_severity == "重":
                if duration >= recovery_days:
                    # 重度问题达到恢复时间后降为中度
                    factor["severity"] = "中"
                    factor["severity_level"] = 2
                    factor["auto_reduced"] = True
                    factor["reduction_reason"] = f"持续{duration}天后自动减轻"
                    factor["reduction_date"] = datetime.datetime.now().strftime("%Y-%m-%d")

                    # 如果是受伤，调整运动建议
                    if factor_type == "受伤":
                        factor["should_exercise"] = False  # 中度受伤仍不建议运动
                elif duration >= recovery_days * 2:
                    # 两倍恢复时间后降为轻度
                    factor["severity"] = "轻"
                    factor["severity_level"] = 1
                    factor["auto_reduced"] = True
                    factor["reduction_reason"] = f"持续{duration}天后显著改善"

                    # 调整运动建议
                    factor["should_exercise"] = True  # 轻度可以适当运动

            elif current_severity == "中":
                if duration >= recovery_days:
                    # 中度问题达到恢复时间后降为轻度
                    factor["severity"] = "轻"
                    factor["severity_level"] = 1
                    factor["auto_reduced"] = True
                    factor["reduction_reason"] = f"持续{duration}天后自动减轻"

                    # 调整运动建议
                    factor["should_exercise"] = True  # 轻度可以适当运动
                elif duration >= recovery_days * 1.5:
                    # 1.5倍恢复时间后建议确认康复
                    factor["status"] = "recovering"
                    factor["recovery_suggested"] = True
                    factor["recovery_reason"] = f"已持续{duration}天，建议确认是否已完全康复"

            elif current_severity == "轻":
                if duration >= recovery_days:
                    # 轻度问题达到恢复时间后建议确认康复
                    factor["status"] = "recovering"
                    factor["recovery_suggested"] = True
                    factor["recovery_reason"] = f"已持续{duration}天，建议确认是否已完全康复"
                elif duration >= recovery_days * 2:
                    # 两倍恢复时间后自动康复
                    factor["status"] = "recovered"
                    factor["recovery_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
                    factor["recovery_notes"] = f"持续{duration}天后系统自动标记康复"
                    factor["auto_recovered"] = True

            # 超过30天的活跃负面因子，强制标记为康复
            if duration >= 30 and factor.get("status") == "active":
                factor["status"] = "recovered"
                factor["recovery_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
                factor["recovery_notes"] = f"持续{duration}天，系统自动标记康复"
                factor["auto_recovered"] = True

            # 记录恢复进度百分比（用于大模型参考）
            recovery_percent = min(100, (duration / recovery_days) * 100)
            factor["recovery_progress"] = round(recovery_percent, 1)
            factor["estimated_recovery_days"] = max(0, recovery_days - duration)
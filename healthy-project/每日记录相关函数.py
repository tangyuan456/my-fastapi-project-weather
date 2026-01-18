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
                "早餐状态": "没吃",
                "午餐状态": "没吃",
                "晚餐状态": "没吃",
                "宵夜状态": "没吃",
                "运动状态": "没运动",
                "daily_history": [],  # 当日对话历史
                "summary": "",  # 当日总结
                "last_updated": datetime.datetime.now().isoformat()
            }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 创建今日记录文件: {filename}")
        return initial_data

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

    def add_daily_history(self, role: str, content: str) -> bool:
        """
        添加当日对话历史

        Args:
            role: 角色 ('user' 或 'assistant')
            content: 对话内容

        Returns:
            是否成功
        """
        try:
            data = self.load_today_record()

            note = {
                "role": role,
                "content": content[:500],  # 限制长度
                "timestamp": datetime.datetime.now().isoformat()
            }

            data["daily_history"].append(note)

            # 限制最多保存100条对话历史
            if len(data["daily_history"]) > 100:
                data["daily_history"] = data["daily_history"][-100:]

            return self.save_today_record(data)

        except Exception as e:
            print(f"❌ 添加对话历史失败: {e}")
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

            # 构建大模型提示词
            prompt = f"""你是一个专业的健康营养师和健身教练。请根据以下信息为用户制定今日的健康计划。

    {user_info}

    前三天健康记录摘要：
    {three_day_summary}

    请制定一个详细、可执行的今日健康计划，包括：

    1. 饮食计划（food）[不能和前三天一摸一样，要变换花样，且要丰盛]：
       - 早餐（具体食物、分量）
       - 午餐（具体食物、分量）  
       - 晚餐（具体食物、分量）
       - 加餐建议
       - 饮水提醒

    2. 运动计划（movement）：
       - 运动类型
       - 运动时长
       - 运动强度
       - 注意事项
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
        "注意事项",
        "鼓励"
      ]
    }}

    要求：
    1. 基于前三天的记录进行个性化调整，
    2. 计划要具体、可执行、且强度要适中
    3. 考虑营养均衡、运动安全和用户偏好
    4. 语气温和且专业
    4. 用中文回复"""

            # 调用大模型
            response = openai_client.chat.completions.create(
                model="qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是专业的健康管理专家，擅长制定个性化的饮食和运动计划。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
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
                        return today_plan
                    else:
                        print("⚠️ AI返回的计划格式不完整，使用默认计划")

                except json.JSONDecodeError:
                    print("❌ AI返回的JSON格式错误，使用默认计划")

            # 如果AI生成失败，返回默认计划
            return self._get_default_plan(user_profile)

        except Exception as e:
            print(f"❌ 使用AI生成计划失败: {e}")
            # 返回默认计划
            return self._get_default_plan(user_profile)

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

            # 2. 使用大模型基于摘要生成今日详细计划
            print("🤖 正在使用AI生成个性化健康计划...")
            today_plan = self.create_today_plan_with_ai(three_day_summary, openai_client, user_profile)

            # 3. 保存计划
            success = self.set_daily_plan(today_plan["food"], today_plan["movement"])

            if success:
                print("✅ 已自动生成今日详细健康计划！")
                self.print_today_plan()

            return success

        except Exception as e:
            print(f"❌ 自动生成计划失败: {e}")
            return False
"""
历史总结函数模块
负责生成、保存和管理历史健康记录的总结
依赖：每日记录相关函数.DailyHealthRecorder
"""

import os
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple
import re


class HistorySummaryManager:
    """历史总结管理器"""

    def __init__(self, daily_recorder):
        """
        初始化历史总结管理器

        Args:
            daily_recorder: DailyHealthRecorder实例，用于访问记录数据
        """
        self.recorder = daily_recorder
        self.base_dir = daily_recorder.base_dir

    def find_latest_record_date(self, max_days_back: int = 30) -> Optional[str]:
        """
        查找最近有记录的日期（跳过今天）

        Args:
            max_days_back: 最多回溯多少天

        Returns:
            最近有记录的日期字符串（YYYY-MM-DD），如果没有返回None

        说明：使用每日相关函数中的load_date_record方法
        """
        try:
            # 使用recorder的get_date_filename方法（如果存在）或者直接构建路径
            for days_ago in range(1, max_days_back + 1):
                check_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
                date_str = check_date.strftime("%Y-%m-%d")

                # 使用每日相关函数中的load_date_record方法
                record_data = self.recorder.load_date_record(date_str)

                if record_data:
                    # 检查是否有实际记录
                    has_history = bool(record_data.get("daily_history", []))
                    has_meal_records = any(
                        self._get_meal_status(record_data, meal) == "吃了"
                        for meal in ["早餐", "午餐", "晚餐", "宵夜"]
                    )
                    has_summary = bool(record_data.get("summary", "").strip())

                    # 如果有对话记录、餐次记录或已有总结，都算有效记录
                    if has_history or has_meal_records or has_summary:
                        print(f"📅 找到最近有效记录：{date_str}（{days_ago}天前）")
                        return date_str

            print(f"📭 在最近{max_days_back}天内没有找到有效记录")
            return None

        except Exception as e:
            print(f"❌ 查找最近记录日期失败: {e}")
            return None

    def _get_meal_status(self, data: Dict[str, Any], meal: str) -> str:
        """获取餐次状态（兼容元组和旧格式）"""
        status_field = f"{meal}状态"
        meal_status = data.get(status_field, ("没吃", ""))

        if isinstance(meal_status, tuple):
            return meal_status[0]
        elif isinstance(meal_status, str):
            return meal_status
        else:
            return "没吃"

    def _get_meal_food_info(self, data: Dict[str, Any], meal: str) -> Dict[str, Any]:
        """获取餐次食物信息"""
        status_field = f"{meal}状态"
        meal_status = data.get(status_field, ("没吃", ""))

        if isinstance(meal_status, tuple) and len(meal_status) > 1:
            food_info = meal_status[1]
            if isinstance(food_info, dict):
                return food_info

        return {}

    def generate_summary_for_date(self, date_str: str, ai_client=None) -> Tuple[str, bool]:
        """
        为指定日期生成总结

        Args:
            date_str: 日期字符串（YYYY-MM-DD）
            ai_client: OpenAI客户端实例（可选）

        Returns:
            (总结文本, 是否是新生成的)

        说明：调用每日相关函数中的load_date_record和save_today_record方法
        """
        try:
            # 使用每日相关函数中的load_date_record方法
            target_data = self.recorder.load_date_record(date_str)

            if not target_data:
                return f"{date_str} 没有记录文件。", False

            # 检查是否已经有总结
            existing_summary = target_data.get("summary", "").strip()
            if existing_summary:
                print(f"✅ {date_str} 的总结已存在")
                return existing_summary, False

            print(f"🤖 正在为 {date_str} 生成总结...")

            # 获取所有历史记录
            history = target_data.get("daily_history", [])

            # 收集关键信息
            key_events = self._collect_key_events(target_data)

            # 分析对话主题
            conversation_themes = self._analyze_conversation_themes(history)
            if conversation_themes:
                key_events.append(f"💬 主要话题：{', '.join(conversation_themes)}")

            # 计算总体完成度
            completion_stats = self._calculate_completion_stats(target_data)
            key_events.append(f"📊 总体完成度：{completion_stats}")

            # 如果有AI客户端且历史记录足够，使用AI生成
            if ai_client and len(history) >= 3:
                try:
                    summary = self._generate_ai_summary(
                        target_data, date_str, key_events, history, ai_client
                    )
                except Exception as ai_error:
                    print(f"⚠️ AI生成{date_str}总结失败，使用标准总结: {ai_error}")
                    summary = self._generate_standard_summary(target_data, date_str, key_events)
            else:
                summary = self._generate_standard_summary(target_data, date_str, key_events)

            # 保存总结（注意：这里需要特殊处理，因为save_today_record只能保存今天）
            # 我们需要直接保存到指定日期的文件
            self._save_summary_to_date_file(date_str, target_data, summary)

            return summary, True

        except Exception as e:
            print(f"❌ 生成{date_str}总结失败: {e}")
            return f"{date_str}总结生成失败：{str(e)}", False

    def _save_summary_to_date_file(self, date_str: str, original_data: Dict[str, Any],
                                   summary: str) -> bool:
        """保存总结到指定日期的文件"""
        try:
            # 更新数据
            updated_data = original_data.copy()
            updated_data["summary"] = summary
            updated_data["last_updated"] = datetime.datetime.now().isoformat()

            # 构建文件路径
            filename = os.path.join(self.base_dir, f"{date_str}.json")

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)

            print(f"✅ 已保存{date_str}的总结（{len(summary)}字）")
            return True

        except Exception as e:
            print(f"❌ 保存{date_str}总结失败: {e}")
            return False

    def _collect_key_events(self, data: Dict[str, Any]) -> List[str]:
        """收集关键事件"""
        key_events = []

        # 1. 餐次记录
        meals = []
        for meal in ["早餐", "午餐", "晚餐", "宵夜"]:
            status = self._get_meal_status(data, meal)
            if status == "吃了":
                food_info = self._get_meal_food_info(data, meal)
                if food_info.get("description"):
                    calories = food_info.get('total_calories', 0)
                    cal_info = f" ({calories}大卡)" if calories > 0 else ""
                    meals.append(f"{meal}: {food_info.get('description')}{cal_info}")
                else:
                    meals.append(f"{meal}: 已吃")

        if meals:
            key_events.append(f"🍽️ 用餐记录：{', '.join(meals)}")

        # 2. 饮水记录
        drink_plan = data.get("drink_plan", 8)
        current_drinks = data.get("drink_number", 0)
        drink_percent = round((current_drinks / drink_plan * 100), 1) if drink_plan > 0 else 0
        drink_status = f"💧 饮水：{current_drinks}/{drink_plan}杯 ({drink_percent}%)"
        key_events.append(drink_status)

        # 3. 运动记录
        exercise_status = data.get("运动状态", ("没运动", ""))
        if isinstance(exercise_status, tuple):
            exercise_text = exercise_status[0]
        else:
            exercise_text = exercise_status

        if exercise_text == "运动了":
            key_events.append("🏃 已完成运动计划")
        else:
            key_events.append("🏃 未运动")

        return key_events

    def _analyze_conversation_themes(self, history: List[Dict]) -> List[str]:
        """分析对话主题"""
        if not history:
            return []

        themes = set()

        theme_keywords = {
            "体重管理": ["体重", "bmi", "减肥", "减重", "胖", "瘦", "公斤", "kg"],
            "饮食分析": ["热量", "卡路里", "营养", "吃了", "食物", "米饭", "肉", "菜", "吃"],
            "运动指导": ["运动", "健身", "锻炼", "跑步", "走路", "瑜伽", "训练"],
            "健康计划": ["计划", "安排", "目标", "明天", "今天", "日程"],
            "健康咨询": ["建议", "怎么", "如何", "为什么", "原因", "问题"],
            "情绪支持": ["开心", "难过", "压力", "累", "辛苦", "鼓励", "加油", "谢谢"]
        }

        for entry in history:
            content = entry.get("content", "").lower()
            for theme, keywords in theme_keywords.items():
                if any(keyword in content for keyword in keywords):
                    themes.add(theme)

        return list(themes)[:3]  # 最多返回3个主题

    def _calculate_completion_stats(self, data: Dict[str, Any]) -> str:
        """计算总体完成度"""
        # 餐次完成数
        meals_eaten = sum(
            1 for meal in ["早餐", "午餐", "晚餐", "宵夜"]
            if self._get_meal_status(data, meal) == "吃了"
        )

        # 饮水完成度
        drink_plan = data.get("drink_plan", 8)
        current_drinks = data.get("drink_number", 0)
        drink_percent = round((current_drinks / drink_plan * 100), 1) if drink_plan > 0 else 0

        # 运动完成
        exercise_status = data.get("运动状态", ("没运动", ""))
        if isinstance(exercise_status, tuple):
            exercise_done = exercise_status[0] == "运动了"
        else:
            exercise_done = exercise_status == "运动了"

        return f"{meals_eaten}/4餐，饮水{drink_percent}%，运动{'✓' if exercise_done else '✗'}"

    def _generate_standard_summary(self, data: Dict[str, Any], date_str: str, key_events: List[str]) -> str:
        """生成标准总结"""
        summary_lines = [
            f"📊 {date_str} 健康总结",
            "",
            "🎯 完成情况："
        ]

        summary_lines.extend([f"  • {event}" for event in key_events])
        summary_lines.extend([
            "",
            "💪 健康小贴士：",
            "  • 规律作息，均衡饮食",
            "  • 每天保证充足水分",
            "  • 适量运动，保持活力",
            "",
            "🌟 继续加油，坚持就是胜利！"
        ])

        return "\n".join(summary_lines)

    def _generate_ai_summary(self, data: Dict[str, Any], date_str: str,
                             key_events: List[str], history: List[Dict],
                             ai_client) -> str:
        """使用AI生成总结"""

        # 准备对话摘要（取开头和结尾各3条）
        conversation_samples = []
        if len(history) > 0:
            # 开头
            for i in range(min(3, len(history))):
                entry = history[i]
                role = "用户" if entry.get("role") == "user" else "助手"
                content = entry.get("content", "")[:200]
                conversation_samples.append(f"{role}: {content}")

            # 结尾（如果有足够记录）
            if len(history) > 6:
                for i in range(max(0, len(history) - 3), len(history)):
                    entry = history[i]
                    role = "用户" if entry.get("role") == "user" else "助手"
                    content = entry.get("content", "")[:200]
                    conversation_samples.append(f"{role}: {content}")

        prompt = f"""你是一个贴心的健康教练，请基于用户{date_str}的健康记录生成一个温暖、鼓励的总结报告。

【健康数据概览】
{chr(10).join(key_events)}

【对话摘要】
{chr(10).join(conversation_samples) if conversation_samples else "当天没有对话记录"}

【总结要求】
1. 开头亲切问候，提及日期
2. 对重要信息进行总结：
    -早中晚及宵夜的食用，计算总摄入的热量
    -运动情况，计算总燃烧的卡路里
    -是否有体重变化、是否制造了热量缺口
    -其他情况
3. 根据对话内容给予个性化反馈
4. 真诚表扬做得好的地方，若用户前一天有记录到不好的事，温柔安慰并鼓励
5. 提供1个具体、可行的改进建议
6. 识别用户受伤或生病的消息，要着重强调（这将是后面安排的重要依据），可以通过对用户的关心等方式来强调
7. 用温暖鼓励的话语结束

请用中文生成一个150-200字的总结，要分行输出，语气温暖、专业、有亲和力。"""

        response = ai_client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的健康管理教练，擅长从健康数据中提炼亮点并给予个性化鼓励。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )

        return response.choices[0].message.content.strip()

    def process_latest_unsummarized_record(self, ai_client=None, max_days_back: int = 30) -> Tuple[
        Optional[str], str, bool]:
        """
        处理最近未总结的记录

        Args:
            ai_client: OpenAI客户端实例（可选）
            max_days_back: 最多回溯多少天

        Returns:
            (日期字符串, 总结文本, 是否成功生成新总结)

        说明：这是主要的外部调用接口
        """
        try:
            # 1. 查找最近有记录的日期
            latest_date = self.find_latest_record_date(max_days_back)

            if not latest_date:
                print("📭 没有找到需要总结的历史记录")
                return None, "没有找到需要总结的历史记录", False

            # 2. 检查该日期是否已有总结
            record_data = self.recorder.load_date_record(latest_date)
            if record_data and record_data.get("summary", "").strip():
                print(f"✅ {latest_date} 已有总结")
                return latest_date, record_data["summary"], False

            # 3. 生成总结
            print(f"📝 为 {latest_date} 生成总结...")
            summary, is_new = self.generate_summary_for_date(latest_date, ai_client)

            if is_new:
                print(f"✅ 成功为 {latest_date} 生成新总结")
                return latest_date, summary, True
            else:
                print(f"⚠️  {latest_date} 总结已存在或生成失败")
                return latest_date, summary, False

        except Exception as e:
            print(f"❌ 处理最近未总结记录失败: {e}")
            return None, f"处理失败：{str(e)}", False

    def clear_history_for_date(self, date_str: str, keep_summary: bool = True) -> bool:
        """
        清理指定日期的历史记录（可选保留总结）

        Args:
            date_str: 日期字符串
            keep_summary: 是否保留总结

        Returns:
            是否成功

        说明：用于节省存储空间
        """
        try:
            data = self.recorder.load_date_record(date_str)
            if not data:
                return False

            original_count = len(data.get("daily_history", []))

            if keep_summary:
                # 保留总结，清空历史记录
                summary = data.get("summary", "")
                cleared_data = {
                    "date": data.get("date", date_str),
                    "summary": summary,
                }

                # 保留其他重要字段
                for field in ["drink_plan", "drink_number", "早餐状态", "午餐状态", "晚餐状态", "宵夜状态", "运动状态",
                              "daily_plan"]:
                    if field in data:
                        cleared_data[field] = data[field]
            else:
                # 完全清空
                cleared_data = {
                    "date": data.get("date", date_str),
                }

            # 保存清理后的数据
            success = self._save_summary_to_date_file(date_str, cleared_data, "", "cleaned")

            if success:
                print(f"🗑️  已清理{date_str}的历史记录（原{original_count}条）")
                return True
            else:
                return False

        except Exception as e:
            print(f"❌ 清理{date_str}历史记录失败: {e}")
            return False
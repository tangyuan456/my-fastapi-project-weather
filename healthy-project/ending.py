import os
import json
import datetime
from typing import Dict, List, Any, Optional
import logging
from openai import OpenAI


class WeightLossJourneyAnalyzer:
    """减肥历程分析器 - 在用户达到目标体重时自动调用"""

    def __init__(self, openai_client: OpenAI, daily_records_dir: str = "daily_records"):
        """
        初始化分析器

        Args:
            openai_client: OpenAI客户端实例
            daily_records_dir: 每日记录目录
        """
        self.client = openai_client
        self.daily_records_dir = daily_records_dir
        self.profiles_file = "user_profiles.json"

        # 配置日志
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def load_user_profile(self) -> Optional[Dict[str, Any]]:
        """加载用户档案"""
        try:
            if not os.path.exists(self.profiles_file):
                return None

            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                profiles = json.load(f)

            # 取第一个用户（一对一应用）
            if profiles and isinstance(profiles, dict) and len(profiles) > 0:
                user_key = list(profiles.keys())[0]
                return profiles[user_key]
            return None

        except Exception as e:
            logging.error(f"加载用户档案失败: {e}")
            return None

    def load_all_daily_records(self) -> List[Dict[str, Any]]:
        """加载所有每日记录（排除对话历史）"""
        daily_records = []

        try:
            if not os.path.exists(self.daily_records_dir):
                return []

            # 获取所有JSON文件
            json_files = [f for f in os.listdir(self.daily_records_dir) if f.endswith('.json')]

            for filename in sorted(json_files):
                filepath = os.path.join(self.daily_records_dir, filename)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        record = json.load(f)

                    # 移除对话历史以简化数据
                    if "daily_history" in record:
                        del record["daily_history"]

                    # 移除其他不必要的大字段
                    for key in list(record.keys()):
                        if isinstance(record.get(key), list) and len(record[key]) > 10:
                            # 保留但截断长列表
                            record[key] = record[key][:5]

                    daily_records.append(record)

                except Exception as e:
                    logging.warning(f"读取文件 {filename} 失败: {e}")
                    continue

        except Exception as e:
            logging.error(f"加载每日记录失败: {e}")

        return daily_records

    def calculate_weight_progress(self, user_profile: Dict[str, Any], daily_records: List[Dict[str, Any]]) -> Dict[
        str, Any]:
        """计算体重变化进度"""
        try:
            if not user_profile:
                return {}

            # 获取关键体重数据
            current_weight = user_profile.get('current_weight_kg', 0)
            target_weight = user_profile.get('target_weight_kg', 0)
            initial_weight = user_profile.get('initial_weight_kg', current_weight)
            height = user_profile.get('height_cm', 170)

            # 计算变化
            total_loss = initial_weight - current_weight if initial_weight > current_weight else 0
            target_loss = initial_weight - target_weight if initial_weight > target_weight else 0

            # 提取每日记录中的体重信息（如果有的话）
            weight_records = []
            for record in daily_records:
                date = record.get('date', '')
                if date:
                    # 检查是否有体重记录
                    weight_data = record.get('weight_data', {})
                    if weight_data and isinstance(weight_data, dict):
                        weight = weight_data.get('weight_kg')
                        if weight:
                            weight_records.append({
                                'date': date,
                                'weight': weight
                            })

            return {
                'initial_weight': initial_weight,
                'current_weight': current_weight,
                'target_weight': target_weight,
                'height': height,
                'total_loss': round(total_loss, 1),
                'target_loss': round(target_loss, 1),
                'progress_percent': round((total_loss / target_loss * 100), 1) if target_loss > 0 else 0,
                'weight_records': weight_records[-10:],  # 取最近10次记录
                'is_goal_reached': current_weight <= target_weight
            }

        except Exception as e:
            logging.error(f"计算体重进度失败: {e}")
            return {}

    def analyze_daily_habits(self, daily_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析每日习惯"""
        try:
            if not daily_records:
                return {}

            total_days = self.calculate_total_days(user_profile, daily_records)

            # 统计吃饭习惯
            meal_stats = {
                '早餐': {'ate': 0, 'total': 0},
                '午餐': {'ate': 0, 'total': 0},
                '晚餐': {'ate': 0, 'total': 0},
                '宵夜': {'ate': 0, 'total': 0}
            }

            # 统计喝水情况
            drink_stats = {
                'total_days': 0,
                'total_cups': 0,
                'days_met_goal': 0,
                'average_cups': 0
            }

            # 统计运动情况
            exercise_stats = {
                'total_days': 0,
                'exercise_days': 0,
                'exercise_percent': 0
            }

            # 统计健康问题
            health_stats = {
                'total_factors': 0,
                'injury_days': 0,
                'illness_days': 0,
                'emotion_days': 0
            }

            # 统计计划执行 - 新增：统计小助手规划情况
            plan_stats = {
                'total_days': total_days,
                'planned_days': 0,
                'plan_follow_rate': 0,
                'ai_generated_plans': 0,  # AI生成的计划次数
                'user_modified_plans': 0,  # 用户修改计划的次数
                'food_plans_count': 0,  # 饮食规划次数
                'exercise_plans_count': 0  # 运动规划次数
            }

            for record in daily_records:
                # 吃饭统计
                for meal in meal_stats.keys():
                    status_field = f"{meal}状态"
                    status = record.get(status_field, ("没吃", ""))
                    if isinstance(status, tuple):
                        meal_status = status[0]
                    else:
                        meal_status = status

                    meal_stats[meal]['total'] += 1
                    if meal_status == "吃了":
                        meal_stats[meal]['ate'] += 1

                # 喝水统计
                drink_cups = record.get('drink_number', 0)
                drink_target = record.get('drink_plan', 8)

                if drink_cups > 0:
                    drink_stats['total_days'] += 1
                    drink_stats['total_cups'] += drink_cups
                    if drink_cups >= drink_target:
                        drink_stats['days_met_goal'] += 1

                # 运动统计
                exercise_status = record.get('运动状态', ("没运动", ""))
                if isinstance(exercise_status, tuple):
                    exercised = exercise_status[0] != "没运动"
                else:
                    exercised = exercise_status != "没运动"

                exercise_stats['total_days'] += 1
                if exercised:
                    exercise_stats['exercise_days'] += 1

                # 健康问题统计
                negative_factors = record.get('negative_factors', {})
                factors = negative_factors.get('factors', [])
                health_stats['total_factors'] += len(factors)

                for factor in factors:
                    factor_type = factor.get('type', '')
                    if factor_type == '受伤':
                        health_stats['injury_days'] += 1
                    elif factor_type == '生病':
                        health_stats['illness_days'] += 1
                    elif factor_type == '情绪':
                        health_stats['emotion_days'] += 1

                # 计划执行统计 - 新增详细统计
                daily_plan = record.get('daily_plan', {})
                has_plan = bool(daily_plan.get('food') or daily_plan.get('movement'))

                if has_plan:
                    plan_stats['planned_days'] += 1

                    # 统计饮食和运动规划
                    food_plan = daily_plan.get('food', [])
                    movement_plan = daily_plan.get('movement', [])

                    if food_plan:
                        plan_stats['food_plans_count'] += 1
                    if movement_plan:
                        plan_stats['exercise_plans_count'] += 1

                    # 检查是否为AI生成（通过created_at判断是否系统自动生成）
                    created_at = daily_plan.get('created_at', '')
                    if created_at and 'auto_generate' in str(daily_plan).lower():
                        plan_stats['ai_generated_plans'] += 1

            # 计算百分比
            for meal in meal_stats:
                total = meal_stats[meal]['total']
                ate = meal_stats[meal]['ate']
                meal_stats[meal]['percent'] = round((ate / total * 100), 1) if total > 0 else 0

            if drink_stats['total_days'] > 0:
                drink_stats['average_cups'] = round(drink_stats['total_cups'] / drink_stats['total_days'], 1)

            if exercise_stats['total_days'] > 0:
                exercise_stats['exercise_percent'] = round(
                    (exercise_stats['exercise_days'] / exercise_stats['total_days'] * 100), 1)

            if plan_stats['total_days'] > 0:
                plan_stats['plan_follow_rate'] = round((plan_stats['planned_days'] / plan_stats['total_days'] * 100), 1)

            return {
                'meal_stats': meal_stats,
                'drink_stats': drink_stats,
                'exercise_stats': exercise_stats,
                'health_stats': health_stats,
                'plan_stats': plan_stats
            }

        except Exception as e:
            logging.error(f"分析每日习惯失败: {e}")
            return {}

    def extract_key_moments(self, daily_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取关键时刻"""
        try:
            key_moments = []

            for record in daily_records:
                date = record.get('date', '')
                summary = record.get('summary', '')

                # 检查是否有关键事件
                has_important_event = False
                event_type = "普通"
                event_desc = ""

                # 检查负面因子
                negative_factors = record.get('negative_factors', {}).get('factors', [])
                if negative_factors:
                    has_important_event = True
                    event_type = "健康挑战"
                    # 取最严重的因子
                    severities = {'轻': 1, '中': 2, '重': 3}
                    severe_factor = max(negative_factors,
                                        key=lambda x: severities.get(x.get('severity', '轻'), 1))
                    event_desc = f"遇到{severe_factor.get('type', '问题')}挑战"

                # 检查是否有运动突破
                exercise_status = record.get('运动状态', ("", ""))
                if isinstance(exercise_status, tuple):
                    exercised = exercise_status[0] != "没运动"
                else:
                    exercised = exercise_status != "没运动"

                if exercised and "跑步" in str(exercise_status) or "健身" in str(exercise_status):
                    has_important_event = True
                    event_type = "运动突破"
                    event_desc = "完成了重要运动训练"

                # 检查饮食记录
                meal_count = 0
                for meal in ["早餐", "午餐", "晚餐"]:
                    status = record.get(f"{meal}状态", ("没吃", ""))
                    if isinstance(status, tuple) and status[0] == "吃了":
                        meal_count += 1

                if meal_count == 3:
                    has_important_event = True
                    event_type = "饮食完美"
                    event_desc = "坚持了三餐规律饮食"

                # 检查是否有使用小助手规划
                daily_plan = record.get('daily_plan', {})
                if daily_plan.get('food') or daily_plan.get('movement'):
                    has_important_event = True
                    if event_type == "普通":
                        event_type = "计划执行"
                        event_desc = "按照健康计划行动"

                # 如果有总结或重要事件，添加到关键时刻
                if summary or has_important_event:
                    key_moments.append({
                        'date': date,
                        'summary': summary[:100] if summary else '',
                        'has_event': has_important_event,
                        'event_type': event_type,
                        'event_desc': event_desc,
                        'used_plan': bool(daily_plan)  # 标记是否使用了计划
                    })

            # 取最近的关键时刻（最多10个）
            return key_moments[-10:]

        except Exception as e:
            logging.error(f"提取关键时刻失败: {e}")
            return []

    def generate_journey_summary(self, user_profile: Dict[str, Any],
                                 weight_progress: Dict[str, Any],
                                 daily_habits: Dict[str, Any],
                                 key_moments: List[Dict[str, Any]]) -> str:
        """使用大模型生成减肥历程总结"""
        try:
            # 构建提示词
            nickname = user_profile.get('nickname', '亲爱的用户')
            gender = user_profile.get('gender', '')
            age = user_profile.get('age', '')
            height = weight_progress.get('height', 170)
            initial_weight = weight_progress.get('initial_weight', 0)
            current_weight = weight_progress.get('current_weight', 0)
            target_weight = weight_progress.get('target_weight', 0)
            total_loss = weight_progress.get('total_loss', 0)

            # 获取规划统计数据
            plan_stats = daily_habits.get('plan_stats', {})
            food_plans_count = plan_stats.get('food_plans_count', 0)
            exercise_plans_count = plan_stats.get('exercise_plans_count', 0)
            ai_generated_plans = plan_stats.get('ai_generated_plans', 0)
            planned_days = plan_stats.get('planned_days', 0)

            # 获取用户坚持数据
            meal_stats = daily_habits.get('meal_stats', {})
            breakfast_rate = meal_stats.get('早餐', {}).get('percent', 0)
            exercise_percent = daily_habits.get('exercise_stats', {}).get('exercise_percent', 0)
            drink_average = daily_habits.get('drink_stats', {}).get('average_cups', 0)

            # 计算规划使用率
            plan_usage_rate = round((planned_days / plan_stats.get('total_days', 1) * 100), 1) if plan_stats.get(
                'total_days', 1) > 0 else 0

            # 计算关键时刻中使用计划的比例
            plan_moments = [m for m in key_moments if m.get('used_plan', False)]
            plan_moment_percent = round((len(plan_moments) / len(key_moments) * 100), 1) if key_moments else 0

            # 构建时间信息
            first_record = None
            last_record = None
            if key_moments:
                first_record = key_moments[0]['date'] if key_moments else ""
                last_record = key_moments[-1]['date'] if key_moments else ""

            prompt = f"""# 减肥成功历程总结

## 用户基础信息
- 昵称：{nickname}
- 身高：{height}cm
- 起始体重：{initial_weight}kg
- 当前体重：{current_weight}kg
- 目标体重：{target_weight}kg
- 减重成果：{total_loss}kg（恭喜达成目标！🎉）
- 记录周期：{first_record} 至 {last_record}

## 用户的卓越贡献（突出用户努力）
### 🍽️ 饮食坚持度
- 早餐按时吃：{breakfast_rate}%（说明你很有自律性！）
- 午餐按时吃：{meal_stats.get('午餐', {}).get('percent', 0)}%
- 晚餐按时吃：{meal_stats.get('晚餐', {}).get('percent', 0)}%

### 💧 饮水习惯养成
- 平均每日喝水：{drink_average}杯
- 达到目标天数：{daily_habits.get('drink_stats', {}).get('days_met_goal', 0)}天（你的坚持让身体更健康！）

### 🏃 运动坚持成果
- 运动天数比例：{exercise_percent}%（这是你努力的直接体现！）
- 总运动天数：{daily_habits.get('exercise_stats', {}).get('exercise_days', 0)}天

### 📋 计划执行情况（用户的执行力）
- 使用健康计划天数：{planned_days}天
- 计划使用率：{plan_usage_rate}%（说明你非常重视科学方法！）
- 关键时刻使用计划比例：{plan_moment_percent}%（在重要时刻选择了科学指导）

## 健康规划支持数据
### 🎯 个性化规划服务
- 为你量身定制饮食计划：{food_plans_count}次
- 为你制定专属运动方案：{exercise_plans_count}次
- AI智能生成个性化计划：{ai_generated_plans}次

### ⚠️ 克服的健康挑战
- 遇到健康问题：{daily_habits.get('health_stats', {}).get('total_factors', 0)}次
- 其中：受伤{daily_habits.get('health_stats', {}).get('injury_days', 0)}天，生病{daily_habits.get('health_stats', {}).get('illness_days', 0)}天，情绪问题{daily_habits.get('health_stats', {}).get('emotion_days', 0)}天
- **特别表扬**：你成功地克服了这些挑战，展现了强大的毅力！

## 关键时刻回顾（用户的成长轨迹）
{self._format_key_moments_for_prompt(key_moments)}

## 请生成一份温暖且专业的减肥成功总结报告，要求：

### 第一部分：热烈祝贺与成果肯定
- 用最热烈的语言祝贺{nickname}达成目标
- 强调{total_loss}kg减重成果的来之不易
- 突出这是**用户自身努力**的成果

### 第二部分：用户贡献详细回顾（重点！）
- 详细列举用户的具体贡献：
  1. 饮食自律：每天坚持按时吃饭
  2. 运动坚持：{exercise_percent}%的运动天数
  3. 计划执行：{plan_usage_rate}%的计划使用率
  4. 饮水习惯：平均每天{drink_average}杯水
- 用具体数字证明用户的努力

### 第三部分：健康支持系统的作用（含蓄表达）
- 提到"科学规划"、"个性化方案"、"健康指导"等概念
- 含蓄地暗示"在健康工具的辅助下"、"结合科学方法"
- **不要直接说"小助手"，而是用"健康管理系统"、"科学工具"等词汇**
- 强调"用户善用工具"的智慧

### 第四部分：防反弹详细指南
- 基于用户习惯提供个性化维持建议
- 饮食：如何维持现有好习惯
- 运动：适合长期坚持的方案
- 监控：体重波动应对策略
- 心理：如何保持积极心态

### 第五部分：未来展望与鼓励
- 强调这是健康生活的新起点
- 鼓励继续保持良好习惯
- 表达对未来健康生活的期待

## 写作要求：
- **语气**：温暖、亲切、充满敬意和骄傲
- **角度**：以教练为学员感到骄傲的口吻
- **重点**：80%篇幅讲用户贡献，20%含蓄提到工具辅助
- **技巧**：用"我们一起"、"你的智慧在于"等句式暗示合作
- **长度**：600-800字
- **关键词**：避免"减肥"，用"健康管理"、"体重维持"、"健康生活" """

            # 调用大模型
            response = self.client.chat.completions.create(
                model="qwen-turbo",
                messages=[
                    {"role": "system", "content": """你是一位资深健康教练，擅长用温暖而专业的方式总结用户的健康旅程。
                    你的特点是：
                    1. 极度尊重和强调用户的自身努力
                    2. 含蓄地提到科学工具的支持作用
                    3. 用具体数据证明用户的成就
                    4. 给予真诚的赞美和专业的指导"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1800
            )

            summary = response.choices[0].message.content.strip()
            return summary

        except Exception as e:
            logging.error(f"生成总结失败: {e}")
            return self._generate_fallback_summary(nickname, total_loss, food_plans_count, exercise_plans_count)

    def _format_key_moments_for_prompt(self, key_moments: List[Dict[str, Any]]) -> str:
        """为提示词格式化关键时刻"""
        if not key_moments:
            return "暂无记录的关键时刻"

        formatted = ""
        for moment in key_moments:
            date = moment.get('date', '')
            summary = moment.get('summary', '')
            event_type = moment.get('event_type', '')
            event_desc = moment.get('event_desc', '')
            used_plan = moment.get('used_plan', False)

            plan_note = "（使用了科学规划）" if used_plan else "（自主坚持）"

            if summary:
                formatted += f"- {date} [{event_type}]：{summary}{plan_note}\n"
            elif event_desc:
                formatted += f"- {date} [{event_type}]：{event_desc}{plan_note}\n"

        return formatted

    def _generate_fallback_summary(self, nickname: str, total_loss: float,
                                   food_plans_count: int, exercise_plans_count: int) -> str:
        """备用总结（如果AI生成失败）"""
        return f"""🎉🎉🎉 热烈祝贺{nickname}成功达成健康目标！

## 🌟 你的辉煌成就
成功减重{total_loss}kg！这是你**每天坚持**的结果，每一个数字背后都是你的汗水和决心。

## 📊 你的卓越贡献
在整个旅程中，你展现了非凡的自律：
- **饮食自律**：坚持规律三餐，养成了健康的饮食习惯
- **运动坚持**：用行动证明了"坚持就是力量"
- **计划执行**：认真对待每一次健康规划
- **饮水习惯**：让充足饮水成为生活的一部分

## 🎯 科学规划的辅助
在这个过程中：
- 你接受了{exercise_plans_count}次专属运动方案指导
- 你参考了{food_plans_count}次个性化饮食建议
- 你展现了善用科学工具的智慧

## 💪 防反弹关键策略
1. **持续监控**：每周称重1-2次
2. **习惯维持**：继续保持现有的好习惯
3. **适度调整**：根据生活变化微调饮食和运动
4. **心态建设**：相信自己可以长期保持

## 🌈 新的健康生活开始
这不是结束，而是更健康、更自信的生活开始！你已经掌握了健康生活的秘诀，这是你最宝贵的财富。

为你感到无比骄傲！继续闪耀！✨

---
*备注：此总结基于你的健康记录数据分析生成*
*包含：{exercise_plans_count}次运动规划 + {food_plans_count}次饮食规划*
"""

    def check_and_generate_summary(self, new_weight: float) -> Optional[str]:
        """
        检查是否达到目标并生成总结

        Args:
            new_weight: 用户刚刚更新的体重

        Returns:
            生成的总结文本，如果未达到目标则返回None
        """
        try:
            # 1. 加载用户档案
            user_profile = self.load_user_profile()
            if not user_profile:
                logging.info("未找到用户档案")
                return None

            # 2. 检查是否达到目标
            target_weight = user_profile.get('target_weight_kg', 0)
            if target_weight <= 0:
                logging.info("未设置目标体重")
                return None

            # 3. 判断是否达到目标
            if new_weight > target_weight:
                logging.info(f"当前体重{new_weight}kg，目标{target_weight}kg，尚未达到目标")
                return None

            # 4. 达到目标！开始生成总结
            print(f"\n🎯 恭喜！已达到目标体重！开始分析你的减肥历程...")
            print("📊 正在统计你的健康数据...")

            # 5. 加载所有数据
            daily_records = self.load_all_daily_records()
            if not daily_records:
                logging.warning("未找到每日记录，只能生成简单总结")

            # 6. 分析数据
            print("🔍 分析你的每日习惯和坚持情况...")
            weight_progress = self.calculate_weight_progress(user_profile, daily_records)
            daily_habits = self.analyze_daily_habits(daily_records)
            key_moments = self.extract_key_moments(daily_records)

            # 7. 显示用户贡献统计
            plan_stats = daily_habits.get('plan_stats', {})
            print(f"\n📈 你的坚持数据统计：")
            print(f"   • 计划使用天数：{plan_stats.get('planned_days', 0)}天")
            print(f"   • 饮食规划次数：{plan_stats.get('food_plans_count', 0)}次")
            print(f"   • 运动规划次数：{plan_stats.get('exercise_plans_count', 0)}次")
            print(f"   • 运动坚持比例：{daily_habits.get('exercise_stats', {}).get('exercise_percent', 0)}%")

            # 8. 生成AI总结
            print("🤖 正在为你生成个性化总结报告...")
            summary = self.generate_journey_summary(
                user_profile,
                weight_progress,
                daily_habits,
                key_moments
            )

            # 9. 保存总结到文件（可选）
            self._save_summary_to_file(summary, user_profile, daily_habits)

            return summary

        except Exception as e:
            logging.error(f"生成减肥总结失败: {e}")
            return None

    def _save_summary_to_file(self, summary: str, user_profile: Dict[str, Any],
                              daily_habits: Dict[str, Any]):
        """保存总结到文件，包含详细统计数据"""
        try:
            summary_dir = "weight_loss_summaries"
            if not os.path.exists(summary_dir):
                os.makedirs(summary_dir)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nickname = user_profile.get('nickname', 'user').replace('/', '_')
            filename = f"{summary_dir}/{nickname}_减肥成功总结_{timestamp}.txt"

            # 获取统计数据
            plan_stats = daily_habits.get('plan_stats', {})
            meal_stats = daily_habits.get('meal_stats', {})
            exercise_stats = daily_habits.get('exercise_stats', {})
            drink_stats = daily_habits.get('drink_stats', {})

            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("🎉 减肥成功历程总结报告 🎉\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"用户昵称：{nickname}\n")
                f.write(f"当前体重：{user_profile.get('current_weight_kg', 0)}kg\n")
                f.write(f"目标体重：{user_profile.get('target_weight_kg', 0)}kg\n")
                f.write(
                    f"减重成果：{user_profile.get('initial_weight_kg', 0) - user_profile.get('current_weight_kg', 0)}kg\n")
                f.write("\n" + "-" * 70 + "\n")
                f.write("📊 用户坚持数据统计\n")
                f.write("-" * 70 + "\n")
                f.write(f"• 健康计划使用天数：{plan_stats.get('planned_days', 0)}天\n")
                f.write(f"• 饮食规划接受次数：{plan_stats.get('food_plans_count', 0)}次\n")
                f.write(f"• 运动方案执行次数：{plan_stats.get('exercise_plans_count', 0)}次\n")
                f.write(f"• 早餐坚持比例：{meal_stats.get('早餐', {}).get('percent', 0)}%\n")
                f.write(f"• 运动天数比例：{exercise_stats.get('exercise_percent', 0)}%\n")
                f.write(f"• 平均每日饮水：{drink_stats.get('average_cups', 0)}杯\n")
                f.write(f"• 计划使用率：{plan_stats.get('plan_follow_rate', 0)}%\n")
                f.write("\n" + "=" * 70 + "\n\n")
                f.write(summary)

            print(f"📄 详细总结报告已保存到：{filename}")
            print("💡 你可以随时查看这份报告，回顾自己的健康旅程！")

        except Exception as e:
            logging.error(f"保存总结文件失败: {e}")

    def calculate_total_days(self, user_profile: Dict[str, Any], daily_records: List[Dict[str, Any]]) -> int:
        """计算从开始到现在的总天数"""
        try:
            if not daily_records:
                return 0

            if user_profile is None:
                # 如果没有用户档案，从文件日期计算
                return self._calculate_days_from_records(daily_records)

            # 方法1：如果有用户档案创建日期
            if user_profile:
                creation_date_str = user_profile.get('creation_date', '')
                if creation_date_str:
                    try:
                        creation_date = datetime.datetime.strptime(creation_date_str, "%Y-%m-%d")
                        today = datetime.datetime.now()
                        total_days = (today - creation_date).days + 1
                        return max(1, total_days)
                    except:
                        pass

            # 方法2：从文件日期计算
            dates = []
            for record in daily_records:
                date_str = record.get('date', '')
                if date_str:
                    try:
                        dates.append(datetime.datetime.strptime(date_str, "%Y-%m-%d"))
                    except:
                        continue

            if dates:
                earliest = min(dates)
                latest = max(dates)
                return (latest - earliest).days + 1

            # 方法3：备用方案
            return len(daily_records)

        except Exception as e:
            logging.error(f"计算总天数失败: {e}")
            return len(daily_records)  # 返回文档数量作为备用

    def _calculate_days_from_records(self, daily_records: List[Dict[str, Any]]) -> int:
        """从记录文件中计算天数"""
        try:
            dates = []
            for record in daily_records:
                date_str = record.get('date', '')
                if date_str:
                    try:
                        dates.append(datetime.datetime.strptime(date_str, "%Y-%m-%d"))
                    except:
                        continue

            if dates:
                earliest = min(dates)
                latest = max(dates)
                return (latest - earliest).days + 1

            return len(daily_records)
        except Exception as e:
            logging.error(f"从记录计算天数失败: {e}")
            return len(daily_records)


# 使用示例
if __name__ == "__main__":
    # 测试代码
    from openai import OpenAI

    # 初始化客户端（需要传入实际的API key）
    client = OpenAI(
        api_key="your-api-key",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    analyzer = WeightLossJourneyAnalyzer(client)

    # 测试生成总结
    test_weight = 60.5  # 假设用户刚刚更新到这个体重
    summary = analyzer.check_and_generate_summary(test_weight)

    if summary:
        print("\n" + "=" * 80)
        print("🎉 你的减肥成功总结报告 🎉")
        print("=" * 80)
        print(summary)
        print("=" * 80)
    else:
        print("未达到目标体重或生成失败")


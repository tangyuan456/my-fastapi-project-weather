"""
运动相关函数模块
负责处理运动状态的记录、卡路里计算和多次运动累积
"""

import datetime
import re
import json
from typing import Dict, Any, Optional, List, Tuple


class ExerciseFunctions:
    """运动相关功能类"""

    def __init__(self, daily_recorder, user_profile: Dict[str, Any] = None):
        """
        初始化运动功能

        Args:
            daily_recorder: DailyHealthRecorder实例
            user_profile: 用户档案数据（可选）
        """
        self.recorder = daily_recorder
        self.user_profile = user_profile

        # 运动卡路里数据库（每单位消耗卡路里）
        self.exercise_calories_db = {
            "跑步": {
                "calories_per_km": 65,  # 每公里消耗卡路里
                "calories_per_min": 10,  # 每分钟消耗卡路里
                "keywords": ["跑步", "慢跑", "快跑", "jog", "run", "晨跑", "夜跑"]
            },
            "步行": {
                "calories_per_km": 50,
                "calories_per_min": 5,
                "keywords": ["走路", "步行", "散步", "walk", "健走", "快走"]
            },
            "骑行": {
                "calories_per_km": 35,
                "calories_per_min": 8,
                "keywords": ["骑车", "骑行", "自行车", "bike", "cycling", "单车"]
            },
            "游泳": {
                "calories_per_km": 100,
                "calories_per_min": 12,
                "keywords": ["游泳", "swim", "蛙泳", "自由泳", "蝶泳"]
            },
            "跳绳": {
                "calories_per_km": 0,
                "calories_per_min": 15,
                "keywords": ["跳绳", "跳神", "rope", "skipping"]
            },
            "瑜伽": {
                "calories_per_km": 0,
                "calories_per_min": 4,
                "keywords": ["瑜伽", "拉伸", "yoga", "普拉提", "冥想"]
            },
            "健身": {
                "calories_per_km": 0,
                "calories_per_min": 8,
                "keywords": ["健身", "举铁", "力量训练", "gym", "workout", "器械"]
            },
            "羽毛球": {
                "calories_per_km": 0,
                "calories_per_min": 10,
                "keywords": ["羽毛球", "badminton", "羽球"]
            },
            "篮球": {
                "calories_per_km": 0,
                "calories_per_min": 12,
                "keywords": ["篮球", "basketball"]
            },
            "足球": {
                "calories_per_km": 0,
                "calories_per_min": 12,
                "keywords": ["足球", "soccer", "football"]
            }
        }

    # ==================== 工具1：更新运动状态 ====================

    def update_exercise_status(self, user_input: str, exercise_type: str = "auto") -> dict:
        """
        工具1：更新运动状态（将"没运动"改为"运动了"）

        Args:
            user_input: 用户描述运动情况的文本
            exercise_type: 运动类型（可选）

        Returns:
            更新结果，可能包含追问问题
        """
        try:
            # 检查是否有recorder对象
            if not hasattr(self, 'recorder'):
                return {
                    "success": False,
                    "message": "❌ 系统错误：找不到记录器"
                }

            # 分析用户输入，判断是否需要追问
            analysis = self._analyze_exercise_input_with_context(user_input)

            # 如果需要追问，返回追问问题
            if analysis.get("needs_clarification", False):
                return {
                    "success": False,
                    "needs_clarification": True,
                    "message": "为了准确记录您的运动，请补充一些信息：",
                    "questions": analysis.get("clarification_questions", []),
                    "suggestion": "请回答上述问题，我会为您详细记录这次运动。",
                    "is_followup": analysis.get("is_followup", False)
                }

            should_calculate_now = False
            if not analysis.get("needs_clarification", False):
                ex_type = analysis.get("detected_type", "其他")
                if ex_type in ["跳绳", "瑜伽", "健身", "羽毛球", "篮球", "足球"] and analysis.get("duration_min"):
                    should_calculate_now = True  # 有时间信息的时长类运动
                elif ex_type in ["跑步", "步行", "骑行", "游泳"] and analysis.get("distance_km"):
                    should_calculate_now = True  # 有距离信息的距离类运动
                elif ex_type != "其他" and (analysis.get("duration_min") or analysis.get("distance_km")):
                    should_calculate_now = True  # 有其他完整信息

            # 加载今日记录
            today_data = self.recorder.load_today_record()

            # 获取当前运动状态
            current_exercise_status = today_data.get("运动状态", ("没运动", ""))
            current_status_text = current_exercise_status[0] if isinstance(current_exercise_status,
                                                                           tuple) else current_exercise_status

            # 如果当前状态是"没运动"，改为"运动了"
            if current_status_text == "没运动":
                # 第一次运动，初始化为空列表
                exercise_records = []
                status_text = "运动了"
            else:
                # 已经有运动记录，保持"运动了"状态
                status_text = "运动了"
                # 获取已有的运动记录
                if isinstance(current_exercise_status, tuple) and len(current_exercise_status) > 1:
                    records_data = current_exercise_status[1]
                    if isinstance(records_data, list):
                        exercise_records = records_data
                    elif isinstance(records_data, dict):
                        # 如果是旧的单个记录格式，转换为列表
                        exercise_records = [records_data]
                    else:
                        exercise_records = []
                else:
                    exercise_records = []

            # 创建新的运动记录（暂不包含卡路里，等第二个工具计算）
            new_record = {
                "description": user_input,
                "exercise_type": analysis.get("detected_type", "其他"),
                "timestamp": datetime.datetime.now().isoformat(),
                "record_status": "已计算卡路里" if should_calculate_now else "待计算卡路里"  # 标记需要计算卡路里
            }

            # 如果有分析出的距离或时间，也记录下来
            if analysis.get("distance_km"):
                new_record["distance_km"] = analysis["distance_km"]
            if analysis.get("duration_min"):
                new_record["duration_min"] = analysis["duration_min"]

            #如果信息完整，直接计算卡路里并更新记录
            if should_calculate_now:
                calories_result = self._calculate_calories_from_analysis(analysis)
                if calories_result.get("success", False):
                    new_record.update({
                        "calories_burned": calories_result["total_calories"],
                        "calculation_method": calories_result.get("calculation_method", "估算"),
                        "record_status": "已计算卡路里",
                        "calories_calculated_at": datetime.datetime.now().isoformat()
                    })

            # 将新记录添加到列表前面（最新的在前面）
            exercise_records.insert(0, new_record)

            # 更新运动状态
            today_data["运动状态"] = (status_text, exercise_records)

            # 保存记录
            success = self.recorder.save_today_record(today_data)

            if success:
                response = {
                    "success": True,
                    "message": "✅ 已记录您的运动！" + (
                        "并计算了消耗的卡路里。" if should_calculate_now else "现在为您计算消耗的卡路里..."),
                    "exercise_type": analysis.get("detected_type", "未知"),
                }

                if should_calculate_now:
                    # 如果已经计算了卡路里，返回详细信息
                    total_calories = self._calculate_today_total_calories(exercise_records)
                    response.update({
                        "needs_calorie_calculation": False,
                        "calories_burned": new_record.get("calories_burned", 0),
                        "calculation_method": new_record.get("calculation_method", "估算"),
                        "today_total_calories": total_calories
                    })
                else:
                    # 如果需要单独计算卡路里
                    response.update({
                        "needs_calorie_calculation": True,
                        "record_index": 0,
                        "user_input": user_input
                    })

                return response
            else:
                return {
                    "success": False,
                    "message": "❌ 保存运动记录失败"
                }

        except Exception as e:
            print(f"❌ 更新运动状态失败: {e}")
            return {
                "success": False,
                "message": f"❌ 更新运动状态失败：{str(e)}"
            }

    # ==================== 工具2：计算运动卡路里 ====================

    def calculate_exercise_calories(self, user_input: str, exercise_type: str = "auto",
                                    record_index: int = 0) -> dict:
        """
        工具2：计算运动消耗的卡路里

        Args:
            user_input: 用户描述（可能是补充信息）
            exercise_type: 运动类型
            record_index: 要计算的记录索引（0表示最新记录）

        Returns:
            计算结果，可能包含追问问题
        """
        try:
            # 检查是否有recorder对象
            if not hasattr(self, 'recorder'):
                return {
                    "success": False,
                    "message": "❌ 系统错误：找不到记录器"
                }

            # 加载今日记录
            today_data = self.recorder.load_today_record()
            exercise_status = today_data.get("运动状态", ("没运动", ""))

            # 检查是否有运动记录
            if exercise_status[0] != "运动了":
                return {
                    "success": False,
                    "message": "❌ 今天还没有运动记录"
                }

            # 获取运动记录列表
            exercise_records = []
            if isinstance(exercise_status, tuple) and len(exercise_status) > 1:
                records_data = exercise_status[1]
                if isinstance(records_data, list):
                    exercise_records = records_data
                elif isinstance(records_data, dict):
                    exercise_records = [records_data]

            if not exercise_records or record_index >= len(exercise_records):
                return {
                    "success": False,
                    "message": "❌ 找不到指定的运动记录"
                }

            # 获取要计算的记录
            target_record = exercise_records[record_index]

            # 分析用户输入（可能是补充信息）
            analysis = self._analyze_exercise_input_with_context(user_input, target_record.get("description", ""))

            # 如果需要追问，返回追问问题
            if analysis.get("needs_clarification", False):
                return {
                    "success": False,
                    "needs_clarification": True,
                    "message": "为了准确计算卡路里，请补充运动信息：",
                    "questions": analysis.get("clarification_questions", []),
                    "suggestion": "请回答上述问题，我会为您计算消耗的卡路里。",
                    "record_index": record_index,
                    "is_followup": analysis.get("is_followup", False)
                }

            # 计算卡路里
            calories_result = self._calculate_calories_from_analysis(analysis)

            if not calories_result.get("success", False):
                return calories_result

            # 更新记录中的卡路里信息
            target_record.update({
                "calories_burned": calories_result["total_calories"],
                "distance_km": analysis.get("distance_km", target_record.get("distance_km")),
                "duration_min": analysis.get("duration_min", target_record.get("duration_min")),
                "exercise_type": analysis.get("detected_type", target_record.get("exercise_type")),
                "calculation_method": calories_result.get("calculation_method", "估算"),
                "record_status": "已计算卡路里",
                "calories_calculated_at": datetime.datetime.now().isoformat()
            })

            # 更新记录列表
            exercise_records[record_index] = target_record
            today_data["运动状态"] = ("运动了", exercise_records)

            # 保存更新后的记录
            success = self.recorder.save_today_record(today_data)

            if success:
                # 构建详细回复
                response = {
                    "success": True,
                    "message": f"🔥 运动卡路里计算完成！",
                    "total_calories": calories_result["total_calories"],
                    "exercise_type": analysis.get("detected_type", "未知"),
                    "calculation_method": calories_result.get("calculation_method", "估算"),
                    "explanation": calories_result.get("explanation", ""),
                    "today_total": self._calculate_today_total_calories(exercise_records)
                }

                return response
            else:
                return {
                    "success": False,
                    "message": "❌ 保存卡路里计算结果失败"
                }

        except Exception as e:
            print(f"❌ 计算运动卡路里失败: {e}")
            return {
                "success": False,
                "message": f"❌ 计算卡路里失败：{str(e)}"
            }

    # ==================== 辅助函数 ====================
    def _get_recent_exercise_context(self, limit: int = 10) -> Optional[str]:
        """
        获取最近的与运动相关的对话上下文

        Args:
            limit: 检查最近多少条记录

        Returns:
            最近的运动相关输入文本，如果没有返回None
        """
        try:
            # 获取最近的对话历史
            recent_history = self.recorder.get_daily_history(limit)

            # 从最近的记录开始查找运动相关的对话
            for i in range(len(recent_history) - 1, 0, -1):
                if recent_history[i].get("role") == "assistant":
                    content = recent_history[i].get("content", "").lower()
                    # 检查是否是运动相关的追问
                    if any(word in content for word in
                           ["运动", "跑步", "游泳", "健身", "距离", "时间", "分钟", "公里"]):
                        # 往前找用户的回复
                        for j in range(i - 1, -1, -1):
                            if recent_history[j].get("role") == "user":
                                previous_input = recent_history[j].get("content", "")
                                # 检查是否是运动描述
                                if any(word in previous_input for word in ["运动", "跑", "游", "健", "练", "动"]):
                                    return previous_input
                        break
            return None

        except Exception as e:
            print(f"❌ 获取运动上下文失败: {e}")
            return None

    def _analyze_exercise_input_with_context(self, user_input: str) -> Dict[str, Any]:
        """
        带上下文的运动输入分析

        Args:
            user_input: 当前用户输入

        Returns:
            分析结果
        """
        # 获取上下文
        previous_input = self._get_recent_exercise_context()
        print(f"🔍 [运动分析] 找到上下文输入：{previous_input}")

        # 判断当前输入是否是补充信息
        is_followup = False
        if previous_input:
            # 检查当前输入是否是补充信息
            is_followup = any(
                word in user_input for word in ["大概", "大约", "左右", "分钟", "小时", "公里", "km", "min", "h"]
            ) or any(word in user_input for word in ["补充", "还有", "另外", "加上"])

        # 合并输入
        if is_followup and previous_input:
            # 如果是补充信息，合并两次输入
            combined_input = f"{previous_input}。补充：{user_input}"
            print(f"🔍 [运动分析] 合并上下文：{combined_input}")
        else:
            combined_input = user_input

        # 使用合并后的输入进行分析
        return self._analyze_exercise_input(combined_input, is_followup)

    def _analyze_exercise_input(self, full_input: str, is_followup: bool = False) -> Dict[str, Any]:
        """
        分析运动输入，提取信息并判断是否需要追问

        Args:
            full_input: 完整的输入文本
            is_followup: 是否是补充信息

        Returns:
            分析结果
        """
        # 检测运动类型
        detected_type = "其他"
        for ex_type, data in self.exercise_calories_db.items():
            for keyword in data["keywords"]:
                if keyword in full_input.lower():
                    detected_type = ex_type
                    break
            if detected_type != "其他":
                break

        # 提取距离（公里）
        distance_km = None
        distance_patterns = [
            (r'(\d+(?:\.\d+)?)\s*公里', lambda x: float(x)),
            (r'(\d+(?:\.\d+)?)\s*km', lambda x: float(x)),
            (r'(\d+)\s*千米', lambda x: float(x)),
            (r'跑了\s*(\d+(?:\.\d+)?)', lambda x: float(x)),  # 简单匹配"跑了10"
        ]

        for pattern, converter in distance_patterns:
            match = re.search(pattern, full_input.lower())
            if match:
                try:
                    distance_km = converter(match.group(1))
                    break
                except:
                    pass

        # 提取时间（分钟）
        duration_min = None
        time_patterns = [
            (r'(\d+)\s*分钟', lambda x: int(x)),
            (r'(\d+)\s*min', lambda x: int(x)),
            (r'(\d+)\s*小时', lambda x: int(x) * 60),
            (r'(\d+)\s*h', lambda x: int(x) * 60),
            (r'半个?小时', lambda x: 30),
            (r'(\d+)\s*刻钟', lambda x: int(x) * 15),
        ]

        for pattern, converter in time_patterns:
            match = re.search(pattern, full_input.lower())
            if match:
                try:
                    duration_min = converter(match.group(1) if match.group(1) else "1")
                    break
                except:
                    pass

        # 判断是否需要追问
        needs_clarification = False
        clarification_questions = []

        # 规则0：如果是补充信息，但信息仍然不足
        if is_followup:
            if detected_type == "其他":
                needs_clarification = True
                clarification_questions.append("您进行的是什么类型的运动？")
            elif detected_type in ["跑步", "步行", "骑行", "游泳"] and distance_km is None:
                needs_clarification = True
                clarification_questions.append(f"您{detected_type}了多远距离？（如：5公里）")
            elif detected_type in ["跳绳", "瑜伽", "健身", "羽毛球", "篮球", "足球"] and duration_min is None:
                needs_clarification = True
                clarification_questions.append(f"您{detected_type}了多长时间？（如：30分钟）")

        # 规则1：如果没有明确运动类型
        if detected_type == "其他" and not any(word in full_input for word in ["运动", "锻炼", "健身"]):
            needs_clarification = True
            clarification_questions.append("您进行的是什么类型的运动？（如：跑步、游泳、健身等）")

        # 规则2：对于需要距离计算的运动（如跑步、步行、骑行），但没有距离信息
        elif detected_type in ["跑步", "步行", "骑行", "游泳"] and distance_km is None:
            needs_clarification = True
            clarification_questions.append(f"您{detected_type}了多远距离？（如：5公里、3km等）")

        # 规则3：对于按时间计算的运动（如跳绳、瑜伽、健身），但没有时间信息
        elif detected_type in ["跳绳", "瑜伽", "健身", "羽毛球", "篮球", "足球"] and duration_min is None:
            needs_clarification = True
            clarification_questions.append(f"您{detected_type}了多长时间？（如：30分钟、1小时等）")

        # 规则4：如果用户描述过于模糊
        elif len(full_input.strip()) < 4 and not is_followup:  # 太短的描述
            needs_clarification = True
            clarification_questions.append("能详细描述一下您的运动情况吗？")

        return {
            "detected_type": detected_type,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "full_input": full_input,
            "needs_clarification": needs_clarification,
            "clarification_questions": clarification_questions,
            "is_followup": is_followup
        }

    def _calculate_calories_from_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """根据分析结果计算卡路里"""
        ex_type = analysis.get("detected_type", "其他")

        if ex_type not in self.exercise_calories_db:
            return {
                "success": False,
                "message": f"❌ 不支持的运动类型：{ex_type}"
            }

        ex_data = self.exercise_calories_db[ex_type]
        total_calories = 0
        calculation_method = ""
        explanation = ""

        # 方法1：按距离计算（优先）
        distance_km = analysis.get("distance_km")
        if distance_km and ex_data["calories_per_km"] > 0:
            total_calories = int(distance_km * ex_data["calories_per_km"])
            calculation_method = "按距离计算"
            explanation = f"{ex_type}{distance_km}公里 × {ex_data['calories_per_km']}卡/公里"

        # 方法2：按时间计算
        elif analysis.get("duration_min"):
            duration_min = analysis["duration_min"]
            total_calories = int(duration_min * ex_data["calories_per_min"])
            calculation_method = "按时间计算"
            explanation = f"{ex_type}{duration_min}分钟 × {ex_data['calories_per_min']}卡/分钟"

        # 方法3：估算（当信息不足时）
        else:
            # 根据运动类型给一个估算值
            estimated_values = {
                "跑步": 300, "步行": 150, "骑行": 200, "游泳": 250,
                "跳绳": 200, "瑜伽": 100, "健身": 250, "羽毛球": 180,
                "篮球": 300, "足球": 350, "其他": 150
            }
            total_calories = estimated_values.get(ex_type, 150)
            calculation_method = "估算"
            explanation = f"基于{ex_type}的平均消耗估算"

        return {
            "success": True,
            "total_calories": total_calories,
            "calculation_method": calculation_method,
            "explanation": explanation,
            "exercise_type": ex_type
        }

    def _calculate_today_total_calories(self, exercise_records: List[Dict]) -> int:
        """计算今天运动消耗的总卡路里"""
        total = 0
        for record in exercise_records:
            if record.get("calories_burned"):
                total += record["calories_burned"]
        return total

    def get_today_exercise_summary(self) -> Dict[str, Any]:
        """获取今日运动总结"""
        try:
            today_data = self.recorder.load_today_record()
            exercise_status = today_data.get("运动状态", ("没运动", ""))

            if isinstance(exercise_status, tuple):
                status_text = exercise_status[0]
                records_data = exercise_status[1] if len(exercise_status) > 1 else []
            else:
                status_text = exercise_status
                records_data = []

            # 处理记录数据
            exercise_records = []
            if isinstance(records_data, list):
                exercise_records = records_data
            elif isinstance(records_data, dict):
                exercise_records = [records_data]

            summary = {
                "status": status_text,
                "has_exercised": status_text == "运动了",
                "total_records": len(exercise_records),
                "total_calories": self._calculate_today_total_calories(exercise_records),
                "records": exercise_records[:5]  # 只返回最近的5条记录
            }

            return summary

        except Exception as e:
            print(f"❌ 获取今日运动总结失败: {e}")
            return {"status": "获取失败", "has_exercised": False, "total_records": 0}
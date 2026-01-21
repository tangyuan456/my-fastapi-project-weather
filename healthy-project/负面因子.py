"""
负面因子自动检测与处理模块
用于自动识别用户输入中的负面因子并记录
"""

import re
import json
import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """严重程度枚举"""
    LIGHT = "轻"
    MEDIUM = "中"
    SEVERE = "重"


class FactorType(Enum):
    """负面因子类型枚举"""
    INJURY = "受伤"
    ILLNESS = "生病"
    EMOTION = "情绪"
    FATIGUE = "疲劳"
    OTHER = "其他"


@dataclass
class NegativeFactor:
    """负面因子数据类"""
    type: FactorType
    description: str
    severity: Severity
    should_exercise: bool
    keywords: List[str]
    weight: float  # 0-1之间的权重


class NegativeFactorDetector:
    """负面因子检测器"""

    def __init__(self):
        # 初始化负面因子数据库
        self.factor_database = self._initialize_factor_database()

        # 关键词权重表
        self.keyword_weights = {
            # 受伤相关关键词
            "骨折": 3.0, "断骨": 3.0, "骨裂": 2.5,
            "扭伤": 2.0, "拉伤": 2.0, "挫伤": 2.0,
            "擦伤": 1.0, "刮伤": 1.0, "磕伤": 1.0,
            "割伤": 1.5, "划伤": 1.5,
            "膝盖": 2.0, "脚踝": 2.0, "手腕": 1.5,
            "扭到": 1.8, "摔伤": 2.0, "跌倒": 1.5,

            # 生病相关关键词
            "发烧": 2.0, "感冒": 1.5, "咳嗽": 1.0,
            "头痛": 1.5, "头晕": 1.5, "恶心": 1.8,
            "呕吐": 2.0, "腹泻": 2.0, "腹痛": 1.8,
            "流感": 2.0, "肺炎": 3.0, "感染": 2.5,
            "过敏": 1.5, "气喘": 2.0,

            # 情绪相关关键词
            "难过": 1.5, "伤心": 1.5, "沮丧": 1.5,
            "抑郁": 2.5, "焦虑": 2.0, "压力": 1.8,
            "烦躁": 1.5, "生气": 1.2, "愤怒": 1.5,
            "失落": 1.5, "孤独": 1.8,
            "哭": 1.2, "流泪": 1.2,

            # 疲劳相关关键词
            "累": 1.0, "疲惫": 1.2, "疲劳": 1.2,
            "困": 0.8, "困倦": 0.8, "没精神": 1.5,
            "虚弱": 1.8, "乏力": 1.8,

            # 程度副词
            "很": 0.5, "非常": 0.7, "特别": 0.7,
            "极其": 0.9, "严重": 1.0, "轻微": -0.5,
            "一点": -0.3, "有点": -0.3,
        }

        # 严重程度关键词
        self.severity_keywords = {
            "轻微": Severity.LIGHT,
            "轻度": Severity.LIGHT,
            "一点": Severity.LIGHT,
            "有点": Severity.LIGHT,
            "中度": Severity.MEDIUM,
            "严重": Severity.SEVERE,
            "很严重": Severity.SEVERE,
            "非常严重": Severity.SEVERE,
            "重度": Severity.SEVERE,
        }

        # 否定词（用于降低权重）
        self.negation_words = {"不", "没有", "没", "未", "无", "非"}

    def _initialize_factor_database(self) -> List[NegativeFactor]:
        """初始化负面因子数据库"""
        return [
            # 受伤类
            NegativeFactor(
                type=FactorType.INJURY,
                description="轻伤（擦伤、轻微扭伤等）",
                severity=Severity.LIGHT,
                should_exercise=True,
                keywords=["擦伤", "刮伤", "轻微扭伤", "小伤口"],
                weight=0.3
            ),
            NegativeFactor(
                type=FactorType.INJURY,
                description="中度受伤（拉伤、挫伤等）",
                severity=Severity.MEDIUM,
                should_exercise=False,
                keywords=["扭伤", "拉伤", "挫伤", "割伤", "脚踝", "膝盖"],
                weight=0.6
            ),
            NegativeFactor(
                type=FactorType.INJURY,
                description="重伤（骨折、严重扭伤等）",
                severity=Severity.SEVERE,
                should_exercise=False,
                keywords=["骨折", "断骨", "骨裂", "严重扭伤"],
                weight=0.9
            ),

            # 生病类
            NegativeFactor(
                type=FactorType.ILLNESS,
                description="小病（轻微感冒、咳嗽等）",
                severity=Severity.LIGHT,
                should_exercise=True,
                keywords=["感冒", "咳嗽", "头痛", "轻微"],
                weight=0.3
            ),
            NegativeFactor(
                type=FactorType.ILLNESS,
                description="中度疾病（发烧、流感等）",
                severity=Severity.MEDIUM,
                should_exercise=False,
                keywords=["发烧", "流感", "腹泻", "腹痛"],
                weight=0.7
            ),
            NegativeFactor(
                type=FactorType.ILLNESS,
                description="重病（肺炎、严重感染等）",
                severity=Severity.SEVERE,
                should_exercise=False,
                keywords=["肺炎", "感染", "住院", "手术"],
                weight=0.9
            ),

            # 情绪类
            NegativeFactor(
                type=FactorType.EMOTION,
                description="轻度情绪低落",
                severity=Severity.LIGHT,
                should_exercise=True,  # 轻度运动有助于缓解情绪
                keywords=["难过", "伤心", "沮丧", "失落"],
                weight=0.2
            ),
            NegativeFactor(
                type=FactorType.EMOTION,
                description="中度情绪问题",
                severity=Severity.MEDIUM,
                should_exercise=True,
                keywords=["抑郁", "焦虑", "压力", "烦躁"],
                weight=0.5
            ),
            NegativeFactor(
                type=FactorType.EMOTION,
                description="重度情绪问题",
                severity=Severity.SEVERE,
                should_exercise=False,
                keywords=["严重抑郁", "自杀", "崩溃", "绝望"],
                weight=0.9
            ),

            # 疲劳类
            NegativeFactor(
                type=FactorType.FATIGUE,
                description="轻度疲劳",
                severity=Severity.LIGHT,
                should_exercise=True,
                keywords=["累", "困", "疲惫"],
                weight=0.2
            ),
            NegativeFactor(
                type=FactorType.FATIGUE,
                description="中度疲劳",
                severity=Severity.MEDIUM,
                should_exercise=False,
                keywords=["疲劳", "虚弱", "乏力"],
                weight=0.6
            ),
            NegativeFactor(
                type=FactorType.FATIGUE,
                description="重度疲劳（过度训练等）",
                severity=Severity.SEVERE,
                should_exercise=False,
                keywords=["过度训练", "筋疲力尽", "虚脱"],
                weight=0.8
            ),
        ]

    def detect_negative_factor(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        检测用户输入中的负面因子

        Args:
            user_input: 用户输入文本

        Returns:
            检测到的负面因子信息，或None
        """
        if not user_input or not isinstance(user_input, str):
            return None

        # 转换为小写进行匹配
        input_lower = user_input.lower()

        # 计算总权重
        total_weight = 0.0
        matched_keywords = []

        # 检查关键词
        for keyword, weight in self.keyword_weights.items():
            keyword_lower = keyword.lower()
            if keyword_lower in input_lower:
                # 检查是否有否定词前缀
                has_negation = self._has_negation_before(input_lower, keyword_lower)
                if has_negation:
                    # 有否定词，降低权重
                    total_weight -= weight * 0.5
                else:
                    total_weight += weight
                    matched_keywords.append(keyword)

        # 如果总权重低于阈值，认为没有负面因子
        if total_weight < 0.5:
            return None

        # 检测严重程度
        severity = self._detect_severity(input_lower, total_weight)

        # 确定因子类型
        factor_type = self._determine_factor_type(matched_keywords, input_lower)

        # 判断是否适合运动
        should_exercise = self._should_exercise(factor_type, severity, total_weight)

        # 生成描述
        description = self._generate_description(matched_keywords, input_lower)

        return {
            "detected": True,
            "type": factor_type.value,
            "description": description,
            "severity": severity.value,
            "total_weight": round(total_weight, 2),
            "matched_keywords": matched_keywords,
            "should_exercise": should_exercise,
            "duration_days": 1,  # 默认第1天
            "user_input": user_input,
            "detected_at": datetime.datetime.now().isoformat()
        }

    def _has_negation_before(self, text: str, keyword: str) -> bool:
        """检查关键词前面是否有否定词"""
        try:
            keyword_index = text.find(keyword)
            if keyword_index == -1:
                return False

            # 检查关键词前的几个字符
            start_idx = max(0, keyword_index - 5)
            preceding_text = text[start_idx:keyword_index]

            # 检查是否有否定词
            for negation in self.negation_words:
                if negation in preceding_text:
                    return True

            return False
        except:
            return False

    def _detect_severity(self, text: str, weight: float) -> Severity:
        """检测严重程度"""
        # 首先检查明确的严重程度关键词
        for keyword, severity in self.severity_keywords.items():
            if keyword in text:
                return severity

        # 根据权重判断
        if weight >= 2.5:
            return Severity.SEVERE
        elif weight >= 1.5:
            return Severity.MEDIUM
        else:
            return Severity.LIGHT

    def _determine_factor_type(self, keywords: List[str], text: str) -> FactorType:
        """确定因子类型"""
        # 统计各类关键词出现次数
        type_scores = {
            FactorType.INJURY: 0,
            FactorType.ILLNESS: 0,
            FactorType.EMOTION: 0,
            FactorType.FATIGUE: 0,
            FactorType.OTHER: 0
        }

        # 受伤相关关键词
        injury_words = ["伤", "扭", "拉", "挫", "摔", "跌", "骨折", "骨裂"]
        for word in injury_words:
            if any(word in kw for kw in keywords):
                type_scores[FactorType.INJURY] += 1

        # 生病相关关键词
        illness_words = ["病", "烧", "咳", "吐", "泻", "痛", "晕", "炎", "感染"]
        for word in illness_words:
            if any(word in kw for kw in keywords):
                type_scores[FactorType.ILLNESS] += 1

        # 情绪相关关键词
        emotion_words = ["难过", "伤心", "沮丧", "抑郁", "焦虑", "生气", "愤怒"]
        for word in emotion_words:
            if any(word in kw for kw in keywords):
                type_scores[FactorType.EMOTION] += 1

        # 疲劳相关关键词
        fatigue_words = ["累", "疲惫", "疲劳", "困", "乏", "虚弱"]
        for word in fatigue_words:
            if any(word in kw for kw in keywords):
                type_scores[FactorType.FATIGUE] += 1

        # 找出得分最高的类型
        max_score = 0
        selected_type = FactorType.OTHER

        for factor_type, score in type_scores.items():
            if score > max_score:
                max_score = score
                selected_type = factor_type

        # 如果所有得分都为0，尝试从文本中推断
        if max_score == 0:
            if any(word in text for word in injury_words):
                return FactorType.INJURY
            elif any(word in text for word in illness_words):
                return FactorType.ILLNESS
            elif any(word in text for word in emotion_words):
                return FactorType.EMOTION
            elif any(word in text for word in fatigue_words):
                return FactorType.FATIGUE

        return selected_type

    def _should_exercise(self, factor_type: FactorType, severity: Severity, weight: float) -> bool:
        """判断是否适合运动"""
        # 重度情况都不适合运动
        if severity == Severity.SEVERE:
            return False

        # 根据因子类型和严重程度判断
        if factor_type == FactorType.INJURY:
            # 受伤情况：轻度可以运动，中度不建议
            return severity == Severity.LIGHT

        elif factor_type == FactorType.ILLNESS:
            # 生病情况：轻度感冒可以轻度运动，其他不建议
            if severity == Severity.LIGHT and weight < 1.5:
                return True
            return False

        elif factor_type == FactorType.EMOTION:
            # 情绪问题：轻度中度都可以适当运动
            return severity in [Severity.LIGHT, Severity.MEDIUM]

        elif factor_type == FactorType.FATIGUE:
            # 疲劳情况：轻度可以，中度重度不建议
            return severity == Severity.LIGHT

        else:
            return True  # 其他类型默认可以运动

    def _generate_description(self, keywords: List[str], text: str) -> str:
        """生成描述"""
        if not keywords:
            return "检测到负面情绪或状态"

        # 取最重要的几个关键词
        important_keywords = []
        for kw in keywords:
            if self.keyword_weights.get(kw, 0) > 1.0:
                important_keywords.append(kw)

        if important_keywords:
            description = f"{'、'.join(important_keywords[:3])}相关不适"
        else:
            description = f"{keywords[0]}等相关不适"

        return description


class NegativeFactorManager:
    """负面因子管理器（作为MCP工具使用）"""

    def __init__(self, recorder):
        """
        初始化管理器

        Args:
            recorder: DailyHealthRecorder实例
        """
        self.recorder = recorder
        self.detector = NegativeFactorDetector()

    def analyze_and_record(self, user_input: str) -> Dict[str, Any]:
        """
        分析用户输入并记录负面因子

        Args:
            user_input: 用户输入文本

        Returns:
            处理结果
        """
        try:
            # 1. 检测负面因子
            detection_result = self.detector.detect_negative_factor(user_input)

            if not detection_result or not detection_result["detected"]:
                return {
                    "success": False,
                    "has_negative_factor": False,
                    "message": "未检测到明显的负面因子",
                    "suggestion": "保持良好的状态！"
                }

            print(f"🔍 检测到负面因子: {detection_result}")

            # 2. 检查是否已经有类似的活跃因子
            active_factors = self.recorder.get_active_negative_factors()

            # 查找是否已经有类似的因子（避免重复记录）
            similar_factor = None
            for factor in active_factors:
                if (factor.get("type") == detection_result["type"] and
                        abs(factor.get("severity_level", 1) -
                            self._get_severity_level(detection_result["severity"])) <= 1):
                    similar_factor = factor
                    break

            if similar_factor:
                # 已有类似因子，更新天数
                factor_id = similar_factor.get("id")
                current_duration = similar_factor.get("duration_days", 1)

                success = self.recorder.update_factor_duration(
                    factor_id,
                    current_duration + 1
                )

                if success:
                    return {
                        "success": True,
                        "has_negative_factor": True,
                        "is_new": False,
                        "message": f"检测到您仍在经历{detection_result['type']}问题",
                        "suggestion": f"该问题已持续{current_duration + 1}天，请继续注意休息和治疗",
                        "factor_info": {
                            "id": factor_id,
                            "type": detection_result["type"],
                            "severity": detection_result["severity"],
                            "duration_days": current_duration + 1
                        }
                    }

            # 3. 记录新的负面因子
            success = self.recorder.add_negative_factor(
                factor_type=detection_result["type"],
                description=detection_result["description"],
                severity=detection_result["severity"],
                duration_days=1,
                notes=f"自动检测自用户输入：{user_input[:100]}",
                should_exercise=detection_result["should_exercise"]
            )

            if success:
                # 获取运动能力判断
                exercise_check = self.recorder.can_user_exercise_today()

                # 构建建议
                severity = detection_result["severity"]
                factor_type = detection_result["type"]

                suggestions = []

                if severity == "轻":
                    suggestions.append("问题比较轻微，通常不会影响正常活动")
                    if detection_result["should_exercise"]:
                        suggestions.append("可以进行轻度运动，但要注意感受身体反应")
                    else:
                        suggestions.append("建议暂时休息，让身体恢复")
                elif severity == "中":
                    suggestions.append("问题需要引起注意，建议适当调整活动强度")
                    suggestions.append("如果症状持续或加重，请考虑就医")
                else:  # 重
                    suggestions.append("问题比较严重，建议立即休息")
                    suggestions.append("如果症状严重，请及时就医")

                # 根据因子类型添加特定建议
                if factor_type == "受伤":
                    suggestions.append("受伤部位要注意保护，避免二次伤害")
                elif factor_type == "生病":
                    suggestions.append("多喝水，注意休息，保持营养")
                elif factor_type == "情绪":
                    suggestions.append("情绪问题可以通过运动、社交等方式缓解")

                # 运动建议
                if exercise_check["can_exercise"]:
                    suggestions.append("根据当前状况，可以进行适当的运动")
                else:
                    suggestions.append("根据当前状况，建议暂时避免剧烈运动")

                suggestion_text = "\n".join([f"• {s}" for s in suggestions])

                return {
                    "success": True,
                    "has_negative_factor": True,
                    "is_new": True,
                    "message": f"检测到{detection_result['type']}问题：{detection_result['description']}",
                    "suggestion": f"💡 我的建议：\n{suggestion_text}",
                    "factor_info": detection_result,
                    "exercise_check": exercise_check
                }
            else:
                return {
                    "success": False,
                    "has_negative_factor": True,
                    "message": "检测到负面因子，但记录失败",
                    "suggestion": "请稍后重试或手动记录"
                }

        except Exception as e:
            print(f"❌ 负面因子分析失败: {e}")
            return {
                "success": False,
                "has_negative_factor": False,
                "message": f"分析失败: {str(e)}",
                "suggestion": "请重新描述您的情况"
            }

    def _get_severity_level(self, severity_str: str) -> int:
        """将严重程度字符串转换为数值"""
        severity_map = {"轻": 1, "中": 2, "重": 3}
        return severity_map.get(severity_str, 1)

    def get_daily_summary(self) -> str:
        """获取当日负面因子摘要"""
        return self.recorder.get_factor_impact_summary()

    def mark_recovery(self, factor_id: int = None, recovery_notes: str = "") -> Dict[str, Any]:
        """
        标记负面因子为已康复

        Args:
            factor_id: 因子ID，为None时标记所有活跃因子
            recovery_notes: 康复备注

        Returns:
            处理结果
        """
        try:
            if factor_id is None:
                # 标记所有活跃因子
                active_factors = self.recorder.get_active_negative_factors()
                recovered_count = 0

                for factor in active_factors:
                    factor_id = factor.get("id")
                    if factor_id:
                        success = self.recorder.mark_factor_recovered(
                            factor_id,
                            recovery_notes
                        )
                        if success:
                            recovered_count += 1

                if recovered_count > 0:
                    return {
                        "success": True,
                        "message": f"已标记{recovered_count}个负面因子为已康复！",
                        "suggestion": "恭喜您恢复健康！继续保持良好的生活习惯哦~"
                    }
                else:
                    return {
                        "success": False,
                        "message": "没有找到活跃的负面因子",
                        "suggestion": "您已经处于良好的状态了！"
                    }
            else:
                # 标记指定因子
                success = self.recorder.mark_factor_recovered(
                    factor_id,
                    recovery_notes
                )

                if success:
                    return {
                        "success": True,
                        "message": "已标记该负面因子为已康复！",
                        "suggestion": "恭喜您恢复健康！请继续保持良好的状态"
                    }
                else:
                    return {
                        "success": False,
                        "message": "标记康复失败",
                        "suggestion": "请检查因子ID是否正确"
                    }

        except Exception as e:
            print(f"❌ 标记康复失败: {e}")
            return {
                "success": False,
                "message": f"标记康复失败: {str(e)}",
                "suggestion": "请稍后重试"
            }

    def mark_as_recovered(self, user_input: str = None, factor_id: int = None) -> Dict[str, Any]:
        """
        标记负面因子为已康复

        Args:
            user_input: 用户输入文本（包含康复信息）
            factor_id: 指定要标记的因子ID（可选）

        Returns:
            处理结果
        """
        try:
            # 检查是否有活跃的负面因子
            active_factors = self.recorder.get_active_negative_factors()

            if not active_factors:
                return {
                    "success": False,
                    "message": "没有找到活跃的负面因子需要标记康复",
                    "suggestion": "您已经处于良好的状态了！"
                }

            # 如果没有指定factor_id，根据用户输入选择
            if factor_id is None:
                # 如果只有一个活跃因子，直接标记它
                if len(active_factors) == 1:
                    factor_id = active_factors[0].get("id")
                else:
                    # 多个活跃因子，让用户选择
                    return {
                        "success": False,
                        "needs_clarification": True,
                        "message": "检测到多个活跃的负面因子，请指定要标记康复的是哪一个：",
                        "questions": [
                            f"{i + 1}. {factor.get('type')}：{factor.get('description')}（已持续{factor.get('duration_days')}天）"
                            for i, factor in enumerate(active_factors)
                        ],
                        "suggestion": "请回复对应编号（如：1）来标记特定因子为康复，或回复'全部'标记所有"
                    }

            # 解析用户输入中的康复信息
            recovery_notes = ""
            if user_input:
                # 提取康复相关信息
                recovery_keywords = ["好了", "康复", "痊愈", "恢复", "不疼", "不痛", "没事"]
                for keyword in recovery_keywords:
                    if keyword in user_input:
                        recovery_notes = f"用户报告：{user_input[:100]}"
                        break

            if not recovery_notes:
                recovery_notes = "用户主动标记康复"

            # 调用标记康复
            success = self.recorder.mark_factor_recovered(factor_id, recovery_notes)

            if success:
                # 获取康复后的总结
                summary = self.recorder.get_factor_impact_summary()

                return {
                    "success": True,
                    "message": "✅ 已成功标记该负面因子为已康复！",
                    "summary": summary,
                    "suggestion": "恭喜您恢复健康！请继续保持良好的生活习惯哦~",
                    "recovered_factor_id": factor_id
                }
            else:
                return {
                    "success": False,
                    "message": "标记康复失败，请检查因子ID是否正确",
                    "suggestion": "请稍后重试或联系管理员"
                }

        except Exception as e:
            print(f"❌ 标记康复失败: {e}")
            return {
                "success": False,
                "message": f"标记康复失败: {str(e)}",
                "suggestion": "请稍后重试"
            }

    def check_all_recovered(self) -> Dict[str, Any]:
        """
        检查所有负面因子是否都已康复

        Returns:
            检查结果
        """
        try:
            active_factors = self.recorder.get_active_negative_factors()

            if not active_factors:
                return {
                    "all_recovered": True,
                    "message": "🎉 太棒了！您当前没有任何活跃的负面因子！",
                    "suggestion": "继续保持良好的健康状态！"
                }
            else:
                return {
                    "all_recovered": False,
                    "active_count": len(active_factors),
                    "message": f"⚠️ 您还有{len(active_factors)}个活跃的负面因子需要关注",
                    "factors": active_factors,
                    "suggestion": "可以回复'我好了'或'标记康复'来关闭这些负面因子记录"
                }

        except Exception as e:
            print(f"❌ 检查康复状态失败: {e}")
            return {
                "all_recovered": False,
                "message": f"检查失败: {str(e)}"
            }


# 测试函数
def test_negative_factor_detection():
    """测试负面因子检测"""
    detector = NegativeFactorDetector()

    test_cases = [
        "我今天膝盖扭伤了，好痛啊",
        "我感冒了，有点发烧",
        "心情好难过，什么都不想做",
        "今天好累啊，完全没力气",
        "我骨折了，医生说要休息一个月",
        "我感觉有点抑郁，情绪很低落",
        "只是轻微的擦伤，没关系",
        "我没有生病，只是有点累",
        "今天很开心，没有不舒服"
    ]

    print("🧪 测试负面因子检测...")
    for test_case in test_cases:
        print(f"\n输入: {test_case}")
        result = detector.detect_negative_factor(test_case)
        if result and result["detected"]:
            print(f"  检测到: {result['type']} - {result['description']}")
            print(f"  严重程度: {result['severity']}")
            print(f"  适合运动: {result['should_exercise']}")
        else:
            print("  未检测到负面因子")


if __name__ == "__main__":
    test_negative_factor_detection()
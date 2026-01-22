'''初步设计：
根据用户的回答
没吃:每日记录里的饮食提取，
吃了（输入今日吃了的东西即证明吃了）：饮食更新、热量计算、营养计算、（下一餐菜单更新）
下一稿：
1、判断时间，扫描每日文档中的饮食状态，为0则一直询问吃了吗，
2、用户回答吃了或马上吃，不要理他，询问它吃了什么
3、根据用户的回答，[更新饮食状态、计算热量、计算营养、更换今日菜品]都是要给ai自行调用的工具，可以搞成一个集合
                               |———————|
                                   |
                 在这两个工具中肯定要调用大模型：1先追问详细信息 2计算热量

'''
import datetime
import json
import re
import requests
from typing import Dict, List, Optional, Any
from openai import OpenAI


class DietFunctions:
    """饮食相关功能类"""

    def __init__(self, client: OpenAI = None, api_key: str = None):
        """
        初始化饮食功能

        Args:
            client: OpenAI客户端（用于调用大模型）
            api_key: 通义千问API密钥（可选）
        """
        self.client = client

        # 基础食物数据库（每100克）
        self.base_food_db = {
            "米饭": {"calories": 116, "protein": 2.6, "carbs": 25.9, "fat": 0.3},
            "白米饭": {"calories": 116, "protein": 2.6, "carbs": 25.9, "fat": 0.3},
            "面条": {"calories": 138, "protein": 4.5, "carbs": 28.0, "fat": 0.7},
            "鸡蛋": {"calories": 155, "protein": 13.0, "carbs": 1.1, "fat": 11.0},
            "鸡胸肉": {"calories": 165, "protein": 31.0, "carbs": 0.0, "fat": 3.6},
            "牛肉": {"calories": 250, "protein": 26.0, "carbs": 0.0, "fat": 15.0},
            "猪肉": {"calories": 242, "protein": 27.0, "carbs": 0.0, "fat": 14.0},
            "鱼": {"calories": 130, "protein": 22.0, "carbs": 0.0, "fat": 4.0},
            "苹果": {"calories": 52, "protein": 0.3, "carbs": 13.8, "fat": 0.2},
            "香蕉": {"calories": 89, "protein": 1.1, "carbs": 22.8, "fat": 0.3},
            "牛奶": {"calories": 54, "protein": 3.3, "carbs": 5.0, "fat": 3.2},
            "面包": {"calories": 265, "protein": 9.0, "carbs": 49.0, "fat": 3.2},
            "蔬菜": {"calories": 25, "protein": 2.0, "carbs": 5.0, "fat": 0.5},
            "土豆": {"calories": 77, "protein": 2.0, "carbs": 17.0, "fat": 0.1},
            "豆腐": {"calories": 76, "protein": 8.1, "carbs": 4.2, "fat": 4.8},
            "番茄": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2},
            "鸡肉": {"calories": 165, "protein": 31.0, "carbs": 0.0, "fat": 3.6},
            "虾": {"calories": 85, "protein": 18.0, "carbs": 0.0, "fat": 1.0},
            "玉米": {"calories": 86, "protein": 3.3, "carbs": 19.0, "fat": 1.2},
            "燕麦": {"calories": 389, "protein": 16.9, "carbs": 66.0, "fat": 6.9},
        }

        # 烹饪方式系数
        self.cooking_methods = {
            "蒸": 1.0, "煮": 1.1, "白灼": 1.1,
            "炒": 1.5, "煎": 1.6, "炸": 2.0,
            "烤": 1.3, "红烧": 1.8, "炖": 1.4,
            "凉拌": 1.0, "生吃": 1.0, "清蒸": 1.0,
            "水煮": 1.1, "快炒": 1.5, "油炸": 2.0,
            "烧烤": 1.4, "烩": 1.3
        }

        # 份量估算系数
        self.portion_sizes = {
            "小": 0.7, "小份": 0.7, "少量": 0.7, "一点点": 0.5,
            "中": 1.0, "正常": 1.0, "标准": 1.0, "普通": 1.0,
            "大": 1.3, "大份": 1.3, "大量": 1.3, "很多": 1.5,
            "特大": 1.5, "超大": 1.5
        }

        # 酱料系数
        self.sauce_levels = {
            "少": 0.9, "清淡": 0.9, "无": 0.8, "微": 0.9,
            "正常": 1.0, "标准": 1.0, "适中": 1.0,
            "多": 1.2, "重": 1.3, "加量": 1.2, "浓": 1.2
        }

        # 连锁餐厅常见菜品热量数据库
        self.restaurant_calories = {
            "麦当劳": {
                "巨无霸": 540,
                "麦辣鸡腿堡": 440,
                "薯条(中)": 330,
                "可乐(中)": 150,
                "麦辣鸡翅": 210,
                "麦香鱼": 350
            },
            "肯德基": {
                "香辣鸡腿堡": 450,
                "新奥尔良烤鸡腿堡": 420,
                "薯条(中)": 320,
                "上校鸡块": 280,
                "蛋挞": 230
            },
            "星巴克": {
                "拿铁(中)": 150,
                "美式咖啡": 10,
                "焦糖玛奇朵(中)": 250,
                "抹茶星冰乐": 350
            },
            "家常菜": {
                "番茄炒蛋": 180,
                "宫保鸡丁": 350,
                "鱼香肉丝": 320,
                "麻婆豆腐": 280,
                "青椒肉丝": 300,
                "炒青菜": 120
            }
        }

    def analyze_food_with_llm(self, food_input: str) -> Dict:
        """
        使用现有的大模型客户端分析食物描述

        Args:
            food_input: 用户输入的食物描述

        Returns:
            结构化分析结果
        """
        if not self.client:
            return {"error": "大模型客户端未初始化"}

        prompt = f"""作为专业营养师，请分析以下食物描述并提取结构化信息：

食物描述："{food_input}"

请以JSON格式返回分析结果，必须包含以下字段：

{{
  "food_items": [
    {{
      "name": "食物成分名称（如'米饭'、'鸡胸肉'）",
      "estimated_weight_g": "估算重量（克），基于正常份量",
      "cooking_method": "烹饪方式（如'炒'、'煮'、'蒸'等）"
    }}
  ],
  "portion_size": "份量大小（'小'、'中'、'大'）",
  "sauce_level": "酱料程度（'少'、'正常'、'多'）",
  "clarity_score": "描述清晰度评分（1-5分）",
  "needs_clarification": "是否需要进一步询问（true/false）",
  "clarification_questions": ["如果需要追问，提供问题列表"]
}}

重要规则：
1. 如果用户描述模糊（如"吃了饭"），clarity_score设为1-2，needs_clarification设为true
2. 如果用户描述包含具体重量（如"200克米饭"），直接使用该重量
3. 如果描述连锁餐厅食物（如"麦当劳巨无霸"），食物名称用餐厅+菜品形式

示例响应：
{{
  "food_items": [
    {{"name": "米饭", "estimated_weight_g": 200, "cooking_method": "蒸"}},
    {{"name": "鸡胸肉", "estimated_weight_g": 150, "cooking_method": "炒"}}
  ],
  "portion_size": "中",
  "sauce_level": "正常",
  "clarity_score": 4,
  "needs_clarification": false,
  "clarification_questions": []
}}"""

        try:
            response = self.client.chat.completions.create(
                model="qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是专业营养师，必须返回严格JSON格式的分析结果。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )

            content = response.choices[0].message.content

            # 提取JSON部分
            import json
            try:
                # 尝试直接解析
                result = json.loads(content)
            except:
                # 尝试提取JSON
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    result = json.loads(match.group())
                else:
                    # 如果无法解析，创建默认结果
                    result = {
                        "food_items": [],
                        "portion_size": "中",
                        "sauce_level": "正常",
                        "clarity_score": 2,
                        "needs_clarification": True,
                        "clarification_questions": ["能具体描述一下吃了什么吗？"]
                    }

            return result

        except Exception as e:
            return {
                "error": f"分析失败: {str(e)}",
                "food_items": [],
                "clarity_score": 1,
                "needs_clarification": True,
                "clarification_questions": ["抱歉，分析失败了。能再描述一下您吃了什么吗？"]
            }

    def find_food_in_db(self, food_name: str) -> Dict:
        """
        在食物数据库中查找匹配项

        Args:
            food_name: 食物名称

        Returns:
            食物数据，如果找不到返回默认值
        """
        # 首先检查完全匹配
        if food_name in self.base_food_db:
            return self.base_food_db[food_name]

        # 检查部分匹配
        for key in self.base_food_db:
            if key in food_name or food_name in key:
                return self.base_food_db[key]

        # 检查常见关键词
        keywords = {
            "饭": "米饭",
            "面": "面条",
            "肉": "鸡肉",
            "菜": "蔬菜",
            "果": "苹果",
            "蛋": "鸡蛋",
            "奶": "牛奶",
            "包": "面包",
            "豆": "豆腐",
            "鱼": "鱼",
            "虾": "虾",
            "鸡": "鸡肉",
            "牛": "牛肉",
            "猪": "猪肉"
        }

        for keyword, default_food in keywords.items():
            if keyword in food_name:
                return self.base_food_db.get(default_food, {"calories": 100, "protein": 5, "carbs": 10, "fat": 5})

        # 返回默认值
        return {"calories": 100, "protein": 5, "carbs": 10, "fat": 5}

    def calculate_calories_from_analysis(self, analysis: Dict) -> Dict:
        """
        基于分析结果计算热量

        Args:
            analysis: 食物分析结果

        Returns:
            热量计算结果
        """
        if "error" in analysis:
            return {
                "success": False,
                "message": analysis["error"],
                "total_calories": 0
            }

        if not analysis.get("food_items"):
            return {
                "success": False,
                "message": "无法识别食物成分",
                "total_calories": 0,
                "needs_clarification": True,
                "clarification_questions": ["您具体吃了什么呢？"]
            }

        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        details = []

        for item in analysis["food_items"]:
            food_name = item.get("name", "")
            weight = item.get("estimated_weight_g", 100)
            cooking_method = item.get("cooking_method", "炒")

            # 1. 首先检查是否为连锁餐厅食物
            is_restaurant_food = False
            restaurant_calories = 0

            for restaurant, menu in self.restaurant_calories.items():
                if restaurant in food_name:
                    # 查找具体菜品
                    for dish, cal in menu.items():
                        if dish in food_name:
                            restaurant_calories = cal
                            is_restaurant_food = True
                            break
                    if is_restaurant_food:
                        break

            if is_restaurant_food and restaurant_calories > 0:
                # 使用餐厅菜品的热量
                item_calories = restaurant_calories
                item_protein = restaurant_calories * 0.15 / 4  # 估算蛋白质
                item_carbs = restaurant_calories * 0.5 / 4  # 估算碳水
                item_fat = restaurant_calories * 0.35 / 9  # 估算脂肪

                details.append({
                    "name": food_name,
                    "type": "餐厅菜品",
                    "weight_g": "标准份",
                    "cooking_method": cooking_method,
                    "calories": item_calories,
                    "protein_g": round(item_protein, 1),
                    "carbs_g": round(item_carbs, 1),
                    "fat_g": round(item_fat, 1)
                })

            else:
                # 2. 查找基础食物数据库
                base_data = self.find_food_in_db(food_name)

                # 3. 应用烹饪系数
                cooking_coef = self.cooking_methods.get(cooking_method, 1.2)

                # 4. 计算热量
                item_calories = (base_data["calories"] * weight / 100) * cooking_coef
                item_protein = base_data["protein"] * weight / 100
                item_carbs = base_data["carbs"] * weight / 100
                item_fat = base_data["fat"] * weight / 100

                details.append({
                    "name": food_name,
                    "type": "家常菜",
                    "weight_g": weight,
                    "cooking_method": cooking_method,
                    "calories": round(item_calories),
                    "protein_g": round(item_protein, 1),
                    "carbs_g": round(item_carbs, 1),
                    "fat_g": round(item_fat, 1)
                })

            total_calories += item_calories
            total_protein += item_protein
            total_carbs += item_carbs
            total_fat += item_fat

        # 5. 应用份量和酱料系数
        portion_size = analysis.get("portion_size", "中")
        sauce_level = analysis.get("sauce_level", "正常")

        portion_coef = self.portion_sizes.get(portion_size, 1.0)
        sauce_coef = self.sauce_levels.get(sauce_level, 1.0)

        total_calories *= portion_coef * sauce_coef
        total_protein *= portion_coef
        total_carbs *= portion_coef
        total_fat *= portion_coef * sauce_coef

        # 6. 估算准确度
        clarity_score = analysis.get("clarity_score", 3)
        if clarity_score <= 2:
            calorie_range = f"{round(total_calories * 0.7)}-{round(total_calories * 1.3)}"
            accuracy = "较低"
        elif clarity_score == 3:
            calorie_range = f"{round(total_calories * 0.8)}-{round(total_calories * 1.2)}"
            accuracy = "中等"
        else:
            calorie_range = f"{round(total_calories * 0.9)}-{round(total_calories * 1.1)}"
            accuracy = "较高"

        return {
            "success": True,
            "total_calories": round(total_calories),
            "calorie_range": calorie_range,
            "protein_g": round(total_protein, 1),
            "carbs_g": round(total_carbs, 1),
            "fat_g": round(total_fat, 1),
            "details": details,
            "accuracy": accuracy,
            "clarity_score": clarity_score,
            "portion_size": portion_size,
            "sauce_level": sauce_level,
            "notes": [
                "💡 这是估算值，实际热量可能因食材品牌、烹饪细节有所不同",
                f"📊 基于您的描述清晰度：{accuracy}",
                f"🍽️ 份量：{portion_size}，酱料：{sauce_level}"
            ]
        }

    def get_calorie_analysis(self, food_input: str) -> Dict:
        """
        主函数：获取食物热量分析

        Args:
            food_input: 用户输入的食物描述

        Returns:
            包含热量信息或追问问题的结果
        """
        # 0. 补充信息
        if "补充：" in food_input:
            # 提取主要食物描述和补充信息
            parts = food_input.split("补充：")
            main_part = parts[0].replace("。", "")
            supplement = parts[1]

            # 重新组合
            food_input = f"{main_part}，{supplement}"
            print(f"🔄 已合并上下文：{food_input}")

        # 1. 分析食物描述
        analysis = self.analyze_food_with_llm(food_input)

        # 2. 检查是否需要追问
        needs_clarification = analysis.get("needs_clarification", False)
        clarity_score = analysis.get("clarity_score", 3)

        if needs_clarification or clarity_score < 3:
            questions = analysis.get("clarification_questions", [])
            if not questions:
                questions = [
                    "能具体说一下您吃了什么食物吗？",
                    "大概吃了多少呢？（比如一碗、一份、200克等）",
                    "是怎么做的？（炒、煮、蒸等）"
                ]

            return {
                "success": False,
                "needs_clarification": True,
                "message": "为了更准确地计算热量，需要您补充一些信息：",
                "questions": questions[:3],
                "suggestion": "请回答上述问题，我会为您重新分析热量"
            }

        # 3. 计算热量
        result = self.calculate_calories_from_analysis(analysis)

        if not result["success"]:
            return result

        # 4. 生成解释文本
        explanation = self.generate_explanation(food_input, result)
        result["explanation"] = explanation

        return result

    def generate_explanation(self, food_input: str, result: Dict) -> str:
        """
        生成自然语言解释

        Args:
            food_input: 用户输入
            result: 热量结果

        Returns:
            自然语言解释
        """
        total_cal = result["total_calories"]
        calorie_range = result["calorie_range"]
        protein = result["protein_g"]
        carbs = result["carbs_g"]
        fat = result["fat_g"]
        accuracy = result["accuracy"]

        details_text = ""
        for i, detail in enumerate(result.get("details", []), 1):
            details_text += f"\n{i}. {detail['name']}：{detail['calories']}大卡"
            if detail.get('weight_g'):
                details_text += f"（约{detail['weight_g']}{'克' if isinstance(detail['weight_g'], (int, float)) else ''}）"

        # 根据总热量给出建议
        if total_cal < 300:
            advice = "热量很低，适合作为加餐或轻食。"
        elif total_cal < 500:
            advice = "热量适中，适合作为一餐的正常摄入。"
        elif total_cal < 800:
            advice = "热量偏高，建议搭配适量运动消耗。"
        else:
            advice = "热量较高，建议下一餐适当减少摄入，并增加运动量。"

        explanation = f"""📊 **热量分析报告**

根据您的描述"**{food_input}**"，分析如下：

🔥 **总热量估算**：约 **{calorie_range}大卡**（最可能值：{total_cal}大卡）

🍽️ **营养构成**：
• 蛋白质：**{protein}克** 💪（帮助肌肉修复）
• 碳水化合物：**{carbs}克** ⚡（提供能量）
• 脂肪：**{fat}克** 🥑（维持身体功能）

{details_text}

📈 **准确度评估**：{accuracy}

💡 **健康建议**：
{advice}

✨ **温馨提示**：
• 估算基于标准食材和烹饪方式
• 实际热量可能因个体差异略有不同
• 保持均衡饮食，享受健康生活！"""

        return explanation

def update_meal_status(self, user_input: str, meal_type: str = "auto", food_info: Dict[str, Any] = None) -> dict:
    """
    更新用户的用餐状态并给出相应建议

    Args:
        user_input: 用户描述用餐情况的文本
        meal_type: 用餐类型（早餐/午餐/晚餐/auto）
    """
    status_field = None
    detected_meal = None

    try:
        # 获取当前时间
        current_time = datetime.datetime.now()
        current_hour = current_time.hour

        #print(f"🕐 [update_meal_status内部] 当前时间：{current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        #print(f"🕐 [update_meal_status内部] 当前小时：{current_hour}")
        #print(f"📝 [update_meal_status内部] 用户输入：'{user_input}'")
        #print(f"🍽️ [update_meal_status内部] 传入meal_type：'{meal_type}'")

        # 自动判断用餐类型
        if meal_type == "auto":
            # 精确匹配餐次关键词
            meal_patterns = {
                "早餐": [r'早餐|早饭|早点|晨餐|早(?![上中晚])|breakfast', "早餐"],
                "午餐": [r'午餐|午饭|午(?![餐])|中餐|中午饭|lunch', "午餐"],
                "晚餐": [r'晚餐|晚饭|晚(?![上])|晚饭|supper|dinner', "晚餐"]
            }

            detected_meal = None
            for meal, (pattern, display_name) in meal_patterns.items():
                if re.search(pattern, user_input, re.IGNORECASE):
                    detected_meal = display_name
                    break

            # 根据时间判断
            if not detected_meal:
                if 5 <= current_hour < 11:
                    detected_meal = "早餐"
                elif 11 <= current_hour < 16:
                    detected_meal = "午餐"
                elif 16 <= current_hour < 22:
                    detected_meal = "晚餐"
                else:
                    detected_meal = "宵夜"

            #    print(f"🔍 [update_meal_status内部] 自动判断结果：{detected_meal}")
        else:
        #    print(f"🔍 [update_meal_status内部] 使用指定的meal_type：{meal_type}")
            detected_meal = meal_type

            # 检查detected_meal是否有效
            if not detected_meal:
                print("❌ [update_meal_status内部] 无法判断用餐类型")
                return {
                    "success": False,
                    "message": "❌ 无法判断用餐类型，请明确指定是早餐、午餐还是晚餐"
                }

        #    print(f"🔍 [update_meal_status内部] 开始更新每日档案...")

            # 1. 检查是否有recorder对象
            if not hasattr(self, 'recorder'):
                print("❌ [update_meal_status内部] 找不到recorder对象")
                return {
                    "success": False,
                    "message": "❌ 系统错误：找不到记录器"
                }

            # 2. 加载今日的每日档案（不是user_profile！）
            today_data = self.recorder.load_today_record()
        #    print(f"✅ [update_meal_status内部] 加载今日档案成功")
        #    print(f"📊 [update_meal_status内部] 档案日期：{today_data.get('date', '未知')}")

            # 3. 设置status_field
            status_field = f"{detected_meal}状态"
        #    print(f"🔍 [update_meal_status内部] status_field设置为：{status_field}")

            # 4. 检查是否有饮食计划用于比较
            food_plan = today_data.get("daily_plan", {}).get("food", [])
        #    print(f"🔍 [update_meal_status内部] 饮食计划长度：{len(food_plan)}")

            current_meal_plan = ""
            for plan_item in food_plan:
                if plan_item.startswith(detected_meal) or detected_meal in plan_item:
                    current_meal_plan = plan_item
                    break

        #    print(f"🔍 [update_meal_status内部] 当前餐次计划：{current_meal_plan}")

            # 5. 更新状态字段（在每日档案中更新）
            old_tuple = today_data.get(status_field, ("没吃", ""))
            old_status = old_tuple[0]  # 旧的用餐状态
            old_note = old_tuple[1] if len(old_tuple) > 1 else ""  # 旧的备注

            # 如果旧备注是字典（单个记录），转换为列表
            old_records = []
            if isinstance(old_note, dict) and old_note:  # 如果是字典且有内容
                old_records = [old_note]  # 转换为列表，包含一个元素
            elif isinstance(old_note, list):  # 如果已经是列表
                old_records = old_note
            elif old_note:  # 如果是其他非空值
                # 尝试转换为字典格式
                try:
                    if isinstance(old_note, str):
                        # 如果是JSON字符串
                        import json
                        try:
                            old_note_dict = json.loads(old_note)
                            if isinstance(old_note_dict, dict):
                                old_records = [old_note_dict]
                            elif isinstance(old_note_dict, list):
                                old_records = old_note_dict
                        except:
                            # 如果不是JSON，创建简单记录
                            old_records = [{"description": old_note}]
                    else:
                        # 其他类型，创建简单记录
                        old_records = [{"description": str(old_note)}]
                except:
                    old_records = []

            print(f"🔍 [update_meal_status内部] 现有记录数量：{len(old_records)}")
            for i, record in enumerate(old_records):
                print(f"   记录{i + 1}: {record.get('description', '无描述')}")

            current_time = datetime.datetime.now()

            # 创建新的食物记录
            new_record = {
                "description": user_input,  # 使用用户输入作为描述
                "timestamp": current_time.isoformat(),
                "meal_type": detected_meal,
                "record_index": len(old_records)  # 记录这是第几次进食
            }

            # 如果有食物分析信息，添加到记录中
            if food_info:
                new_record.update({
                    "total_calories": food_info.get("total_calories", 0),
                    "protein_g": food_info.get("protein_g", 0),
                    "carbs_g": food_info.get("carbs_g", 0),
                    "fat_g": food_info.get("fat_g", 0),
                    "calorie_range": food_info.get("calorie_range", ""),
                    "details": food_info.get("details", []),
                    "has_calorie_info": True
                })
            else:
                new_record["has_calorie_info"] = False

            updated_records = old_records.copy()  # 复制现有记录
            updated_records.append(new_record)  # 追加新记录

            print(f"✅ [update_meal_status内部] 新增记录，现在总共有 {len(updated_records)} 条{detected_meal}记录")

            # 确定状态文本
            if len(updated_records) == 1:
                status_text = "吃了"
            else:
                status_text = f"吃了{len(updated_records)}次"  # 显示进食次数

            today_data[status_field] = (status_text, updated_records)

            today_data["last_updated"] = current_time.isoformat()

            # 7. 保存每日档案（关键！不是save_profiles）
            success = self.recorder.save_today_record(today_data)
            if success:
                print(f"✅ [update_meal_status内部] 每日档案保存成功")
            else:
                print(f"❌ [update_meal_status内部] 每日档案保存失败")
                return {
                    "success": False,
                    "message": "❌ 保存记录失败"
                }

            # 8. 从每日档案中读取状态构建返回消息
            meal_status = {
                "早餐": today_data.get("早餐状态", ("没吃", ""))[0],
                "午餐": today_data.get("午餐状态", ("没吃", ""))[0],
                "晚餐": today_data.get("晚餐状态", ("没吃", ""))[0]
            }

            completed_meals = [meal for meal, status in meal_status.items() if status == "吃了"]

            # 构建返回消息
            response = {
                "success": True,
                "message": f"✅ 已记录：{detected_meal} - 吃了",
                "detected_meal": detected_meal,
                "current_status": meal_status,
                "completed_meals": completed_meals,
                "total_completed": len(completed_meals),
                "next_action": ""
            }

            # 检查是否在合理的时间报告用餐
            meal_time_ranges = {
                "早餐": (5, 11),
                "午餐": (11, 16),
                "晚餐": (16, 22)
            }

            if detected_meal in meal_time_ranges:
                start, end = meal_time_ranges[detected_meal]
                if not (start <= current_hour < end):
                    time_check_message = f"⏰ 注意：当前时间{current_time.strftime('%H:%M')}不在{detected_meal}时间范围（{start}:00-{end}:00）内，但已记录您的用餐。"
                    response["time_check"] = time_check_message

            if current_meal_plan:
                response["recommended_plan"] = current_meal_plan

            # 根据完成情况给出建议
            if len(completed_meals) == 3:
                response["next_action"] = "🌟 太棒了！今天所有正餐都完成了，记得适量运动哦！"
            elif len(completed_meals) == 2:
                remaining_meal = next((meal for meal, status in meal_status.items() if status == "没吃"), None)
                if remaining_meal:
                    response["next_action"] = f"💪 继续加油！{remaining_meal}也要按时吃哦！"
                else:
                    response["next_action"] = "💪 继续保持！"
            else:
                response["next_action"] = "👍 好的开始！坚持记录每餐，健康更有保障！"

            #print(f"✅ [update_meal_status内部] 函数执行完成，返回结果：{response}")
            return response

    except Exception as e:
        print(f"❌ [update_meal_status内部] 函数执行出错：{str(e)}")
        import traceback
        traceback.print_exc()  # 打印完整的错误堆栈
        return {
            "success": False,
            "message": f"❌ 更新失败：{str(e)}"
        }

def get_daily_plan(self, view_type: str = "current_meal") -> dict:
    """
    获取用户当前时间段对应的饮食和运动计划

    Args:
        view_type: 查看的类型
            - current_meal: 当前餐次的计划
            - next_meal: 下一餐的计划
            - all: 全天计划
            - drink: 饮水计划
            - exercise: 运动计划

    Returns:
        dict: 对应的计划信息
    """
    try:
        # 检查是否有recorder对象
        if not hasattr(self, 'recorder'):
            return {
                "success": False,
                "message": "❌ 系统错误：找不到记录器"
            }

        # 获取当前时间
        current_time = datetime.datetime.now()
        current_hour = current_time.hour

        # 判断当前时间段
        if 5 <= current_hour < 11:
            current_meal = "早餐"
            next_meal = "午餐"
            meal_time_range = "5:00-11:00"
        elif 11 <= current_hour < 16:
            current_meal = "午餐"
            next_meal = "晚餐"
            meal_time_range = "11:00-16:00"
        elif 16 <= current_hour < 22:
            current_meal = "晚餐"
            next_meal = "明天早餐"
            meal_time_range = "16:00-22:00"
        else:
            current_meal = "宵夜"
            next_meal = "明天早餐"
            meal_time_range = "22:00-5:00"

        # 从每日档案加载数据
        today_data = self.recorder.load_today_record()

        # 关键修复：如果 today_data 是字符串，尝试转换为字典
        if isinstance(today_data, str):
            try:
                import json
                today_data = json.loads(today_data)
            except:
                # 如果无法解析，创建空字典
                today_data = {}

        if not isinstance(today_data, dict):
            today_data = {}

        if "daily_plan" not in today_data:
            return {
                "success": False,
                "message": "❌ 今天还没有生成健康计划"
            }

        # 确保 daily_plan 是字典
        daily_plan = today_data.get("daily_plan", {})
        if isinstance(daily_plan, str):
            try:
                import json
                daily_plan = json.loads(daily_plan)
            except:
                daily_plan = {"food": [], "movement": []}

        food_plan = daily_plan.get("food", [])

        # 从每日档案读取餐次状态
        meal_status = {
            "早餐": today_data.get("早餐状态", ("没吃", ""))[0],
            "午餐": today_data.get("午餐状态", ("没吃", ""))[0],
            "晚餐": today_data.get("晚餐状态", ("没吃", ""))[0]
        }

        # 获取餐次详细记录
        meal_records = {}
        for meal in ["早餐", "午餐", "晚餐"]:
            meal_data = today_data.get(f"{meal}状态", ("没吃", ""))
            if len(meal_data) > 1 and isinstance(meal_data[1], list):
                meal_records[meal] = meal_data[1]
            else:
                meal_records[meal] = []

        # 根据view_type返回不同的信息
        if view_type == "current_meal":
            # 只获取当前餐次的饮食计划
            current_meal_plan = []
            for plan_item in food_plan:
                if plan_item.startswith(current_meal) or plan_item.startswith(current_meal[0]):  # 匹配"早餐"或"早"
                    current_meal_plan.append(plan_item)

            # 如果没有找到明确的当前餐次计划，返回第一条计划
            if not current_meal_plan and food_plan:
                # 根据时间选择最合适的
                if current_meal == "早餐":
                    current_meal_plan = [item for item in food_plan if "早餐" in item or "早饭" in item]
                elif current_meal == "午餐":
                    current_meal_plan = [item for item in food_plan if "午餐" in item or "午饭" in item]
                elif current_meal == "晚餐":
                    current_meal_plan = [item for item in food_plan if "晚餐" in item or "晚饭" in item]

            if current_meal_plan:
                return {
                    "success": True,
                    "message": f"🍽️ 现在是{current_meal}时间（{meal_time_range}），这是您的{current_meal}计划：",
                    "plan": current_meal_plan,
                    "meal_type": current_meal,
                    "current_time": current_time.strftime("%H:%M"),
                    "meal_status": today_data.get(f"{current_meal}状态", ("没吃", ""))[0],
                    "meal_records_count": len(meal_records.get(current_meal, [])),
                    "meal_records": meal_records.get(current_meal, [])
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ 没有找到{current_meal}的具体计划"
                }

        elif view_type == "next_meal":
            # 获取下一餐的计划
            next_meal_plan = []
            for plan_item in food_plan:
                if plan_item.startswith(next_meal) or plan_item.startswith(next_meal[0]):
                    next_meal_plan.append(plan_item)

            if next_meal_plan:
                return {
                    "success": True,
                    "message": f"🔜 下一餐是{next_meal}，这是计划：",
                    "plan": next_meal_plan,
                    "next_meal": next_meal,
                    "current_meal": current_meal
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ 没有找到{next_meal}的具体计划"
                }

        elif view_type == "all":
            # 返回全天计划
            return {
                "success": True,
                "message": "📋 这是您今天的全天健康计划：",
                "food_plan": food_plan,
                "movement_plan": daily_plan.get("movement", []),
                "current_time": current_time.strftime("%H:%M"),
                "meal_status": {
                    "早餐": today_data.get("早餐状态", ("没吃", ""))[0],
                    "午餐": today_data.get("午餐状态", ("没吃", ""))[0],
                    "晚餐": today_data.get("晚餐状态", ("没吃", ""))[0]
                }
            }

        elif view_type == "drink":
            # 返回饮水计划
            drink_plan = today_data.get("drink_plan", 8)
            current_drinks = today_data.get("drink_number", 0)
            remaining = drink_plan - current_drinks

            return {
                "success": True,
                "message": "💧 饮水计划：",
                "total_target": drink_plan,
                "current_drinks": current_drinks,
                "remaining": remaining,
                "progress_percentage": round((current_drinks / drink_plan * 100), 1) if drink_plan > 0 else 0,
                "recommendation": f"今天目标{drink_plan}杯水，已喝{current_drinks}杯，还需{remaining}杯"
            }

        elif view_type == "exercise":
            # 返回运动计划
            movement_plan = daily_plan.get("movement", [])
            if movement_plan:
                return {
                    "success": True,
                    "message": "🏃 今日运动计划：",
                    "movement_plan": movement_plan,
                    "exercise_status": today_data.get("运动状态", ("没运动", ""))[0]
                }
            else:
                return {
                    "success": False,
                    "message": "❌ 今天没有安排具体运动计划"
                }

    except Exception as e:
        return {
            "success": False,
            "message": f"❌ 获取计划失败：{str(e)}"
        }


def calculate_food_calories(user_input: str, meal_type: str = None) -> Dict:
    """
    MCP工具：计算食物热量和营养成分

    Args:
        user_input: 用户描述食物的文本
        meal_type: 用餐类型（可选）

    Returns:
        热量计算结果
    """
    # 注意：这个函数需要被主函数中的 _execute_tool 调用
    # 由于需要大模型客户端，我们将在主函数中处理初始化

    # 这里返回一个标准格式，实际处理在主函数中
    return {
        "success": False,
        "message": "此功能需要在主函数中初始化后使用",
        "needs_initialization": True
    }


def get_calorie_calculator_help() -> Dict:
    """
    获取热量计算器帮助信息

    Returns:
        帮助信息
    """
    return {
        "tool_name": "calculate_food_calories",
        "description": "分析食物热量和营养成分",
        "usage": "输入食物描述，如'200克米饭和150克炒鸡胸肉'",
        "parameters": {
            "user_input": "食物描述（必填）",
            "meal_type": "用餐类型（早餐/午餐/晚餐/宵夜，可选）"
        },
        "examples": [
            "一碗米饭",
            "一个苹果和一杯牛奶",
            "150克煎牛排配蔬菜",
            "麦当劳巨无霸套餐",
            "番茄炒蛋和一碗米饭"
        ],
        "notes": [
            "支持中文食物描述",
            "对于模糊描述会追问细节",
            "支持连锁餐厅常见菜品",
            "结果为估算值，仅供参考"
        ]
    }
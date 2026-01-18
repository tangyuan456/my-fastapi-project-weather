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
import re


def update_meal_status(self, user_input: str, meal_type: str = "auto") -> dict:
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

        print(f"🕐 [update_meal_status内部] 当前时间：{current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 [update_meal_status内部] 当前小时：{current_hour}")
        print(f"📝 [update_meal_status内部] 用户输入：'{user_input}'")
        print(f"🍽️ [update_meal_status内部] 传入meal_type：'{meal_type}'")

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

                print(f"🔍 [update_meal_status内部] 自动判断结果：{detected_meal}")
            else:
                print(f"🔍 [update_meal_status内部] 使用指定的meal_type：{meal_type}")
                detected_meal = meal_type

            # 检查detected_meal是否有效
            if not detected_meal:
                print("❌ [update_meal_status内部] 无法判断用餐类型")
                return {
                    "success": False,
                    "message": "❌ 无法判断用餐类型，请明确指定是早餐、午餐还是晚餐"
                }

            print(f"🔍 [update_meal_status内部] 开始更新每日档案...")

            # 1. 检查是否有recorder对象
            if not hasattr(self, 'recorder'):
                print("❌ [update_meal_status内部] 找不到recorder对象")
                return {
                    "success": False,
                    "message": "❌ 系统错误：找不到记录器"
                }

            # 2. 加载今日的每日档案（不是user_profile！）
            today_data = self.recorder.load_today_record()
            print(f"✅ [update_meal_status内部] 加载今日档案成功")
            print(f"📊 [update_meal_status内部] 档案日期：{today_data.get('date', '未知')}")

            # 3. 设置status_field
            status_field = f"{detected_meal}状态"
            print(f"🔍 [update_meal_status内部] status_field设置为：{status_field}")

            # 4. 检查是否有饮食计划用于比较
            food_plan = today_data.get("daily_plan", {}).get("food", [])
            print(f"🔍 [update_meal_status内部] 饮食计划长度：{len(food_plan)}")

            current_meal_plan = ""
            for plan_item in food_plan:
                if plan_item.startswith(detected_meal) or detected_meal in plan_item:
                    current_meal_plan = plan_item
                    break

            print(f"🔍 [update_meal_status内部] 当前餐次计划：{current_meal_plan}")

            # 5. 更新状态字段（在每日档案中更新）
            old_status = today_data.get(status_field, "没吃")
            print(f"🔍 [update_meal_status内部] 更新字段：{status_field}，从'{old_status}'改为'吃了'")

            today_data[status_field] = "吃了"

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
                "早餐": today_data.get("早餐状态", "没吃"),
                "午餐": today_data.get("午餐状态", "没吃"),
                "晚餐": today_data.get("晚餐状态", "没吃")
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

            print(f"✅ [update_meal_status内部] 函数执行完成，返回结果：{response}")
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

        if "daily_plan" not in today_data:
            return {
                "success": False,
                "message": "❌ 今天还没有生成健康计划"
            }

        daily_plan = today_data["daily_plan"]
        food_plan = daily_plan.get("food", [])

        # 从每日档案读取餐次状态
        meal_status = {
            "早餐": today_data.get("早餐状态", "没吃"),
            "午餐": today_data.get("午餐状态", "没吃"),
            "晚餐": today_data.get("晚餐状态", "没吃")
        }

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
                    "meal_status": today_data.get(f"{current_meal}状态", "没吃")
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
                    "早餐": today_data.get("早餐状态", "没吃"),
                    "午餐": today_data.get("午餐状态", "没吃"),
                    "晚餐": today_data.get("晚餐状态", "没吃")
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
                    "exercise_status": today_data.get("运动状态", "没运动")
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
"""
健康减肥助手功能函数库
包含所有核心功能的独立函数
加载所有用户档案、计算BMI及相关信息、创建新用户健康档案、保存所有用户档案到文件、显示用户档案详情、更新用户体重、注销用户档案
"""

import json
import datetime
import os
from typing import Dict, Any, Optional, List

# 全局变量（模拟数据库）
USER_PROFILES = {}
DATA_FILE = "user_profiles.json"

# 常量定义
GENDER_OPTIONS = {'A': '男', 'B': '女', 'C': '其他/不愿透露'}

GOAL_OPTIONS = {
    'A': '快速减重（每月减4-8斤）',
    'B': '健康减重（每月减2-4斤）',
    'C': '维持体重',
    'D': '增肌塑形'
}

DIET_OPTIONS = {
    'A': '清淡少油',
    'B': '喜欢辣味',
    'C': '偏好甜食',
    'D': '素食主义',
    'E': '低盐饮食',
    'F': '高蛋白饮食',
    'G': '低碳水饮食',
    'H': '地中海饮食',
    'I': '广东菜系',
    'J': '川菜湘菜',
    'K': '江浙菜系',
    'L': '北方菜系'
}

ALLERGEN_OPTIONS = {
    'A': '牛奶/乳制品',
    'B': '鸡蛋',
    'C': '花生',
    'D': '坚果',
    'E': '鱼类',
    'F': '贝类',
    'G': '大豆',
    'H': '小麦/麸质',
    'I': '海鲜',
    'J': '芒果',
    'K': '酒精',
    'L': '其他，自写',
    'M': '无'
}

MOVEMENT_OPTIONS={
    'A': '慢跑',
    'B': '跳绳',
    'C': '瑜伽',
    'D': '游泳',
    'E': '自行车骑行',
    'F': '健身操',
    'G': '羽毛球',
    'H': '舞蹈',
    'L': '其他，自填',
    'M': '随便，我都可以'
}

def load_profiles() -> Dict[str, Any]:
    """
    加载所有用户档案

    返回值:
        Dict: 包含所有用户档案的字典
    """
    global USER_PROFILES

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                USER_PROFILES = json.load(f)
                print(f"已加载 {len(USER_PROFILES)} 个用户档案")
        except Exception as e:
            print(f"加载用户档案时出错: {e}")
            USER_PROFILES = {}
    else:
        USER_PROFILES = {}

    return USER_PROFILES

def get_valid_number_input(prompt: str, min_val: float, max_val: float) -> float:
    """
    获取有效的数字输入

    参数:
        prompt: 提示文本
        min_val: 最小值
        max_val: 最大值

    返回值:
        float: 有效的数字
    """
    while True:
        try:
            value = float(input(prompt))
            if min_val <= value <= max_val:
                return value
            else:
                print(f"请输入 {min_val} 到 {max_val} 之间的数字")
        except ValueError:
            print("请输入有效的数字")

def get_multiple_choice_input(prompt: str, options: Dict[str, str],
                              allow_multiple: bool = False) -> List[str]:
    """
    获取多选或单选输入

    参数:
        prompt: 提示文本
        options: 选项字典
        allow_multiple: 是否允许多选

    返回值:
        List[str]: 选择的选项值列表
    """
    print(prompt)

    # 显示选项
    for key, value in options.items():
        print(f"   {key}. {value}")

    while True:
        if allow_multiple:
            choice_text = "请输入选项(多个用逗号分隔，如：A,B,C): "
        else:
            choice_text = "请输入选项: "

        choices = input(choice_text).upper().replace('，', ',')

        if allow_multiple:
            selected = [c.strip() for c in choices.split(',') if c.strip()]
        else:
            selected = [choices.strip()] if choices.strip() else []

        if not selected:
            print("请至少选择一个选项")
            continue

        # 验证所有选项
        invalid = [c for c in selected if c not in options]
        if invalid:
            print(f"无效选项: {', '.join(invalid)}，请重新选择")
            continue

        # 返回选项对应的值
        return [options[c] for c in selected]


def calculate_bmi(weight_kg: float, height_cm: float) -> Dict[str, Any]:
    """
    计算BMI及相关信息

    参数:
        weight_kg: 体重(kg)
        height_cm: 身高(cm)

    返回值:
        Dict: 包含BMI和状态的信息
    """
    bmi = weight_kg / ((height_cm / 100) ** 2)
    bmi = round(bmi, 1)

    if bmi < 18.5:
        status = "偏瘦"
        suggestion = "建议适当增加营养摄入"
    elif bmi < 24:
        status = "正常"
        suggestion = "保持良好生活习惯"
    elif bmi < 28:
        status = "超重"
        suggestion = "建议控制饮食，增加运动"
    else:
        status = "肥胖"
        suggestion = "建议制定科学减肥计划"

    return {
        'bmi': bmi,
        'status': status,
        'suggestion': suggestion
    }

def create_user_profile() -> Optional[Dict[str, Any]]:
    """
    创建新用户健康档案

    返回值:
        Dict: 用户档案数据，创建失败返回None
    """
    print("\n" + "=" * 60)
    print("你是第一次使用我，我将为你健康档案")
    print("=" * 60)

    user_data = {}

    try:
        # 1. 昵称
        nickname = input("\n1. 请输入您的昵称: ").strip()
        if not nickname:
            print("昵称不能为空")
            return None

        # 检查昵称是否已存在
        if nickname in USER_PROFILES:
            print(f"昵称 '{nickname}' 已存在，请使用其他昵称")
            return None

        user_data['nickname'] = nickname

        # 2. 年龄
        user_data['age'] = int(get_valid_number_input(
            "2. 请输入您的年龄（18-80）: ", 18, 80
        ))

        # 3. 性别
        gender_list = get_multiple_choice_input(
            "\n3. 请选择您的性别:", GENDER_OPTIONS, allow_multiple=False
        )
        user_data['gender'] = gender_list[0] if gender_list else "未选择"

        # 4. 身高
        height = get_valid_number_input(
            "\n4. 请输入您的身高(cm，例如：175.5): ", 100, 250
        )
        user_data['height_cm'] = height

        # 5. 体重
        weight = get_valid_number_input(
            "5. 请输入您当前的体重(kg，例如：65.2): ", 30, 300
        )
        user_data['current_weight_kg'] = weight

        # 6. 计算BMI
        bmi_info = calculate_bmi(weight, height)
        user_data.update(bmi_info)

        # 7. 减肥目标
        goal_list = get_multiple_choice_input(
            "\n6. 请选择您的减肥目标:", GOAL_OPTIONS, allow_multiple=False
        )
        user_data['goal'] = goal_list[0] if goal_list else "未选择"

        # 8. 目标体重（如果是减肥目标）
        if user_data['goal'] in ['快速减重（每月减4-8斤）', '健康减重（每月减2-4斤）']:
            target_weight = get_valid_number_input(
                f"   请输入您的目标体重(kg，当前{weight}kg): ", 30, 300
            )
            user_data['target_weight_kg'] = target_weight
            user_data['weight_to_lose'] = round(weight - target_weight, 1)

        # 9. 饮食习惯（多选）
        diet_list = get_multiple_choice_input(
            "\n7. 请选择您的饮食习惯（可多选）:", DIET_OPTIONS, allow_multiple=True
        )
        user_data['diet_preferences'] = diet_list

        # 10. 过敏原（多选，可选）
        print("\n8. 过敏食物（可选，直接回车跳过）")
        allergen_list = get_multiple_choice_input(
            "   请选择过敏食物（可多选）:", ALLERGEN_OPTIONS, allow_multiple=True
        )
        user_data['allergens'] = allergen_list



        # 11. 运动偏好
        print("\n9. 运动偏好（可选）")
        movement_list = get_multiple_choice_input(
            "   请选择你喜欢的运动方式（可多选）:", MOVEMENT_OPTIONS, allow_multiple=True
        )
        user_data['move_prefer'] = movement_list

        # 12. 其他备注
        print("\n10. 其他备注（可选）:")
        print("   如：特殊疾病史、服药情况、运动限制等")
        remarks = input("请输入备注（如无可直接回车）: ").strip()
        if remarks:
            user_data['remarks'] = remarks

        # 12. 时间戳
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_data['registration_date'] = current_time
        user_data['last_update'] = current_time

        # 保存到全局数据
        USER_PROFILES[nickname] = user_data

        # 保存到文件
        if save_profiles():
            print(f"\n✅ 用户 '{nickname}' 档案创建成功！")
            return user_data
        else:
            print("\n❌ 档案创建失败，无法保存数据")
            return None

    except KeyboardInterrupt:
        print("\n\n操作已取消")
        return None
    except Exception as e:
        print(f"\n❌ 创建档案时出错: {e}")
        return None


def save_profiles() -> bool:
    """
    保存所有用户档案到文件

    返回值:
        bool: 保存是否成功
    """
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(USER_PROFILES, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存用户档案时出错: {e}")
        return False

def search_user_profile(user_data: Dict[str, Any]) -> None:
    """
    显示用户档案详情

    参数:
        user_data: 用户档案数据
    """
    if not user_data:
        print("无有效用户数据")
        return

    print("\n" + "=" * 60)
    print("用户健康档案详情")
    print("=" * 60)

    # 基本信息
    print(f"👤 昵称: {user_data.get('nickname', '未知')}")
    print(f"🎂 年龄: {user_data.get('age', '未知')}岁")
    print(f"🚻 性别: {user_data.get('gender', '未知')}")

    # 身体数据
    print(f"📏 身高: {user_data.get('height_cm', '未知')}cm")
    print(f"⚖️  当前体重: {user_data.get('current_weight_kg', '未知')}kg")

    # BMI信息
    bmi = user_data.get('bmi', 0)
    status = user_data.get('status', '未知')
    suggestion = user_data.get('suggestion', '')
    print(f"📊 BMI指数: {bmi} ({status})")
    if suggestion:
        print(f"💡 建议: {suggestion}")

    # 减肥目标
    goal = user_data.get('goal', '未设置')
    print(f"🎯 减肥目标: {goal}")

    if 'target_weight_kg' in user_data:
        print(f"🎯 目标体重: {user_data['target_weight_kg']}kg")
        print(f"📉 需减重量: {user_data.get('weight_to_lose', 0)}kg")

    # 饮食习惯
    diet_prefs = user_data.get('diet_preferences', [])
    if diet_prefs:
        print(f"🍽️  饮食习惯: {', '.join(diet_prefs)}")
    else:
        print(f"🍽️  饮食习惯: 未设置")

    # 过敏原
    allergens = user_data.get('allergens', [])
    if allergens:
        print(f"⚠️  过敏食物: {', '.join(allergens)}")

    # 备注
    if 'remarks' in user_data:
        print(f"📝 备注: {user_data['remarks']}")

    # 时间信息
    if 'registration_date' in user_data:
        print(f"📅 注册时间: {user_data['registration_date']}")
    if 'last_update' in user_data:
        print(f"🔄 最后更新: {user_data['last_update']}")

    print("=" * 60)


def update_user_weight(nickname:str,new_weight: float) -> bool:
    """
    更新用户体重

    参数:
        nickname: 用户昵称

    返回值:
        bool: 更新是否成功
    """
    if nickname not in USER_PROFILES:
        print(f"❌ 用户 '{nickname}' 不存在")
        return False

    try:
        # 显示当前信息
        current_weight = USER_PROFILES[nickname]['current_weight_kg']
        print(f"当前体重: {current_weight}kg")

        # 更新数据
        old_weight = current_weight
        USER_PROFILES[nickname]['current_weight_kg'] = new_weight

        # 重新计算BMI
        height = USER_PROFILES[nickname]['height_cm']
        bmi_info = calculate_bmi(new_weight, height)
        USER_PROFILES[nickname].update(bmi_info)

        # 更新目标体重相关数据
        if 'target_weight_kg' in USER_PROFILES[nickname]:
            target = USER_PROFILES[nickname]['target_weight_kg']
            weight_to_lose = new_weight - target
            USER_PROFILES[nickname]['weight_to_lose'] = round(abs(weight_to_lose), 1)

        # 更新时间戳
        USER_PROFILES[nickname]['last_update'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 保存
        if save_profiles():
            print(f"\n✅ 体重更新成功！")
            print(f"📉 变化: {round(new_weight - old_weight, 1)}kg")
            print(f"📊 新BMI: {USER_PROFILES[nickname]['bmi']} ({USER_PROFILES[nickname]['status']})")
            return True
        else:
            print("❌ 更新失败，无法保存数据")
            return False

    except Exception as e:
        print(f"❌ 更新体重时出错: {e}")
        return False


def delete_user_profile(nickname: str) -> bool:
    """
    注销用户档案

    参数:
        nickname: 用户昵称

    返回值:
        bool: 删除是否成功
    """
    if nickname not in USER_PROFILES:
        print(f"❌ 你不叫 '{nickname}' ")
        return False

    confirm = input(f"确定要注销 '{nickname}' 吗？(y/N): ").lower()
    if confirm == 'y':
        del USER_PROFILES[nickname]
        if save_profiles():
            print(f"✅ 用户 '{nickname}' 已注销")
            return True
        else:
            print("❌ 注销失败，无法保存数据")
            return False
    else:
        print("❌ 注销操作已取消")
        return False
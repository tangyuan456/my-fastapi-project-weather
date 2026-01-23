# user_manager_sqlite.py
import json
import datetime
from typing import Dict, Any, Optional
from database import HealthDatabaseSQLite


class UserManagerSQLite:
    """基于SQLite的用户管理类"""

    def __init__(self):
        self.db = HealthDatabaseSQLite()
        self.db.connect()

    def create_user_profile(self, user_data: Dict[str, Any]) -> Optional[int]:
        """在SQLite中创建用户档案"""
        try:
            sql = """
            INSERT OR REPLACE INTO users (
                nickname, age, gender, height_cm, current_weight_kg,
                bmi, bmi_status, goal, target_weight_kg,
                diet_preferences, allergens, move_prefer, remarks,
                registration_date, last_update
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # 序列化列表数据
            diet_pref = json.dumps(user_data.get('diet_preferences', []), ensure_ascii=False)
            allergens = json.dumps(user_data.get('allergens', []), ensure_ascii=False)
            move_prefer = json.dumps(user_data.get('move_prefer', []), ensure_ascii=False)

            values = (
                user_data.get('nickname'),
                user_data.get('age'),
                user_data.get('gender'),
                user_data.get('height_cm'),
                user_data.get('current_weight_kg'),
                user_data.get('bmi'),
                user_data.get('status'),
                user_data.get('goal'),
                user_data.get('target_weight_kg'),
                diet_pref,
                allergens,
                move_prefer,
                user_data.get('remarks', ''),
                user_data.get('registration_date', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            self.db.cursor.execute(sql, values)
            self.db.conn.commit()

            # 获取用户ID
            self.db.cursor.execute("SELECT id FROM users WHERE nickname = ?", (user_data.get('nickname'),))
            result = self.db.cursor.fetchone()
            user_id = result['id'] if result else None

            if user_id:
                # 添加初始体重记录
                self.add_weight_record(
                    user_id,
                    user_data.get('current_weight_kg'),
                    user_data.get('bmi'),
                    user_data.get('status')
                )

            print(f"✅ 用户 '{user_data.get('nickname')}' 已成功创建")
            return user_id

        except Exception as e:
            print(f"❌ 创建用户失败: {e}")
            return None

    def get_user_by_nickname(self, nickname: str) -> Optional[Dict[str, Any]]:
        """根据昵称获取用户信息"""
        return self.db.get_user_by_nickname(nickname)

    def update_user_weight(self, nickname: str, new_weight: float) -> bool:
        """更新用户体重"""
        try:
            user = self.get_user_by_nickname(nickname)
            if not user:
                print(f"❌ 用户 '{nickname}' 不存在")
                return False

            user_id = user['id']
            height = user['height_cm']

            # 计算新BMI
            bmi = new_weight / ((height / 100) ** 2)
            bmi = round(bmi, 1)

            if bmi < 18.5:
                status = "偏瘦"
            elif bmi < 24:
                status = "正常"
            elif bmi < 28:
                status = "超重"
            else:
                status = "肥胖"

            # 更新用户表
            update_sql = """
            UPDATE users 
            SET current_weight_kg = ?, bmi = ?, bmi_status = ?, last_update = ?
            WHERE id = ?
            """

            self.db.cursor.execute(update_sql, (
                new_weight, bmi, status,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_id
            ))

            # 添加体重历史记录
            self.add_weight_record(user_id, new_weight, bmi, status)

            self.db.conn.commit()

            print(f"✅ 用户 '{nickname}' 体重更新成功")
            print(f"📊 新体重: {new_weight}kg, BMI: {bmi} ({status})")

            return True

        except Exception as e:
            print(f"❌ 更新体重失败: {e}")
            return False

    def add_weight_record(self, user_id: int, weight: float, bmi: float, status: str) -> bool:
        """添加体重记录"""
        return self.db.add_weight_record(user_id, weight, bmi, status)

    def get_weight_history(self, nickname: str, limit: int = 10) -> list:
        """获取用户的体重历史"""
        return self.db.get_weight_history(nickname, limit)

    def get_all_users(self) -> list:
        """获取所有用户"""
        return self.db.get_all_users()

    def delete_user(self, nickname: str) -> bool:
        """删除用户"""
        try:
            confirm = input(f"确定要删除用户 '{nickname}' 吗？(y/N): ").lower()
            if confirm != 'y':
                print("❌ 删除操作已取消")
                return False

            # 删除用户（由于外键约束，会级联删除相关记录）
            sql = "DELETE FROM users WHERE nickname = ?"
            self.db.cursor.execute(sql, (nickname,))
            self.db.conn.commit()

            if self.db.cursor.rowcount > 0:
                print(f"✅ 用户 '{nickname}' 已删除")
                return True
            else:
                print(f"❌ 用户 '{nickname}' 不存在")
                return False

        except Exception as e:
            print(f"❌ 删除用户失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        self.db.disconnect()


# 演示函数
def demo_sqlite_features():
    """演示SQLite功能"""
    print("🧪 SQLite用户管理器演示")
    print("=" * 50)

    manager = UserManagerSQLite()

    try:
        # 1. 显示现有用户
        users = manager.get_all_users()
        print(f"📋 现有用户数: {len(users)}")

        # 2. 创建测试用户
        test_data = {
            'nickname': 'SQLite测试用户',
            'age': 28,
            'gender': '女',
            'height_cm': 165.0,
            'current_weight_kg': 58.0,
            'bmi': 21.3,
            'status': '正常',
            'goal': '健康减重',
            'diet_preferences': ['清淡少油', '高蛋白'],
            'allergens': ['海鲜'],
            'move_prefer': ['瑜伽', '步行'],
            'remarks': 'SQLite演示用户'
        }

        print("\n➕ 创建测试用户...")
        user_id = manager.create_user_profile(test_data)

        if user_id:
            # 3. 查询用户
            print("\n🔍 查询用户信息...")
            user = manager.get_user_by_nickname('SQLite测试用户')
            if user:
                print(f"  昵称: {user['nickname']}")
                print(f"  年龄: {user['age']}岁")
                print(f"  BMI: {user['bmi']} ({user['bmi_status']})")

            # 4. 更新体重
            print("\n⚖️  模拟体重更新...")
            manager.update_user_weight('SQLite测试用户', 57.5)

            # 5. 查看体重历史
            print("\n📈 查看体重历史...")
            history = manager.get_weight_history('SQLite测试用户', 3)
            for record in history:
                date = record.get('recorded_date', '未知')
                weight = record.get('weight_kg', 'N/A')
                print(f"  {date}: {weight}kg")

        # 6. 显示所有用户
        print("\n👥 所有用户列表:")
        for user in manager.get_all_users():
            print(f"  • {user['nickname']} - {user.get('age', '?')}岁")

    finally:
        manager.close()

    print("\n✅ SQLite演示完成")
    print("💡 数据库文件: health_assistant.db")


if __name__ == "__main__":
    demo_sqlite_features()
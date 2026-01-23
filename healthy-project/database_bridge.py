# database_bridge.py
"""
数据库桥接层 - 在原有JSON系统和数据库系统之间建立桥梁
保持原有功能100%不变，只增加数据库支持
"""

import json
from typing import Dict, List, Optional
from database import HealthDatabaseSQLite
import logging

logger = logging.getLogger(__name__)


class DatabaseBridge:
    """数据库桥接器，让原有代码无需大量修改"""

    def __init__(self):
        # 初始化数据库连接
        self.db = HealthDatabaseSQLite()
        self.connected = self.db.connect()

        if self.connected:
            logger.info("✅ 数据库桥接器初始化成功")
        else:
            logger.warning("⚠️ 数据库连接失败，将只使用JSON系统")

    def sync_user_creation(self, nickname: str, user_data: Dict) -> bool:
        """
        同步用户创建到数据库
        在原有create_user_profile函数被调用后使用
        """
        if not self.connected:
            return False

        try:
            # 转换原有JSON格式到数据库格式
            db_user_data = {
                'nickname': nickname,
                'age': user_data.get('年龄'),
                'gender': user_data.get('性别'),
                'height_cm': user_data.get('身高'),
                'current_weight_kg': user_data.get('当前体重_kg'),
                'bmi': user_data.get('bmi'),
                'bmi_status': user_data.get('status'),
                'goal': user_data.get('目标', '减肥'),
                'target_weight_kg': user_data.get('目标体重_kg'),
                'diet_preferences': json.dumps(user_data.get('饮食偏好', []), ensure_ascii=False),
                'allergens': json.dumps(user_data.get('过敏原', []), ensure_ascii=False),
                'move_prefer': json.dumps(user_data.get('运动爱好', []), ensure_ascii=False),
                'remarks': user_data.get('备注', ''),
                'registration_date': user_data.get('注册时间', '')
            }

            # 保存到数据库
            self.db.cursor.execute("""
                INSERT OR REPLACE INTO users 
                (nickname, age, gender, height_cm, current_weight_kg, bmi, 
                 bmi_status, goal, target_weight_kg, diet_preferences, 
                 allergens, move_prefer, remarks, registration_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(db_user_data.values()))

            self.db.conn.commit()
            logger.info(f"✅ 同步用户到数据库: {nickname}")
            return True

        except Exception as e:
            logger.error(f"❌ 同步用户失败: {e}")
            return False

    def sync_weight_update(self, nickname: str, new_weight: float) -> bool:
        """
        同步体重更新到数据库
        """
        if not self.connected:
            return False

        try:
            # 1. 获取用户ID
            user = self.db.get_user_by_nickname(nickname)
            if not user:
                logger.warning(f"用户不存在于数据库: {nickname}")
                return False

            # 2. 更新用户表的体重
            self.db.cursor.execute("""
                UPDATE users 
                SET current_weight_kg = ?, last_update = ?
                WHERE nickname = ?
            """, (new_weight, '2024-01-01 00:00:00', nickname))

            # 3. 添加到体重历史（简化版）
            self.db.cursor.execute("""
                INSERT INTO weight_history 
                (user_id, weight_kg, recorded_date)
                VALUES (?, ?, ?)
            """, (user['id'], new_weight, '2024-01-01'))

            self.db.conn.commit()
            logger.info(f"✅ 同步体重更新: {nickname} -> {new_weight}kg")
            return True

        except Exception as e:
            logger.error(f"❌ 同步体重失败: {e}")
            return False

    def get_user_count(self) -> int:
        """获取数据库中的用户数量（用于展示）"""
        if not self.connected:
            return 0

        try:
            self.db.cursor.execute("SELECT COUNT(*) as count FROM users")
            result = self.db.cursor.fetchone()
            return result['count'] if result else 0
        except:
            return 0


# 全局实例
db_bridge = DatabaseBridge()
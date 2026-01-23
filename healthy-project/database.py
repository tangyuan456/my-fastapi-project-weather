# database_sqlite.py
import sqlite3
import json
import os
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional
from First_Entry import calculate_bmi

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthDatabaseSQLite:
    """完整的健康助手SQLite数据库管理类"""

    def __init__(self, db_path: str = "health_assistant.db"):
        """
        初始化SQLite数据库

        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self) -> bool:
        """连接到SQLite数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            # 启用外键约束
            self.conn.execute("PRAGMA foreign_keys = ON")
            # 设置行工厂，返回字典格式
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"✅ SQLite数据库连接成功: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"❌ SQLite连接失败: {e}")
            return False

    def disconnect(self):
        """断开数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("已断开数据库连接")

    def create_tables(self) -> bool:
        """创建所有需要的表"""
        try:
            # 1. 用户表
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT UNIQUE NOT NULL,
                age INTEGER,
                gender TEXT,
                height_cm REAL,
                current_weight_kg REAL,
                bmi REAL,
                bmi_status TEXT,
                goal TEXT,
                target_weight_kg REAL,
                diet_preferences TEXT,
                allergens TEXT,
                move_prefer TEXT,
                remarks TEXT,
                registration_date TEXT,
                last_update TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. 体重历史表
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS weight_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                weight_kg REAL NOT NULL,
                bmi REAL,
                bmi_status TEXT,
                recorded_date TEXT NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            # 3. 每日记录表
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                record_date TEXT NOT NULL,
                breakfast_status TEXT DEFAULT '没吃',
                breakfast_details TEXT,
                lunch_status TEXT DEFAULT '没吃',
                lunch_details TEXT,
                dinner_status TEXT DEFAULT '没吃',
                dinner_details TEXT,
                snack_status TEXT DEFAULT '没吃',
                snack_details TEXT,
                exercise_status TEXT DEFAULT '没运动',
                exercise_details TEXT,
                drink_plan INTEGER DEFAULT 8,
                drink_number INTEGER DEFAULT 0,
                food_plan TEXT,
                movement_plan TEXT,
                daily_summary TEXT,
                negative_factors TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, record_date)
            )
            """)

            # 4. 负面因子表
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS negative_factors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                factor_type TEXT NOT NULL,
                description TEXT,
                severity TEXT,
                duration_days INTEGER DEFAULT 1,
                should_exercise INTEGER DEFAULT 1,  -- SQLite用0/1表示布尔
                status TEXT DEFAULT 'active',
                start_date TEXT,
                recovery_date TEXT,
                recovery_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            # 创建索引以提高查询性能
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_weight_user_date ON weight_history(user_id, recorded_date)",
                "CREATE INDEX IF NOT EXISTS idx_daily_user_date ON daily_records(user_id, record_date)",
                "CREATE INDEX IF NOT EXISTS idx_factors_user_status ON negative_factors(user_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_users_nickname ON users(nickname)"
            ]

            for index_sql in indexes:
                self.cursor.execute(index_sql)

            self.conn.commit()
            logger.info("✅ 所有SQLite表创建成功")
            return True

        except Exception as e:
            logger.error(f"❌ 创建表失败: {e}")
            return False

    def migrate_users_from_json(self, json_file: str = "user_profiles.json") -> int:
        """
        从JSON文件迁移用户数据到SQLite数据库

        Returns:
            迁移的用户数量
        """
        if not os.path.exists(json_file):
            logger.warning(f"❌ JSON文件不存在: {json_file}")
            return 0

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)

            migrated_count = 0

            for nickname, user_data in users_data.items():
                # 插入用户数据
                sql = """
                INSERT OR REPLACE INTO users (
                    nickname, age, gender, height_cm, current_weight_kg,
                    bmi, bmi_status, goal, target_weight_kg,
                    diet_preferences, allergens, move_prefer, remarks,
                    registration_date, last_update
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                # 准备数据
                diet_pref = json.dumps(user_data.get('diet_preferences', []), ensure_ascii=False)
                allergens = json.dumps(user_data.get('allergens', []), ensure_ascii=False)
                move_prefer = json.dumps(user_data.get('move_prefer', []), ensure_ascii=False)

                values = (
                    nickname,
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
                    user_data.get('registration_date'),
                    user_data.get('last_update', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )

                self.cursor.execute(sql, values)

                # 获取用户ID
                self.cursor.execute("SELECT id FROM users WHERE nickname = ?", (nickname,))
                result = self.cursor.fetchone()
                user_id = result['id'] if result else None

                # 如果有体重历史JSON文件，迁移体重历史
                if user_id:
                    weight_file = f"weight_history_{nickname}.json"
                    if os.path.exists(weight_file):
                        self._migrate_weight_history(user_id, nickname, weight_file)

                migrated_count += 1
                logger.info(f"✅ 迁移用户: {nickname}")

            self.conn.commit()
            logger.info(f"🎉 总计迁移 {migrated_count} 个用户")
            return migrated_count

        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ 迁移用户数据失败: {e}")
            return 0

    def _migrate_weight_history(self, user_id: int, nickname: str, weight_file: str):
        """迁移体重历史数据"""
        try:
            with open(weight_file, 'r', encoding='utf-8') as f:
                weight_data = json.load(f)

            for record in weight_data.get('history', []):
                sql = """
                INSERT OR REPLACE INTO weight_history 
                (user_id, weight_kg, bmi, bmi_status, recorded_date)
                VALUES (?, ?, ?, ?, ?)
                """

                # 解析记录日期
                record_date = record.get('up_date', datetime.now().strftime("%Y-%m-%d"))
                if ' ' in record_date:
                    record_date = record_date.split(' ')[0]

                values = (
                    user_id,
                    record.get('weight_kg'),
                    record.get('bmi'),
                    record.get('status'),
                    record_date
                )

                self.cursor.execute(sql, values)

            logger.info(f"✅ 迁移用户 {nickname} 的体重历史记录")

        except Exception as e:
            logger.warning(f"⚠️ 迁移体重历史失败 {nickname}: {e}")

    def get_all_users(self) -> List[Dict]:
        """获取所有用户"""
        try:
            self.cursor.execute("""
            SELECT id, nickname, age, gender, height_cm, 
                   current_weight_kg, bmi, bmi_status, goal
            FROM users
            ORDER BY nickname
            """)
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ 获取用户列表失败: {e}")
            return []

    def get_user_by_nickname(self, nickname: str) -> Optional[Dict]:
        """根据昵称获取用户信息"""
        try:
            self.cursor.execute("SELECT * FROM users WHERE nickname = ?", (nickname,))
            row = self.cursor.fetchone()
            if row:
                user_dict = dict(row)
                # 反序列化JSON字段
                for field in ['diet_preferences', 'allergens', 'move_prefer']:
                    if user_dict.get(field):
                        try:
                            user_dict[field] = json.loads(user_dict[field])
                        except:
                            pass
                return user_dict
            return None
        except Exception as e:
            logger.error(f"❌ 查询用户失败: {e}")
            return None

    def add_weight_record(self, user_id: int, weight: float, bmi: float, status: str) -> bool:
        """添加体重记录"""
        try:
            sql = """
            INSERT INTO weight_history 
            (user_id, weight_kg, bmi, bmi_status, recorded_date)
            VALUES (?, ?, ?, ?, ?)
            """

            self.cursor.execute(sql, (
                user_id, weight, bmi, status,
                datetime.now().date().isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ 添加体重记录失败: {e}")
            return False

    def get_weight_history(self, nickname: str, limit: int = 10) -> List[Dict]:
        """获取用户的体重历史"""
        try:
            # 先获取用户ID
            user = self.get_user_by_nickname(nickname)
            if not user:
                return []

            self.cursor.execute("""
            SELECT weight_kg, bmi, bmi_status, recorded_date, recorded_at
            FROM weight_history
            WHERE user_id = ?
            ORDER BY recorded_date DESC
            LIMIT ?
            """, (user['id'], limit))

            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"❌ 获取体重历史失败: {e}")
            return []

    def test_connection(self) -> bool:
        """测试数据库连接和基本功能"""
        try:
            # 测试连接
            if not self.connect():
                return False

            # 测试查询
            self.cursor.execute("SELECT sqlite_version()")
            version = self.cursor.fetchone()[0]
            logger.info(f"SQLite版本: {version}")

            # 显示表信息
            self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
            """)
            tables = self.cursor.fetchall()
            logger.info("数据库表:")
            for table in tables:
                logger.info(f"  - {table['name']}")

            # 统计用户数量
            self.cursor.execute("SELECT COUNT(*) as count FROM users")
            count = self.cursor.fetchone()['count']
            logger.info(f"用户数量: {count}")

            return True

        except Exception as e:
            logger.error(f"❌ 数据库测试失败: {e}")
            return False
        finally:
            self.disconnect()


    def update_meal_status(self, user_id: int, meal_type: str,
                           status: str = "吃了", details: str = "") -> bool:
        """
        更新用户的用餐状态（对应你的update_meal_status工具）

        Args:
            user_id: 用户ID
            meal_type: 餐次类型 ('breakfast', 'lunch', 'dinner', 'snack')
            status: 状态 ('吃了', '没吃')
            details: 食物详情

        Returns:
            bool: 是否成功
        """
        try:
            today = datetime.now().date().isoformat()

            # 1. 确保今日记录存在
            self.ensure_daily_record_exists(user_id, today)

            # 2. 确定要更新的字段
            status_field = f"{meal_type}_status"
            details_field = f"{meal_type}_details"

            # 3. 更新记录
            sql = f"""
            UPDATE daily_records 
            SET {status_field} = ?, {details_field} = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND record_date = ?
            """

            self.cursor.execute(sql, (status, details, user_id, today))
            self.conn.commit()

            logger.info(f"✅ 更新{meal_type}状态: {status}")
            return True

        except Exception as e:
            logger.error(f"❌ 更新用餐状态失败: {e}")
            return False

    def ensure_daily_record_exists(self, user_id: int, date_str: str) -> bool:
        """确保某天的记录存在"""
        try:
            # 检查记录是否存在
            self.cursor.execute(
                "SELECT id FROM daily_records WHERE user_id = ? AND record_date = ?",
                (user_id, date_str)
            )

            if not self.cursor.fetchone():
                # 创建新记录
                sql = """
                INSERT INTO daily_records (user_id, record_date)
                VALUES (?, ?)
                """
                self.cursor.execute(sql, (user_id, date_str))
                self.conn.commit()
                logger.info(f"✅ 创建每日记录: 用户{user_id}, 日期{date_str}")

            return True
        except Exception as e:
            logger.error(f"❌ 创建每日记录失败: {e}")
            return False

    def update_exercise_status(self, user_id: int,
                               status: str = "已运动", details: str = "") -> bool:
        """
        更新运动状态（对应你的update_exercise_status工具）
        """
        try:
            today = datetime.now().date().isoformat()

            # 确保今日记录存在
            self.ensure_daily_record_exists(user_id, today)

            # 更新运动状态
            sql = """
            UPDATE daily_records 
            SET exercise_status = ?, exercise_details = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND record_date = ?
            """

            self.cursor.execute(sql, (status, details, user_id, today))
            self.conn.commit()

            logger.info(f"✅ 更新运动状态: {status}")
            return True

        except Exception as e:
            logger.error(f"❌ 更新运动状态失败: {e}")
            return False

    def add_negative_factor(self, user_id: int, factor_data: Dict) -> int:
        """
        添加负面因子记录（对应你的detect_and_record_negative_factors工具）

        Returns:
            int: 新记录的ID
        """
        try:
            sql = """
            INSERT INTO negative_factors 
            (user_id, factor_type, description, severity, duration_days, 
             should_exercise, status, start_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """

            should_exercise = 1 if factor_data.get('should_exercise', True) else 0

            values = (
                user_id,
                factor_data.get('factor_type', '其他'),
                factor_data.get('description', ''),
                factor_data.get('severity', '轻'),
                factor_data.get('duration_days', 1),
                should_exercise,
                factor_data.get('status', 'active'),
                datetime.now().date().isoformat()
            )

            self.cursor.execute(sql, values)
            self.conn.commit()

            factor_id = self.cursor.lastrowid
            logger.info(f"✅ 添加负面因子: ID={factor_id}, 类型={values[2]}")
            return factor_id

        except Exception as e:
            logger.error(f"❌ 添加负面因子失败: {e}")
            return 0

    def get_today_plan(self, user_id: int, plan_type: str = "all") -> Dict:
        """
        获取今日计划（对应你的get_daily_plan工具）

        Args:
            plan_type: 'food'=饮食计划, 'movement'=运动计划, 'all'=全部

        Returns:
            Dict: 计划数据
        """
        try:
            today = datetime.now().date().isoformat()

            # 获取今日记录
            self.cursor.execute("""
            SELECT food_plan, movement_plan, 
                   breakfast_status, lunch_status, dinner_status,
                   drink_plan, drink_number, exercise_status
            FROM daily_records
            WHERE user_id = ? AND record_date = ?
            """, (user_id, today))

            row = self.cursor.fetchone()

            if not row:
                # 如果没有记录，创建默认记录
                self.ensure_daily_record_exists(user_id, today)
                return self._get_default_plan()

            # 解析JSON字段
            food_plan = []
            if row['food_plan']:
                try:
                    food_plan = json.loads(row['food_plan'])
                except:
                    food_plan = []

            movement_plan = []
            if row['movement_plan']:
                try:
                    movement_plan = json.loads(row['movement_plan'])
                except:
                    movement_plan = []

            # 构建返回数据
            result = {
                'date': today,
                'meal_status': {
                    '早餐': row['breakfast_status'],
                    '午餐': row['lunch_status'],
                    '晚餐': row['dinner_status']
                },
                'water': {
                    'target': row['drink_plan'] or 8,
                    'current': row['drink_number'] or 0
                },
                'exercise_status': row['exercise_status'] or '未运动'
            }

            # 根据plan_type添加计划
            if plan_type in ['food', 'all'] and food_plan:
                result['food_plan'] = food_plan
            if plan_type in ['movement', 'all'] and movement_plan:
                result['movement_plan'] = movement_plan

            return result

        except Exception as e:
            logger.error(f"❌ 获取今日计划失败: {e}")
            return self._get_default_plan()

    def save_user_to_db(self, user_data: Dict) -> int:
        """保存用户数据到数据库（新增）"""
        try:
            # 准备数据（将原有JSON格式转换为数据库格式）
            sql = """
            INSERT OR REPLACE INTO users 
            (nickname, age, gender, height_cm, current_weight_kg,
             bmi, bmi_status, goal, target_weight_kg,
             diet_preferences, allergens, move_prefer, remarks,
             registration_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # 计算BMI
            height = user_data.get('身高', 0)
            weight = user_data.get('当前体重_kg', 0)
            bmi_info = calculate_bmi(weight, height)  # 需要导入这个函数

            # 序列化列表字段
            diet_pref = json.dumps(user_data.get('饮食偏好', []), ensure_ascii=False)
            allergens = json.dumps(user_data.get('过敏原', []), ensure_ascii=False)
            move_prefer = json.dumps(user_data.get('运动爱好', []), ensure_ascii=False)

            values = (
                user_data.get('昵称'),
                user_data.get('年龄'),
                user_data.get('性别'),
                height,
                weight,
                bmi_info.get('bmi'),
                bmi_info.get('status'),
                user_data.get('目标', '减肥'),
                user_data.get('目标体重_kg', weight),
                diet_pref,
                allergens,
                move_prefer,
                user_data.get('备注', ''),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            self.cursor.execute(sql, values)
            self.conn.commit()

            user_id = self.cursor.lastrowid
            logger.info(f"保存用户到数据库: {user_data.get('昵称')}, ID={user_id}")
            return user_id

        except Exception as e:
            logger.error(f"保存用户失败: {e}")
            return 0

    def update_user_weight(self, user_id: int, weight: float, bmi_info: Dict) -> bool:
        """更新用户体重"""
        try:
            # 1. 更新users表
            sql = """
            UPDATE users 
            SET current_weight_kg = ?, bmi = ?, bmi_status = ?, last_update = ?
            WHERE id = ?
            """
            self.cursor.execute(sql, (
                weight,
                bmi_info.get('bmi'),
                bmi_info.get('status'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_id
            ))

            # 2. 添加到体重历史
            self.add_weight_record(
                user_id,
                weight,
                bmi_info.get('bmi'),
                bmi_info.get('status')
            )

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"更新用户体重失败: {e}")
            return False

# 便捷函数
def init_database():
    """初始化数据库（第一次运行时调用）"""
    print("🗄️  初始化SQLite数据库...")
    db = HealthDatabaseSQLite()
    if db.connect():
        if db.create_tables():
            print("✅ 数据库表创建成功")
        else:
            print("❌ 数据库表创建失败")
        db.disconnect()
    else:
        print("❌ 数据库连接失败")


def migrate_all_data():
    """迁移所有JSON数据到数据库"""
    print("🚚 开始迁移JSON数据到SQLite数据库...")
    db = HealthDatabaseSQLite()
    if db.connect():
        count = db.migrate_users_from_json()
        if count > 0:
            print(f"🎉 成功迁移 {count} 个用户的数据")
        else:
            print("⚠️ 没有迁移到用户数据")
        db.disconnect()


def demo_database_features():
    """演示数据库功能"""
    print("=" * 60)
    print("📊 SQLite数据库功能演示")
    print("=" * 60)

    db = HealthDatabaseSQLite()

    if db.test_connection():
        print("✅ 数据库连接测试通过")

        # 展示数据库内容
        db.connect()

        # 显示所有用户
        users = db.get_all_users()
        print(f"\n📋 用户列表 ({len(users)}个):")
        for user in users:
            print(f"  • {user['nickname']} - {user['age']}岁 - BMI: {user.get('bmi', 'N/A')}")

        # 如果有用户，显示体重历史
        if users:
            first_user = users[0]
            history = db.get_weight_history(first_user['nickname'], 3)
            if history:
                print(f"\n📈 用户'{first_user['nickname']}'的体重历史:")
                for record in history:
                    date = record.get('recorded_date', '未知日期')
                    weight = record.get('weight_kg', 'N/A')
                    bmi = record.get('bmi', 'N/A')
                    print(f"  • {date}: {weight}kg (BMI: {bmi})")

        db.disconnect()

        print("\n" + "=" * 60)
        print("🎯 数据库架构总结")
        print("=" * 60)
        print("1. 使用SQLite轻量级数据库")
        print("2. 设计4个核心表：")
        print("   - users (用户档案)")
        print("   - weight_history (体重历史)")
        print("   - daily_records (每日记录)")
        print("   - negative_factors (负面因子)")
        print("3. 支持数据迁移和查询")
        print("4. 为未来扩展奠定基础")
        print("=" * 60)
    else:
        print("❌ 数据库测试失败")


if __name__ == "__main__":
    # 运行演示
    demo_database_features()

    # 询问是否要初始化
    choice = input("\n是否要初始化数据库？(y/N): ").lower()
    if choice == 'y':
        init_database()

        # 询问是否要迁移数据
        choice = input("是否要迁移现有的JSON数据？(y/N): ").lower()
        if choice == 'y':
            migrate_all_data()
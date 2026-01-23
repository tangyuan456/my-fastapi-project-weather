# demo_sqlite.py
"""
答辩演示脚本 - 展示SQLite数据库功能
"""

import os
import json
from datetime import datetime
from database import (
    HealthDatabaseSQLite,
    init_database,
    migrate_all_data,
    demo_database_features
)


def show_database_structure():
    """显示数据库结构"""
    print("\n" + "=" * 60)
    print("🗃️  数据库结构设计")
    print("=" * 60)

    tables = {
        "users": [
            "id (主键)", "nickname (唯一)", "age", "gender", "height_cm",
            "current_weight_kg", "bmi", "bmi_status", "goal", "target_weight_kg",
            "diet_preferences (JSON)", "allergens (JSON)", "move_prefer (JSON)",
            "registration_date", "last_update"
        ],
        "weight_history": [
            "id (主键)", "user_id (外键)", "weight_kg", "bmi", "bmi_status",
            "recorded_date", "recorded_at"
        ],
        "daily_records": [
            "id (主键)", "user_id (外键)", "record_date",
            "breakfast_status", "lunch_status", "dinner_status",
            "drink_plan", "drink_number", "food_plan (JSON)", "movement_plan (JSON)",
            "daily_summary", "negative_factors (JSON)"
        ],
        "negative_factors": [
            "id (主键)", "user_id (外键)", "factor_type", "description",
            "severity", "duration_days", "should_exercise", "status",
            "start_date", "recovery_date", "recovery_notes"
        ]
    }

    for table_name, columns in tables.items():
        print(f"\n📊 {table_name.upper()} 表:")
        for col in columns:
            print(f"   - {col}")

    print("\n🔗 外键关系:")
    print("   users.id → weight_history.user_id")
    print("   users.id → daily_records.user_id")
    print("   users.id → negative_factors.user_id")


def demonstrate_data_migration():
    """演示数据迁移"""
    print("\n" + "=" * 60)
    print("🚚 数据迁移演示")
    print("=" * 60)

    # 检查是否有JSON数据
    json_files = []
    if os.path.exists("user_profiles.json"):
        json_files.append("user_profiles.json")

    # 查找体重历史文件
    import glob
    weight_files = glob.glob("weight_history_*.json")
    json_files.extend(weight_files)

    if json_files:
        print(f"📁 找到 {len(json_files)} 个JSON数据文件:")
        for file in json_files[:3]:  # 只显示前3个
            print(f"  • {file}")

        if len(json_files) > 3:
            print(f"  • ...等{len(json_files) - 3}个文件")

        # 演示迁移
        choice = input("\n是否演示数据迁移？(y/N): ").lower()
        if choice == 'y':
            print("\n迁移过程:")
            print("1. 读取JSON文件")
            print("2. 解析数据")
            print("3. 插入到SQLite数据库")
            print("4. 建立数据关联")

            # 实际执行迁移
            migrate_all_data()
    else:
        print("📭 没有找到JSON数据文件")
        print("💡 您可以先运行健康助手系统创建一些数据")


def show_sql_queries():
    """展示SQL查询示例"""
    print("\n" + "=" * 60)
    print("🔍 SQL查询示例")
    print("=" * 60)

    queries = [
        ("查询所有用户", "SELECT nickname, age, gender, bmi_status FROM users ORDER BY nickname"),
        ("查询体重历史", """
            SELECT u.nickname, wh.recorded_date, wh.weight_kg, wh.bmi
            FROM weight_history wh
            JOIN users u ON wh.user_id = u.id
            ORDER BY wh.recorded_date DESC
            LIMIT 5
        """),
        ("统计BMI分布", """
            SELECT bmi_status, COUNT(*) as count
            FROM users
            GROUP BY bmi_status
            ORDER BY count DESC
        """),
        ("查询今日记录", """
            SELECT record_date, breakfast_status, lunch_status, 
                   dinner_status, drink_number
            FROM daily_records
            WHERE record_date = DATE('now')
        """)
    ]

    for i, (description, query) in enumerate(queries, 1):
        print(f"\n{i}. {description}:")
        print(f"   ```sql")
        print(f"   {query.strip()}")
        print(f"   ```")


def demonstrate_performance():
    """演示数据库性能优势"""
    print("\n" + "=" * 60)
    print("⚡ 数据库性能优势")
    print("=" * 60)

    advantages = [
        "• **快速查询**: 索引加速数据检索",
        "• **数据关联**: 外键保证数据一致性",
        "• **复杂查询**: 支持JOIN、GROUP BY等高级操作",
        "• **数据安全**: 事务支持保证数据完整性",
        "• **扩展性**: 轻松支持未来功能扩展",
        "• **备份恢复**: 单文件备份，易于管理"
    ]

    print("数据库相比JSON文件的优势:")
    for advantage in advantages:
        print(f"  {advantage}")

    print("\n📊 实际应用场景:")
    print("  1. 快速查找用户历史记录")
    print("  2. 统计用户健康数据趋势")
    print("  3. 关联查询用户的多维度数据")
    print("  4. 保证数据操作的原子性")


def main():
    """主演示函数"""
    print("=" * 70)
    print("🎓 健康助手系统 - 数据库功能答辩演示")
    print("=" * 70)

    # 1. 介绍
    print("\n📋 演示内容:")
    print("  1. 数据库连接和初始化")
    print("  2. 数据库结构设计")
    print("  3. 数据迁移演示")
    print("  4. SQL查询示例")
    print("  5. 性能优势分析")

    input("\n按Enter键开始演示...")

    # 2. 数据库功能演示
    demo_database_features()

    input("\n按Enter键查看数据库结构...")

    # 3. 数据库结构
    show_database_structure()

    input("\n按Enter键查看数据迁移...")

    # 4. 数据迁移
    demonstrate_data_migration()

    input("\n按Enter键查看SQL查询...")

    # 5. SQL查询
    show_sql_queries()

    input("\n按Enter键查看性能优势...")

    # 6. 性能优势
    demonstrate_performance()

    # 7. 总结
    print("\n" + "=" * 70)
    print("🎯 答辩要点总结")
    print("=" * 70)
    print("✅ 已完成:")
    print("  1. SQLite数据库架构设计")
    print("  2. 完整的表结构和关系设计")
    print("  3. 数据迁移方案实现")
    print("  4. 数据库查询功能演示")
    print("  5. 性能优化方案")

    print("\n🚀 技术亮点:")
    print("  • 使用SQLite轻量级数据库")
    print("  • 设计合理的数据表结构")
    print("  • 实现JSON到数据库的数据迁移")
    print("  • 支持复杂查询和数据关联")
    print("  • 为系统扩展奠定基础")

    print("\n💡 答辩陈述:")
    print("  '我的健康助手系统原本使用JSON存储，为了更好的数据管理")
    print("  和查询性能，我设计并实现了SQLite数据库方案。这体现了")
    print("  我的系统架构设计能力和数据库应用能力。'")

    print("\n📁 生成的文件:")
    print("  • health_assistant.db - SQLite数据库文件")
    print("  • database_sqlite.py - 数据库管理模块")
    print("  • user_manager_sqlite.py - 用户管理模块")
    print("  • demo_sqlite.py - 演示脚本")

    print("=" * 70)


if __name__ == "__main__":
    main()
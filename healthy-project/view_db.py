import sqlite3


def view_database():
    conn = None
    try:
        conn = sqlite3.connect('health_assistant.db')
        cursor = conn.cursor()

        # 查看所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            print("数据库中没有表")
            return

        print("数据库中的表：")
        for table in tables:
            table_name = table[0]
            print(f"\n=== 表: {table_name} ===")

            # 查看表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print("表结构:")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                print(f"  {col_name}: {col_type} {'PRIMARY KEY' if pk else ''}")

            # 查看数据
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            if rows:
                print(f"\n数据 ({len(rows)} 行):")
                for row in rows:
                    print(f"  {row}")
            else:
                print("\n表中没有数据")

    except Exception as e:
        print(f"错误: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    view_database()
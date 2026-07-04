#!/usr/bin/env python3
"""
运行数据库迁移脚本
"""
import sqlite3
import os
import sys

def run_migration():
    # 数据库路径
    db_path = os.path.join(os.path.dirname(__file__), 'jarvis.sqlite3')
    migration_path = os.path.join(os.path.dirname(__file__), 'migrations', '004_content_mvp.sql')

    print(f"数据库路径: {db_path}")
    print(f"迁移脚本: {migration_path}")

    # 读取迁移 SQL
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # 使用 executescript 执行整个 SQL 文件（正确处理事务）
        conn.executescript(sql_content)
        print("\n[成功] 迁移完成！")

        # 验证 drafts 表结构
        cursor = conn.execute("PRAGMA table_info(drafts)")
        columns = cursor.fetchall()
        print(f"\ndrafts 表字段（共 {len(columns)} 个）:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        # 验证 prompt_versions 表
        try:
            cursor = conn.execute("PRAGMA table_info(prompt_versions)")
            columns = cursor.fetchall()
            print(f"\nprompt_versions 表字段（共 {len(columns)} 个）:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        except sqlite3.OperationalError:
            print("\nprompt_versions 表不存在")

        # 验证 content_reviews 表
        try:
            cursor = conn.execute("PRAGMA table_info(content_reviews)")
            columns = cursor.fetchall()
            print(f"\ncontent_reviews 表字段（共 {len(columns)} 个）:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        except sqlite3.OperationalError:
            print("\ncontent_reviews 表不存在")

        # 验证现有数据是否保留
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM drafts")
        count = cursor.fetchone()[0]
        print(f"\ndrafts 表现有数据: {count} 条")

    except Exception as e:
        print(f"\n[失败] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()

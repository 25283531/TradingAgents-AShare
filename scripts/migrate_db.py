"""数据库迁移脚本 - 添加缺失的列"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from api.database import SessionLocal, engine, Base

def migrate_database():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("数据库迁移 - 添加缺失列")
        print("=" * 60)
        
        # 检查并添加缺失列
        columns_to_add = [
            ("user_llm_configs", "min_market_cap", "INTEGER DEFAULT 50"),
            ("user_llm_configs", "min_avg_volume", "INTEGER DEFAULT 2"),
            ("user_llm_configs", "min_pe", "INTEGER DEFAULT 0"),
            ("user_llm_configs", "risk_profile", "VARCHAR(20) DEFAULT 'neutral'"),
        ]
        
        for table, column, definition in columns_to_add:
            try:
                # 检查列是否存在
                result = db.execute(
                    text(f"PRAGMA table_info({table})")
                ).fetchall()
                existing_columns = [col[1] for col in result]
                
                if column in existing_columns:
                    print(f"  ✓ {table}.{column} 已存在")
                    continue
                
                # 添加列
                db.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
                db.commit()
                print(f"  ✓ {table}.{column} 添加成功")
            except Exception as e:
                print(f"  ✗ {table}.{column} 添加失败: {e}")
        
        # 验证迁移结果
        print("\n验证迁移结果:")
        result = db.execute(text("PRAGMA table_info(user_llm_configs)")).fetchall()
        columns = [col[1] for col in result]
        required_columns = ["min_market_cap", "min_avg_volume", "min_pe", "risk_profile"]
        
        missing = [col for col in required_columns if col not in columns]
        if missing:
            print(f"  ✗ 仍然缺失列: {missing}")
        else:
            print("  ✓ 所有必需列都已存在")
        
        # 测试查询用户配置
        print("\n测试查询用户配置:")
        try:
            from api.database import UserLLMConfigDB
            users = db.execute("SELECT user_id FROM users LIMIT 2").fetchall()
            for user in users:
                user_id = user[0]
                config = db.query(UserLLMConfigDB).filter(UserLLMConfigDB.user_id == user_id).first()
                if config:
                    print(f"    ✓ 用户 {user_id[:8]}... 的配置查询成功")
                else:
                    print(f"    - 用户 {user_id[:8]}... 没有配置")
        except Exception as e:
            print(f"  ✗ 查询失败: {e}")
        
        print("\n迁移完成!")
        
    except Exception as e:
        db.rollback()
        print(f"\n迁移过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_database()
"""数据库迁移脚本 - 修复Docker容器中缺失的列"""

import sqlite3
import os
import sys

def migrate_database(db_path):
    print("=" * 60)
    print("数据库迁移 - 添加缺失列")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取表的列名
        def get_columns(table):
            cursor.execute(f"PRAGMA table_info({table})")
            return {row[1] for row in cursor.fetchall()}
        
        # 迁移 user_llm_configs 表
        print("\n【1】迁移 user_llm_configs 表")
        llm_columns = get_columns("user_llm_configs")
        llm_migrations = [
            ("min_market_cap", "INTEGER DEFAULT 50"),
            ("min_avg_volume", "INTEGER DEFAULT 2"),
            ("min_pe", "INTEGER DEFAULT 0"),
            ("risk_profile", "VARCHAR(20) DEFAULT 'neutral'"),
        ]
        
        for column, definition in llm_migrations:
            if column in llm_columns:
                print(f"  ✓ {column} 已存在")
            else:
                cursor.execute(f"ALTER TABLE user_llm_configs ADD COLUMN {column} {definition}")
                print(f"  ✓ {column} 添加成功")
        
        # 迁移 reports 表（只添加新增列，原有列已在 _ensure_report_schema() 中处理）
        print("\n【2】迁移 reports 表")
        report_columns = get_columns("reports")
        report_migrations = [
            ("sector_report", "TEXT"),
            ("anti_quant_report", "TEXT"),
            ("investment_plan", "TEXT"),
            ("trader_investment_plan", "TEXT"),
            ("final_trade_decision", "TEXT"),
        ]
        
        for column, definition in report_migrations:
            if column in report_columns:
                print(f"  ✓ {column} 已存在")
            else:
                cursor.execute(f"ALTER TABLE reports ADD COLUMN {column} {definition}")
                print(f"  ✓ {column} 添加成功")
        
        conn.commit()
        
        # 验证
        print("\n【3】验证迁移结果")
        llm_columns = get_columns("user_llm_configs")
        report_columns = get_columns("reports")
        
        llm_required = ["min_market_cap", "min_avg_volume", "min_pe", "risk_profile"]
        report_required = ["sector_report", "anti_quant_report", "investment_plan", 
                          "trader_investment_plan", "final_trade_decision"]
        
        llm_missing = [c for c in llm_required if c not in llm_columns]
        report_missing = [c for c in report_required if c not in report_columns]
        
        if llm_missing:
            print(f"  ✗ user_llm_configs 仍缺失: {llm_missing}")
        else:
            print("  ✓ user_llm_configs 所有列已存在")
        
        if report_missing:
            print(f"  ✗ reports 仍缺失: {report_missing}")
        else:
            print("  ✓ reports 所有列已存在")
        
        print("\n迁移完成!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n迁移失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "./data/tradingagents.db"
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在 {db_path}")
        sys.exit(1)
    
    migrate_database(db_path)
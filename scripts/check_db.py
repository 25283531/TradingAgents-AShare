"""检查数据库状态和用户配置信息"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal, UserDB, UserLLMConfigDB, ImportedPortfolioPositionDB
from sqlalchemy import text

def check_database_status():
    db = SessionLocal()
    try:
        # 检查数据库文件位置
        db_url = os.getenv("DATABASE_URL", "sqlite:///./data/tradingagents.db")
        print(f"数据库路径: {db_url}")
        
        # 检查用户数量
        users = db.query(UserDB).all()
        print(f"\n用户总数: {len(users)}")
        
        for user in users:
            print(f"\n用户: {user.email} (ID: {user.id})")
            
            # 检查用户配置
            config = db.query(UserLLMConfigDB).filter(UserLLMConfigDB.user_id == user.id).first()
            if config:
                print(f"  配置信息:")
                print(f"    - LLM Provider: {config.llm_provider}")
                print(f"    - Deep Think Model: {config.deep_think_llm}")
                print(f"    - Quick Think Model: {config.quick_think_llm}")
                print(f"    - Backend URL: {config.backend_url}")
                print(f"    - Max Debate Rounds: {config.max_debate_rounds}")
                print(f"    - Job Timeout: {config.job_timeout}")
            else:
                print("  配置信息: 无")
            
            # 检查持仓信息
            positions = db.query(ImportedPortfolioPositionDB).filter(
                ImportedPortfolioPositionDB.user_id == user.id
            ).all()
            print(f"  持仓数量: {len(positions)}")
            for pos in positions[:5]:  # 只显示前5个
                print(f"    - {pos.symbol}: {pos.current_position}股 (市值: {pos.market_value})")
        
        # 检查表结构
        print("\n数据库表结构:")
        tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        for table in tables:
            print(f"  - {table[0]}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_database_status()
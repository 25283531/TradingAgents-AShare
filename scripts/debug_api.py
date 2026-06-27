"""调试API连接和配置问题"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal, UserDB, UserLLMConfigDB, ImportedPortfolioPositionDB
from sqlalchemy import text

def debug_api_issues():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("API连接和配置问题诊断")
        print("=" * 60)
        
        # 1. 检查数据库状态
        print("\n【1】数据库状态检查")
        db_url = os.getenv("DATABASE_URL", "sqlite:///./data/tradingagents.db")
        print(f"  数据库路径: {db_url}")
        
        # 检查数据库文件是否存在
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            import pathlib
            db_file = pathlib.Path(db_path)
            if db_file.exists():
                print(f"  ✓ 数据库文件存在")
                print(f"    大小: {db_file.stat().st_size / 1024:.2f} KB")
            else:
                print(f"  ✗ 数据库文件不存在: {db_file}")
        
        # 检查用户表
        users = db.query(UserDB).all()
        print(f"\n  用户数量: {len(users)}")
        for user in users:
            print(f"    - {user.email} (ID: {user.id[:8]}...)")
            
            # 检查用户配置
            config = db.query(UserLLMConfigDB).filter(UserLLMConfigDB.user_id == user.id).first()
            if config:
                print(f"      配置: provider={config.llm_provider}, models={config.quick_think_llm}/{config.deep_think_llm}")
                print(f"      backend_url={config.backend_url}")
                print(f"      has_api_key={bool(config.api_key_encrypted)}")
            else:
                print(f"      配置: 无")
            
            # 检查持仓
            positions = db.query(ImportedPortfolioPositionDB).filter(
                ImportedPortfolioPositionDB.user_id == user.id
            ).all()
            print(f"      持仓数量: {len(positions)}")
        
        # 2. 检查环境变量
        print("\n【2】环境变量检查")
        env_vars = [
            "TA_APP_SECRET_KEY",
            "DATABASE_URL",
            "VITE_API_URL",
            "ALLOW_SERVER_LLM_FALLBACK",
            "CORS_ALLOW_ORIGINS",
        ]
        for var in env_vars:
            value = os.getenv(var)
            if value:
                if var == "TA_APP_SECRET_KEY":
                    print(f"  {var}: {value[:20]}...")
                else:
                    print(f"  {var}: {value}")
            else:
                print(f"  {var}: (未设置)")
        
        # 3. 检查表结构
        print("\n【3】表结构检查")
        tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        table_names = [t[0] for t in tables]
        expected_tables = ["users", "user_llm_configs", "imported_portfolio_positions", "reports"]
        
        for table in expected_tables:
            if table in table_names:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  ✓ {table}: {count} 条记录")
            else:
                print(f"  ✗ {table}: 表不存在")
        
        print("\n诊断完成!")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_api_issues()
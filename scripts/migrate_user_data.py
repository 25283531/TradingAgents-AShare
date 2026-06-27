"""将旧用户的数据迁移到新用户"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal, UserDB, UserLLMConfigDB, ImportedPortfolioPositionDB

def migrate_user_data(old_user_email: str, new_user_email: str):
    """将旧用户的所有数据迁移到新用户"""
    db = SessionLocal()
    try:
        # 查找用户
        old_user = db.query(UserDB).filter(UserDB.email == old_user_email).first()
        new_user = db.query(UserDB).filter(UserDB.email == new_user_email).first()
        
        if not old_user:
            print(f"错误: 未找到旧用户 {old_user_email}")
            return False
        
        if not new_user:
            print(f"错误: 未找到新用户 {new_user_email}")
            return False
        
        print(f"开始迁移数据:")
        print(f"  源用户: {old_user.email} (ID: {old_user.id})")
        print(f"  目标用户: {new_user.email} (ID: {new_user.id})")
        
        # 迁移LLM配置
        old_config = db.query(UserLLMConfigDB).filter(UserLLMConfigDB.user_id == old_user.id).first()
        if old_config:
            new_config = db.query(UserLLMConfigDB).filter(UserLLMConfigDB.user_id == new_user.id).first()
            if not new_config:
                new_config = UserLLMConfigDB(user_id=new_user.id)
                db.add(new_config)
            
            # 复制所有配置字段
            new_config.llm_provider = old_config.llm_provider
            new_config.backend_url = old_config.backend_url
            new_config.quick_think_llm = old_config.quick_think_llm
            new_config.deep_think_llm = old_config.deep_think_llm
            new_config.max_debate_rounds = old_config.max_debate_rounds
            new_config.max_risk_discuss_rounds = old_config.max_risk_discuss_rounds
            new_config.api_key_encrypted = old_config.api_key_encrypted
            new_config.wecom_webhook_encrypted = old_config.wecom_webhook_encrypted
            new_config.default_analysts = old_config.default_analysts
            new_config.job_timeout = old_config.job_timeout
            new_config.stagger_delay = old_config.stagger_delay
            new_config.batch_concurrency = old_config.batch_concurrency
            new_config.min_market_cap = old_config.min_market_cap
            new_config.min_avg_volume = old_config.min_avg_volume
            new_config.min_pe = old_config.min_pe
            new_config.risk_profile = old_config.risk_profile
            
            print("  ✓ LLM配置已迁移")
        
        # 迁移持仓数据
        old_positions = db.query(ImportedPortfolioPositionDB).filter(
            ImportedPortfolioPositionDB.user_id == old_user.id
        ).all()
        
        for old_pos in old_positions:
            # 检查是否已存在
            existing = db.query(ImportedPortfolioPositionDB).filter(
                ImportedPortfolioPositionDB.user_id == new_user.id,
                ImportedPortfolioPositionDB.symbol == old_pos.symbol,
                ImportedPortfolioPositionDB.source == old_pos.source
            ).first()
            
            if existing:
                # 更新现有记录
                existing.current_position = old_pos.current_position
                existing.available_position = old_pos.available_position
                existing.average_cost = old_pos.average_cost
                existing.market_value = old_pos.market_value
                existing.trade_points_json = old_pos.trade_points_json
                existing.trade_points_count = old_pos.trade_points_count
            else:
                # 创建新记录
                new_pos = ImportedPortfolioPositionDB(
                    user_id=new_user.id,
                    symbol=old_pos.symbol,
                    source=old_pos.source,
                    security_name=old_pos.security_name,
                    current_position=old_pos.current_position,
                    available_position=old_pos.available_position,
                    average_cost=old_pos.average_cost,
                    market_value=old_pos.market_value,
                    trade_points_json=old_pos.trade_points_json,
                    trade_points_count=old_pos.trade_points_count,
                )
                db.add(new_pos)
        
        print(f"  ✓ {len(old_positions)} 条持仓记录已迁移")
        
        db.commit()
        print("\n迁移完成!")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python scripts/migrate_user_data.py <旧用户邮箱> <新用户邮箱>")
        print("示例: python scripts/migrate_user_data.py old@example.com new@example.com")
        sys.exit(1)
    
    old_email = sys.argv[1]
    new_email = sys.argv[2]
    migrate_user_data(old_email, new_email)
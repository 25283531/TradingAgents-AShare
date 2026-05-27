"""Trade record service for managing buy/sell transactions."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from api.database import ImportedPortfolioPositionDB, TradeRecordDB

logger = logging.getLogger(__name__)


def record_buy(
    db: Session,
    user_id: str,
    symbol: str,
    security_name: str | None,
    quantity: float,
    price: float,
    fee: float = 0.0,
    tax: float = 0.0,
    notes: str | None = None,
) -> dict[str, Any]:
    """Record a buy transaction and update position.

    Args:
        db: Database session
        user_id: User ID
        symbol: Stock symbol (e.g., '600519.SH')
        security_name: Stock name
        quantity: Number of shares bought (positive)
        price: Price per share
        fee: Transaction fee
        tax: Tax amount
        notes: Optional notes

    Returns:
        Trade record and updated position info
    """
    if quantity <= 0:
        raise ValueError("买入数量必须大于0")
    if price <= 0:
        raise ValueError("买入价格必须大于0")

    now = datetime.now(timezone.utc)
    trade_date = now.strftime("%Y-%m-%d")
    trade_time = now.strftime("%H:%M:%S")

    # Get current position - filter by user_id, source='manual', and symbol
    position = db.query(ImportedPortfolioPositionDB).filter(
        ImportedPortfolioPositionDB.user_id == user_id,
        ImportedPortfolioPositionDB.source == 'manual',
        ImportedPortfolioPositionDB.symbol == symbol,
    ).first()

    position_before = position.current_position if position else 0.0
    average_cost_before = position.average_cost if position else 0.0

    # Calculate new average cost (weighted average, including fee and tax)
    total_cost_before = position_before * (average_cost_before or 0)
    total_cost_add = quantity * price + fee + tax
    total_quantity_after = position_before + quantity

    if total_quantity_after > 0:
        average_cost_after = (total_cost_before + total_cost_add) / total_quantity_after
    else:
        average_cost_after = 0.0

    amount = quantity * price

    # Create trade record
    trade = TradeRecordDB(
        id=uuid4().hex,
        user_id=user_id,
        symbol=symbol,
        security_name=security_name,
        trade_type='buy',
        trade_date=trade_date,
        trade_time=trade_time,
        quantity=quantity,
        price=price,
        amount=amount,
        fee=fee,
        tax=tax,
        position_before=position_before,
        position_after=total_quantity_after,
        average_cost_before=average_cost_before,
        average_cost_after=average_cost_after,
        notes=notes,
    )
    db.add(trade)

    # Update or create position
    if position:
        position.current_position = total_quantity_after
        position.available_position = (position.available_position or 0) + quantity
        position.average_cost = average_cost_after
        position.security_name = security_name or position.security_name
        position.latest_trade_at = f"{trade_date} {trade_time}"
        position.latest_trade_action = 'buy'
        position.trade_points_count = (position.trade_points_count or 0) + 1
    else:
        db.add(ImportedPortfolioPositionDB(
            id=uuid4().hex,
            user_id=user_id,
            source='manual',
            symbol=symbol,
            security_name=security_name,
            current_position=total_quantity_after,
            available_position=quantity,
            average_cost=average_cost_after,
            trade_points_count=1,
            latest_trade_at=f"{trade_date} {trade_time}",
            latest_trade_action='buy',
        ))

    db.commit()

    return _trade_to_dict(trade)


def record_sell(
    db: Session,
    user_id: str,
    symbol: str,
    quantity: float,
    price: float,
    fee: float = 0.0,
    tax: float = 0.0,
    notes: str | None = None,
) -> dict[str, Any]:
    """Record a sell transaction and update position.

    Args:
        db: Database session
        user_id: User ID
        symbol: Stock symbol (e.g., '600519.SH')
        quantity: Number of shares sold (positive)
        price: Price per share
        fee: Transaction fee
        tax: Tax amount
        notes: Optional notes

    Returns:
        Trade record with P&L calculation
    """
    if quantity <= 0:
        raise ValueError("卖出数量必须大于0")
    if price <= 0:
        raise ValueError("卖出价格必须大于0")

    # Get current position - filter by user_id, source='manual', and symbol
    position = db.query(ImportedPortfolioPositionDB).filter(
        ImportedPortfolioPositionDB.user_id == user_id,
        ImportedPortfolioPositionDB.source == 'manual',
        ImportedPortfolioPositionDB.symbol == symbol,
    ).first()

    if not position or (position.current_position or 0) < quantity:
        raise ValueError("持仓不足，无法卖出")

    now = datetime.now(timezone.utc)
    trade_date = now.strftime("%Y-%m-%d")
    trade_time = now.strftime("%H:%M:%S")

    position_before = position.current_position or 0.0
    average_cost_before = position.average_cost or 0.0

    # Calculate P&L
    amount = quantity * price
    cost_basis = quantity * average_cost_before
    pnl = amount - cost_basis - fee - tax
    pnl_pct = (pnl / cost_basis) * 100 if cost_basis > 0 else 0.0

    position_after = position_before - quantity

    # Calculate new average cost (remains unchanged for sell)
    average_cost_after = average_cost_before

    # Create trade record
    trade = TradeRecordDB(
        id=uuid4().hex,
        user_id=user_id,
        symbol=symbol,
        security_name=position.security_name,
        trade_type='sell',
        trade_date=trade_date,
        trade_time=trade_time,
        quantity=quantity,
        price=price,
        amount=amount,
        fee=fee,
        tax=tax,
        position_before=position_before,
        position_after=position_after,
        average_cost_before=average_cost_before,
        average_cost_after=average_cost_after,
        pnl=pnl,
        pnl_pct=pnl_pct,
        notes=notes,
    )
    db.add(trade)

    # Update position
    position.current_position = position_after
    position.available_position = max(0, (position.available_position or 0) - quantity)
    position.latest_trade_at = f"{trade_date} {trade_time}"
    position.latest_trade_action = 'sell'
    position.trade_points_count = (position.trade_points_count or 0) + 1

    db.commit()

    return _trade_to_dict(trade)


def get_trade_history(
    db: Session,
    user_id: str,
    symbol: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Get trade history for a user.

    Args:
        db: Database session
        user_id: User ID
        symbol: Optional symbol filter
        limit: Maximum number of records
        offset: Offset for pagination

    Returns:
        List of trade records
    """
    query = db.query(TradeRecordDB).filter(
        TradeRecordDB.user_id == user_id
    )

    if symbol:
        query = query.filter(TradeRecordDB.symbol == symbol)

    rows = query.order_by(desc(TradeRecordDB.trade_date), desc(TradeRecordDB.trade_time)).offset(offset).limit(limit).all()

    return [_trade_to_dict(row) for row in rows]


def get_trade_summary(
    db: Session,
    user_id: str,
) -> dict[str, Any]:
    """Get trade summary for a user.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Summary statistics
    """
    # Use aggregate queries to avoid loading all records into memory
    total_trades = db.query(func.count(TradeRecordDB.id))\
        .filter(TradeRecordDB.user_id == user_id).scalar() or 0

    buy_trades_count = db.query(func.count(TradeRecordDB.id))\
        .filter(TradeRecordDB.user_id == user_id, TradeRecordDB.trade_type == 'buy').scalar() or 0

    sell_trades_count = db.query(func.count(TradeRecordDB.id))\
        .filter(TradeRecordDB.user_id == user_id, TradeRecordDB.trade_type == 'sell').scalar() or 0

    total_buy_amount = db.query(func.coalesce(func.sum(TradeRecordDB.amount), 0))\
        .filter(TradeRecordDB.user_id == user_id, TradeRecordDB.trade_type == 'buy').scalar()

    total_sell_amount = db.query(func.coalesce(func.sum(TradeRecordDB.amount), 0))\
        .filter(TradeRecordDB.user_id == user_id, TradeRecordDB.trade_type == 'sell').scalar()

    total_fee = db.query(func.coalesce(func.sum(TradeRecordDB.fee), 0))\
        .filter(TradeRecordDB.user_id == user_id).scalar()

    total_tax = db.query(func.coalesce(func.sum(TradeRecordDB.tax), 0))\
        .filter(TradeRecordDB.user_id == user_id).scalar()

    realized_pnl = db.query(func.coalesce(func.sum(TradeRecordDB.pnl), 0))\
        .filter(TradeRecordDB.user_id == user_id, TradeRecordDB.trade_type == 'sell').scalar()

    return {
        'total_trades': total_trades,
        'buy_trades': buy_trades_count,
        'sell_trades': sell_trades_count,
        'total_buy_amount': total_buy_amount,
        'total_sell_amount': total_sell_amount,
        'total_fee': total_fee,
        'total_tax': total_tax,
        'realized_pnl': realized_pnl,
    }


def get_portfolio_summary(
    db: Session,
    user_id: str,
) -> dict[str, Any]:
    """Get portfolio summary including cost basis and current value.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Portfolio summary with cost basis and position info
    """
    positions = db.query(ImportedPortfolioPositionDB).filter(
        ImportedPortfolioPositionDB.user_id == user_id
    ).all()

    total_cost_basis = sum(
        (p.current_position or 0) * (p.average_cost or 0)
        for p in positions
    )
    total_market_value = sum(p.market_value or 0 for p in positions)
    total_position = sum(p.current_position or 0 for p in positions)
    num_symbols = len([p for p in positions if (p.current_position or 0) > 0])

    # Get total invested using aggregate query (sum of all buy amounts)
    total_invested = db.query(func.sum(TradeRecordDB.amount))\
        .filter(TradeRecordDB.user_id == user_id, TradeRecordDB.trade_type == 'buy')\
        .scalar() or 0

    # Get total realized P&L from sells using aggregate query
    realized_pnl = db.query(func.sum(TradeRecordDB.pnl))\
        .filter(TradeRecordDB.user_id == user_id, TradeRecordDB.trade_type == 'sell')\
        .scalar() or 0

    return {
        'num_symbols': num_symbols,
        'total_cost_basis': total_cost_basis,
        'total_market_value': total_market_value,
        'total_position': total_position,
        'total_invested': total_invested,
        'realized_pnl': realized_pnl,
        'unrealized_pnl': total_market_value - total_cost_basis,
    }


def recalculate_positions_from_trades(db: Session, user_id: str, symbol: str) -> dict[str, Any]:
    """Recalculate position for a symbol based on all trade history.

    This recalculates the current position and average cost by replaying
    all trades for the symbol in chronological order.

    Args:
        db: Database session
        user_id: User ID
        symbol: Stock symbol

    Returns:
        Dictionary with recalculated position and cost info
    """
    trades = db.query(TradeRecordDB).filter(
        TradeRecordDB.user_id == user_id,
        TradeRecordDB.symbol == symbol,
    ).order_by(TradeRecordDB.trade_date, TradeRecordDB.trade_time).all()

    if not trades:
        return {
            'current_position': 0.0,
            'average_cost': 0.0,
            'total_cost': 0.0,
        }

    current_position = 0.0
    total_cost = 0.0

    for trade in trades:
        if trade.trade_type == 'buy':
            total_cost_add = trade.quantity * trade.price + (trade.fee or 0) + (trade.tax or 0)
            current_position += trade.quantity
            total_cost += total_cost_add
        elif trade.trade_type == 'sell':
            cost_per_share = total_cost / current_position if current_position > 0 else 0
            total_cost -= trade.quantity * cost_per_share
            current_position -= trade.quantity

    current_position = max(0, current_position)
    average_cost = total_cost / current_position if current_position > 0 else 0.0

    return {
        'current_position': current_position,
        'average_cost': average_cost,
        'total_cost': total_cost,
    }


def delete_trade(db: Session, user_id: str, trade_id: str) -> bool:
    """Delete a trade record and recalculate position.

    After deleting the trade, the position is recalculated based on
    remaining trades to ensure data consistency.

    Args:
        db: Database session
        user_id: User ID
        trade_id: Trade record ID

    Returns:
        True if deleted, False if not found
    """
    trade = db.query(TradeRecordDB).filter(
        TradeRecordDB.id == trade_id,
        TradeRecordDB.user_id == user_id,
    ).first()

    if not trade:
        return False

    symbol = trade.symbol

    db.delete(trade)

    recalc = recalculate_positions_from_trades(db, user_id, symbol)

    position = db.query(ImportedPortfolioPositionDB).filter(
        ImportedPortfolioPositionDB.user_id == user_id,
        ImportedPortfolioPositionDB.source == 'manual',
        ImportedPortfolioPositionDB.symbol == symbol,
    ).first()

    if position:
        position.current_position = recalc['current_position']
        position.average_cost = recalc['average_cost']
        position.available_position = recalc['current_position']
        if recalc['current_position'] <= 0:
            position.available_position = 0
    else:
        if recalc['current_position'] > 0:
            db.add(ImportedPortfolioPositionDB(
                id=uuid4().hex,
                user_id=user_id,
                source='manual',
                symbol=symbol,
                security_name=trade.security_name,
                current_position=recalc['current_position'],
                average_cost=recalc['average_cost'],
                available_position=recalc['current_position'],
            ))

    db.commit()
    return True


def _trade_to_dict(trade: TradeRecordDB) -> dict[str, Any]:
    """Convert TradeRecordDB to dictionary."""
    return {
        'id': trade.id,
        'symbol': trade.symbol,
        'security_name': trade.security_name,
        'trade_type': trade.trade_type,
        'trade_date': trade.trade_date,
        'trade_time': trade.trade_time,
        'quantity': trade.quantity,
        'price': trade.price,
        'amount': trade.amount,
        'fee': trade.fee,
        'tax': trade.tax,
        'position_before': trade.position_before,
        'position_after': trade.position_after,
        'average_cost_before': trade.average_cost_before,
        'average_cost_after': trade.average_cost_after,
        'pnl': trade.pnl,
        'pnl_pct': trade.pnl_pct,
        'notes': trade.notes,
        'created_at': trade.created_at.isoformat() if trade.created_at else None,
    }

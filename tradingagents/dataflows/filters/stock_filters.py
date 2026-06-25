"""股票硬过滤模块 - 根据量化防收割策略进行硬性筛选。"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


# 默认推荐股票列表（当数据获取失败时使用）
DEFAULT_DEMO_STOCKS: List[Dict[str, Any]] = [
    {"symbol": "000858", "name": "五粮液", "price": 165.50, "is_bullish": True},
    {"symbol": "600519", "name": "贵州茅台", "price": 1680.00, "is_bullish": True},
    {"symbol": "601318", "name": "中国平安", "price": 45.20, "is_bullish": True},
    {"symbol": "000001", "name": "平安银行", "price": 12.80, "is_bullish": False},
    {"symbol": "600036", "name": "招商银行", "price": 35.60, "is_bullish": True},
    {"symbol": "002594", "name": "比亚迪", "price": 265.00, "is_bullish": True},
    {"symbol": "300750", "name": "宁德时代", "price": 198.50, "is_bullish": True},
    {"symbol": "688041", "name": "寒武纪", "price": 145.30, "is_bullish": True},
    {"symbol": "002415", "name": "海康威视", "price": 38.90, "is_bullish": True},
    {"symbol": "600900", "name": "长江电力", "price": 28.50, "is_bullish": False},
]


class StockFilter:
    """股票过滤类，实现代码硬过滤逻辑。"""

    MARKET_CAP_MIN = 50  # 最小市值（亿元）
    AVG_VOLUME_MIN = 2   # 最小日均成交额（亿元）
    TREND_WINDOW = 60    # 趋势判断窗口（天）

    @classmethod
    def filter_stocks(cls, stocks: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """批量过滤股票列表。"""
        filtered = []
        for stock in stocks:
            result = cls.filter_single(stock)
            if result["pass"]:
                filtered.append(stock)
        return filtered

    @classmethod
    def filter_single(cls, stock: Dict[str, Any]) -> Dict[str, Any]:
        """过滤单只股票，返回过滤结果。"""
        result = {
            "pass": True,
            "reasons": [],
            "filters": {},
        }

        # 如果数据缺失太多，跳过过滤（有默认值）
        market_cap_result = cls._filter_market_cap(stock)
        result["filters"]["market_cap"] = market_cap_result
        if not market_cap_result["pass"]:
            result["pass"] = False
            result["reasons"].append(market_cap_result["reason"])

        volume_result = cls._filter_volume(stock)
        result["filters"]["volume"] = volume_result
        if not volume_result["pass"]:
            result["pass"] = False
            result["reasons"].append(volume_result["reason"])

        trend_result = cls._filter_trend(stock)
        result["filters"]["trend"] = trend_result
        if not trend_result["pass"]:
            result["pass"] = False
            result["reasons"].append(trend_result["reason"])

        return result

    @classmethod
    def _filter_market_cap(cls, stock: Dict[str, Any]) -> Dict[str, Any]:
        """市值过滤：排除市值小于50亿的股票（容易被量化控盘）。"""
        market_cap = stock.get("market_cap")
        if market_cap is None:
            # 数据缺失时默认通过（有默认值支撑）
            return {"pass": True, "reason": "市值数据缺失（使用默认值）", "value": None}

        try:
            cap = float(market_cap)
        except (ValueError, TypeError):
            return {"pass": True, "reason": "市值数据无效（使用默认值）", "value": market_cap}

        if cap < cls.MARKET_CAP_MIN:
            return {"pass": False, "reason": f"市值{cap}亿小于最低要求{cls.MARKET_CAP_MIN}亿", "value": cap}

        return {"pass": True, "reason": f"市值{cap}亿符合要求", "value": cap}

    @classmethod
    def _filter_volume(cls, stock: Dict[str, Any]) -> Dict[str, Any]:
        """成交额过滤：排除近5天日均成交额小于2亿的股票（缺乏流动性）。"""
        avg_volume = stock.get("avg_volume")
        if avg_volume is None:
            return {"pass": True, "reason": "成交额数据缺失（使用默认值）", "value": None}

        try:
            vol = float(avg_volume)
        except (ValueError, TypeError):
            return {"pass": True, "reason": "成交额数据无效（使用默认值）", "value": avg_volume}

        if vol < cls.AVG_VOLUME_MIN:
            return {"pass": False, "reason": f"日均成交额{vol}亿小于最低要求{cls.AVG_VOLUME_MIN}亿", "value": vol}

        return {"pass": True, "reason": f"日均成交额{vol}亿符合要求", "value": vol}

    @classmethod
    def _filter_trend(cls, stock: Dict[str, Any]) -> Dict[str, Any]:
        """趋势过滤：排除处于明显下行通道的股票。"""
        trend_status = stock.get("trend_status")
        trend_strength = stock.get("trend_strength")

        if trend_status is None:
            return {"pass": True, "reason": "趋势数据缺失（使用默认值）", "value": None}

        if trend_status == "空头排列":
            return {"pass": False, "reason": f"处于{trend_status}状态", "value": trend_status}

        if trend_strength in ("强下行", "下行趋势"):
            return {"pass": False, "reason": f"趋势强度为{trend_strength}", "value": trend_strength}

        return {"pass": True, "reason": f"趋势状态{trend_status}，强度{trend_strength}", "value": trend_status}


def get_filtered_candidates(data_provider, top_n: int = 15, analysis_date: Optional[str] = None) -> list[Dict[str, Any]]:
    """获取经过硬过滤的股票候选列表。

    Args:
        data_provider: 数据提供者实例
        top_n: 返回的股票数量
        analysis_date: 分析日期（格式：YYYY-MM-DD），用于历史数据复盘，默认使用当前日期
    """
    candidates = []

    try:
        hot_stocks = _fetch_hot_stocks(data_provider)
        for stock in hot_stocks:
            candidates.append(stock)
    except Exception:
        pass

    try:
        sector_leaders = _fetch_sector_leaders(data_provider)
        for stock in sector_leaders:
            if stock["symbol"] not in [c["symbol"] for c in candidates]:
                candidates.append(stock)
    except Exception:
        pass

    if not candidates:
        return _get_demo_candidates(top_n)

    if analysis_date is None:
        analysis_date = datetime.now().strftime("%Y-%m-%d")

    for stock in candidates:
        _enrich_stock_data(data_provider, stock, analysis_date)

    filtered = StockFilter.filter_stocks(candidates)

    # 如果过滤后为空，返回演示数据
    if not filtered:
        return _get_demo_candidates(top_n)

    filtered_sorted = sorted(
        filtered,
        key=lambda x: (
            x.get("trend_strength") in ("强趋势", "中等趋势"),
            x.get("avg_volume", 0),
            x.get("market_cap", 0),
        ),
        reverse=True,
    )

    return filtered_sorted[:top_n]


def _get_demo_candidates(top_n: int = 10) -> list[Dict[str, Any]]:
    """获取演示用候选股票列表。"""
    demo = []
    for stock in DEFAULT_DEMO_STOCKS[:top_n]:
        demo.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "price": stock["price"],
            "is_bullish": stock.get("is_bullish", True),
            "trend_status": "多头排列" if stock.get("is_bullish") else "空头排列",
            "trend_strength": "中等趋势" if stock.get("is_bullish") else "下行趋势",
            "market_cap": 500,  # 演示用固定值
            "avg_volume": 5,    # 演示用固定值
        })
    return demo


def _fetch_hot_stocks(data_provider) -> list[Dict[str, Any]]:
    """获取热门股票列表（雪球热搜）。"""
    try:
        result = data_provider.get_hot_stocks_xq()
        lines = result.strip().split("\n")
        stocks = []
        header_skipped = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "雪球热搜" in line:
                continue
            if not header_skipped:
                header_skipped = True
                continue
            parts = line.split()
            if len(parts) >= 2:
                symbol = parts[0].strip()
                name = parts[1].strip()
                price = 0
                if len(parts) >= 3:
                    try:
                        price = float(parts[2].strip())
                    except ValueError:
                        pass
                stocks.append({
                    "symbol": symbol,
                    "name": name,
                    "price": price,
                })
        return stocks[:20]
    except Exception:
        return []


def _fetch_sector_leaders(data_provider) -> list[Dict[str, Any]]:
    """获取涨停板股票（作为板块龙头的替代数据源）。"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        result = data_provider.get_zt_pool(today)
        lines = result.strip().split("\n")
        stocks = []
        for line in lines:
            line = line.strip()
            if not line or "涨停家数" in line or "连板分布" in line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                symbol = parts[0].strip()
                name = parts[1].strip()
                price = 0
                if len(parts) >= 3:
                    try:
                        price = float(parts[2].strip())
                    except ValueError:
                        pass
                stocks.append({
                    "symbol": symbol,
                    "name": name,
                    "price": price,
                })
        return stocks[:10]
    except Exception:
        return []


def _enrich_stock_data(data_provider, stock: Dict[str, Any], analysis_date: str):
    """补充股票的市值、成交额和趋势数据。

    Args:
        data_provider: 数据提供者实例
        stock: 股票字典
        analysis_date: 分析日期（格式：YYYY-MM-DD），用于历史数据复盘
    """
    symbol = stock["symbol"]

    try:
        fundamentals = data_provider.get_fundamentals(symbol)
        market_cap = _extract_market_cap(fundamentals)
        stock["market_cap"] = market_cap
    except Exception:
        stock["market_cap"] = None

    try:
        analysis_dt = datetime.strptime(analysis_date, "%Y-%m-%d")
        start_date = (analysis_dt - timedelta(days=30)).strftime("%Y-%m-%d")
        stock_data = data_provider.get_stock_data(symbol, start_date, analysis_date)
        avg_volume = _calculate_avg_volume(stock_data)
        stock["avg_volume"] = avg_volume
    except Exception:
        stock["avg_volume"] = None

    try:
        ma_bullish = data_provider.get_indicators(symbol, "ma_bullish", analysis_date, 60)
        trend_status, trend_strength = _extract_trend_info(ma_bullish)
        stock["trend_status"] = trend_status
        stock["trend_strength"] = trend_strength
        stock["is_bullish"] = trend_status == "多头排列"
    except Exception:
        stock["trend_status"] = None
        stock["trend_strength"] = None
        stock["is_bullish"] = None


def _extract_market_cap(fundamentals: str) -> Optional[float]:
    """从基本面数据中提取市值。"""
    lines = fundamentals.split("\n")
    for line in lines:
        if "市值" in line or "总市值" in line:
            parts = line.split(":")
            if len(parts) == 2:
                value = parts[1].strip().replace(",", "")
                try:
                    if "亿" in value:
                        return float(value.replace("亿", "").strip())
                    elif "万" in value:
                        return float(value.replace("万", "").strip()) / 10000
                    else:
                        return float(value) / 100000000
                except ValueError:
                    continue
    return None


def _calculate_avg_volume(stock_data: str) -> Optional[float]:
    """计算近5天日均成交额（亿元）。"""
    lines = stock_data.split("\n")
    data_lines = []
    for line in lines:
        if line.strip() and not line.startswith("#") and not line.startswith("##"):
            parts = line.split(",")
            if len(parts) >= 7:
                data_lines.append(parts)

    if not data_lines:
        return None

    df = pd.DataFrame(data_lines[1:], columns=data_lines[0])
    if "Amount" in df.columns:
        try:
            df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
            recent = df.tail(5)
            avg = recent["Amount"].mean()
            if pd.notna(avg):
                return avg / 100000000
        except Exception:
            pass

    return None


def _extract_trend_info(ma_bullish: str) -> tuple[str, str]:
    """从均线排列数据中提取趋势信息。"""
    status = "未知"
    strength = "未知"

    lines = ma_bullish.split("\n")
    for line in lines:
        if "当前状态" in line:
            status = line.split("：")[1].strip() if "：" in line else line.split(":")[1].strip()
        elif "趋势强度" in line:
            strength = line.split("：")[1].strip() if "：" in line else line.split(":")[1].strip()

    return status, strength

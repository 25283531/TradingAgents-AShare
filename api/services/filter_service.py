from typing import Optional, Tuple, Dict, Any
from tradingagents.data.sources.base import DataSource


class FilterResult:
    passed: bool
    reason: str
    metrics: Dict[str, Any]
    
    def __init__(self, passed: bool, reason: str = "", metrics: Optional[Dict[str, Any]] = None):
        self.passed = passed
        self.reason = reason
        self.metrics = metrics or {}


class BaseFilter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def filter(self, symbol: str, data_source: DataSource) -> FilterResult:
        raise NotImplementedError


class MarketCapFilter(BaseFilter):
    def filter(self, symbol: str, data_source: DataSource) -> FilterResult:
        min_market_cap = self.config.get("min_market_cap", 50)
        metrics = {}
        
        try:
            market_cap = data_source.get_market_cap(symbol)
            metrics["market_cap"] = market_cap
            
            if market_cap < min_market_cap * 100000000:
                return FilterResult(
                    passed=False,
                    reason=f"市值{market_cap/100000000:.1f}亿 < {min_market_cap}亿，不符合流动性标准",
                    metrics=metrics
                )
        except Exception as e:
            return FilterResult(
                passed=False,
                reason=f"获取市值数据失败: {str(e)}",
                metrics=metrics
            )
        
        return FilterResult(passed=True, metrics=metrics)


class AvgVolumeFilter(BaseFilter):
    def filter(self, symbol: str, data_source: DataSource) -> FilterResult:
        min_avg_volume = self.config.get("min_avg_volume", 2)
        metrics = {}
        
        try:
            avg_volume = data_source.get_avg_daily_volume(symbol, days=20)
            metrics["avg_volume"] = avg_volume
            
            if avg_volume < min_avg_volume * 100000000:
                return FilterResult(
                    passed=False,
                    reason=f"日均成交额{avg_volume/100000000:.1f}亿 < {min_avg_volume}亿，流动性不足",
                    metrics=metrics
                )
        except Exception as e:
            return FilterResult(
                passed=False,
                reason=f"获取成交额数据失败: {str(e)}",
                metrics=metrics
            )
        
        return FilterResult(passed=True, metrics=metrics)


class PEFilter(BaseFilter):
    def filter(self, symbol: str, data_source: DataSource) -> FilterResult:
        min_pe = self.config.get("min_pe", 0)
        metrics = {}
        
        try:
            pe = data_source.get_pe_ratio(symbol)
            metrics["pe_ratio"] = pe
            
            if pe is not None and pe < min_pe:
                return FilterResult(
                    passed=False,
                    reason=f"市盈率{pe:.1f} < {min_pe}，亏损股风险",
                    metrics=metrics
                )
        except Exception as e:
            return FilterResult(
                passed=False,
                reason=f"获取市盈率数据失败: {str(e)}",
                metrics=metrics
            )
        
        return FilterResult(passed=True, metrics=metrics)


class AntiQuantFilter(BaseFilter):
    def filter(self, symbol: str, data_source: DataSource) -> FilterResult:
        max_turnover = self.config.get("max_turnover", 10)
        max_volatility = self.config.get("max_volatility", 8)
        small_cap_threshold = self.config.get("small_cap_threshold", 100)
        metrics = {}
        
        try:
            avg_turnover = data_source.get_avg_turnover(symbol, days=3)
            market_cap = data_source.get_market_cap(symbol)
            metrics["avg_turnover"] = avg_turnover
            metrics["market_cap"] = market_cap
            
            if avg_turnover > max_turnover and market_cap < small_cap_threshold * 100000000:
                return FilterResult(
                    passed=False,
                    reason=f"近3日平均换手率{avg_turnover:.1f}% > {max_turnover}%且市值{market_cap/100000000:.1f}亿 < {small_cap_threshold}亿，高量化收割风险",
                    metrics=metrics
                )
            
            recent_volatility = data_source.get_recent_volatility(symbol, days=5)
            metrics["recent_volatility"] = recent_volatility
            
            if recent_volatility > max_volatility:
                return FilterResult(
                    passed=False,
                    reason=f"近期振幅{recent_volatility:.1f}% > {max_volatility}%，疑似量化做T割韭菜",
                    metrics=metrics
                )
        except Exception as e:
            return FilterResult(
                passed=False,
                reason=f"获取量化风险指标失败: {str(e)}",
                metrics=metrics
            )
        
        return FilterResult(passed=True, metrics=metrics)


def apply_all_filters(
    symbol: str,
    data_source: DataSource,
    filter_config: Dict[str, Any]
) -> Tuple[bool, str, Dict[str, Any]]:
    filters = [
        MarketCapFilter(filter_config),
        AvgVolumeFilter(filter_config),
        PEFilter(filter_config),
    ]
    
    all_metrics = {}
    reasons = []
    
    for f in filters:
        result = f.filter(symbol, data_source)
        all_metrics.update(result.metrics)
        
        if not result.passed:
            reasons.append(result.reason)
    
    if reasons:
        return False, "; ".join(reasons), all_metrics
    
    return True, "", all_metrics
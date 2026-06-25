import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Minus, ArrowRight, RefreshCw } from 'lucide-react'
import { api } from '@/services/api'
import type { Recommendation } from '@/types'

interface DiscoveryPanelProps {
    onSymbolSelect: (symbol: string) => void
}

export default function DiscoveryPanel({ onSymbolSelect }: DiscoveryPanelProps) {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        setLoading(true)
        setError(null)

        api.getRecommendations()
            .then(res => {
                if (cancelled) return
                setRecommendations(res.stocks)
            })
            .catch(err => {
                if (cancelled) return
                console.error('Failed to load recommendations:', err)
                setError('获取推荐数据失败')
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })

        return () => {
            cancelled = true
        }
    }, [])

    const handleRefresh = () => {
        setLoading(true)
        api.getRecommendations()
            .then(res => {
                setRecommendations(res.stocks)
                setError(null)
            })
            .catch(err => {
                console.error('Failed to refresh recommendations:', err)
                setError('刷新失败')
            })
            .finally(() => {
                setLoading(false)
            })
    }

    const getTrendIcon = (isBullish: boolean | undefined) => {
        if (isBullish === true) return <TrendingUp className="w-4 h-4 text-green-500" />
        if (isBullish === false) return <TrendingDown className="w-4 h-4 text-red-500" />
        return <Minus className="w-4 h-4 text-slate-400" />
    }

    const getTrendLabel = (isBullish: boolean | undefined) => {
        if (isBullish === true) return '多头'
        if (isBullish === false) return '空头'
        return '中性'
    }

    const getTrendClass = (isBullish: boolean | undefined) => {
        if (isBullish === true) return 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300'
        if (isBullish === false) return 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300'
        return 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
    }

    return (
        <div className="h-full flex flex-col bg-white dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700 w-72">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
                <div>
                    <h2 className="font-semibold text-slate-900 dark:text-slate-100">中线趋势股</h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">每日扫描精选</p>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={loading}
                    className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                    {loading ? (
                        <RefreshCw className="w-4 h-4 animate-spin text-slate-400" />
                    ) : (
                        <RefreshCw className="w-4 h-4 text-slate-500" />
                    )}
                </button>
            </div>

            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="flex items-center justify-center h-full text-slate-400">
                        <RefreshCw className="w-5 h-5 animate-spin mr-2" />
                        <span className="text-sm">加载中...</span>
                    </div>
                ) : error ? (
                    <div className="p-4 text-center">
                        <p className="text-sm text-slate-500 dark:text-slate-400">{error}</p>
                        <button
                            onClick={handleRefresh}
                            className="mt-2 text-sm text-blue-600 hover:underline dark:text-blue-400"
                        >
                            重试
                        </button>
                    </div>
                ) : recommendations.length === 0 ? (
                    <div className="p-4 text-center">
                        <p className="text-sm text-slate-500 dark:text-slate-400">暂无推荐数据</p>
                    </div>
                ) : (
                    <div className="divide-y divide-slate-100 dark:divide-slate-700">
                        {recommendations.map((item, index) => (
                            <div
                                key={item.symbol}
                                onClick={() => onSymbolSelect(item.symbol)}
                                className="p-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group"
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-medium text-slate-400 w-5">#{index + 1}</span>
                                            <span className="font-medium text-slate-900 dark:text-slate-100 truncate">
                                                {item.name}
                                            </span>
                                        </div>
                                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                            {item.symbol}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-1 ml-2">
                                        {getTrendIcon(item.is_bullish)}
                                    </div>
                                </div>

                                <div className="mt-2 flex items-center justify-between">
                                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                                        {item.price !== undefined ? `¥${item.price.toFixed(2)}` : '--'}
                                    </span>
                                    <span className={`text-xs px-2 py-0.5 rounded-full ${getTrendClass(item.is_bullish)}`}>
                                        {getTrendLabel(item.is_bullish)}
                                    </span>
                                </div>

                                <div className="mt-2 flex items-center text-xs text-slate-500 dark:text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <span>开始分析</span>
                                    <ArrowRight className="w-3 h-3 ml-1" />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="p-3 border-t border-slate-200 dark:border-slate-700">
                <p className="text-xs text-slate-400 text-center">
                    基于 MA 排列趋势扫描
                </p>
            </div>
        </div>
    )
}

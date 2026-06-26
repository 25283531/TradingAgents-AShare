import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, Minus, ArrowRight, RefreshCw, Search, Filter, X } from 'lucide-react'
import { api } from '@/services/api'
import type { Recommendation } from '@/types'

export default function Discovery() {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterBullish, setFilterBullish] = useState<boolean | null>(null)
    const navigate = useNavigate()
    const isMountedRef = useRef(true)

    useEffect(() => {
        isMountedRef.current = true
        setLoading(true)
        setError(null)

        api.getRecommendations()
            .then(res => {
                if (isMountedRef.current) {
                    setRecommendations(res.stocks)
                }
            })
            .catch(err => {
                if (isMountedRef.current) {
                    console.error('Failed to load recommendations:', err)
                    setError('获取推荐数据失败')
                }
            })
            .finally(() => {
                if (isMountedRef.current) {
                    setLoading(false)
                }
            })

        return () => {
            isMountedRef.current = false
        }
    }, [])

    const handleRefresh = () => {
        setLoading(true)
        api.getRecommendations()
            .then(res => {
                if (isMountedRef.current) {
                    setRecommendations(res.stocks)
                    setError(null)
                }
            })
            .catch(err => {
                if (isMountedRef.current) {
                    console.error('Failed to refresh recommendations:', err)
                    setError('刷新失败')
                }
            })
            .finally(() => {
                if (isMountedRef.current) {
                    setLoading(false)
                }
            })
    }

    const handleSymbolSelect = (symbol: string) => {
        navigate(`/analysis?symbol=${symbol}`)
    }

    const getTrendIcon = (isBullish: boolean | undefined) => {
        if (isBullish === true) return <TrendingUp className="w-5 h-5 text-green-500" />
        if (isBullish === false) return <TrendingDown className="w-5 h-5 text-red-500" />
        return <Minus className="w-5 h-5 text-slate-400" />
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

    const filteredRecommendations = recommendations.filter(item => {
        const matchesSearch = !searchTerm ||
            item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            item.symbol.toLowerCase().includes(searchTerm.toLowerCase())
        const matchesFilter = filterBullish === null || item.is_bullish === filterBullish
        return matchesSearch && matchesFilter
    })

    const bullishCount = recommendations.filter(r => r.is_bullish === true).length
    const bearishCount = recommendations.filter(r => r.is_bullish === false).length
    const neutralCount = recommendations.filter(r => r.is_bullish === undefined).length

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">中线趋势股</h1>
                    <p className="mt-1 text-slate-500 dark:text-slate-400">
                        每日扫描精选，基于 MA 排列趋势分析
                    </p>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-700 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
                >
                    {loading ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                        <RefreshCw className="w-4 h-4" />
                    )}
                    刷新数据
                </button>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-green-200 bg-green-50 px-4 py-4 dark:border-green-500/30 dark:bg-green-500/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-green-100 dark:bg-green-500/20 flex items-center justify-center">
                            <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-green-700 dark:text-green-400">{bullishCount}</p>
                            <p className="text-sm text-green-600/70 dark:text-green-400/70">多头趋势</p>
                        </div>
                    </div>
                </div>
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-4 dark:border-red-500/30 dark:bg-red-500/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-red-100 dark:bg-red-500/20 flex items-center justify-center">
                            <TrendingDown className="w-5 h-5 text-red-600 dark:text-red-400" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-red-700 dark:text-red-400">{bearishCount}</p>
                            <p className="text-sm text-red-600/70 dark:text-red-400/70">空头趋势</p>
                        </div>
                    </div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 dark:border-slate-700 dark:bg-slate-800/50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                            <Minus className="w-5 h-5 text-slate-600 dark:text-slate-400" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-slate-700 dark:text-slate-300">{neutralCount}</p>
                            <p className="text-sm text-slate-600/70 dark:text-slate-400/70">中性趋势</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="card">
                <div className="flex items-center gap-4 mb-4">
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="搜索股票名称或代码..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <Filter className="w-4 h-4 text-slate-400" />
                        <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
                            <button
                                onClick={() => setFilterBullish(null)}
                                className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                                    filterBullish === null
                                        ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm'
                                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                                }`}
                            >
                                全部
                            </button>
                            <button
                                onClick={() => setFilterBullish(true)}
                                className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                                    filterBullish === true
                                        ? 'bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400'
                                        : 'text-slate-500 dark:text-slate-400 hover:text-green-600 dark:hover:text-green-400'
                                }`}
                            >
                                多头
                            </button>
                            <button
                                onClick={() => setFilterBullish(false)}
                                className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                                    filterBullish === false
                                        ? 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400'
                                        : 'text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400'
                                }`}
                            >
                                空头
                            </button>
                        </div>
                        {(searchTerm || filterBullish !== null) && (
                            <button
                                onClick={() => { setSearchTerm(''); setFilterBullish(null) }}
                                className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                            >
                                <X className="w-4 h-4 text-slate-400" />
                            </button>
                        )}
                    </div>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-16 text-slate-400">
                        <RefreshCw className="w-6 h-6 animate-spin mr-3" />
                        <span className="text-sm">加载中...</span>
                    </div>
                ) : error ? (
                    <div className="py-16 text-center">
                        <p className="text-slate-500 dark:text-slate-400">{error}</p>
                        <button
                            onClick={handleRefresh}
                            className="mt-4 text-blue-600 hover:underline dark:text-blue-400"
                        >
                            重试
                        </button>
                    </div>
                ) : filteredRecommendations.length === 0 ? (
                    <div className="py-16 text-center">
                        <p className="text-slate-500 dark:text-slate-400">
                            {searchTerm || filterBullish !== null ? '没有匹配的股票' : '暂无推荐数据'}
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-3">
                        {filteredRecommendations.map((item, index) => (
                            <div
                                key={item.symbol}
                                onClick={() => handleSymbolSelect(item.symbol)}
                                className="flex items-center justify-between p-4 rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800 cursor-pointer hover:border-blue-300 dark:hover:border-blue-500/50 hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-all group"
                            >
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm">
                                        {index + 1}
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-slate-900 dark:text-slate-100">
                                                {item.name}
                                            </span>
                                            <span className="text-xs text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700">
                                                {item.symbol}
                                            </span>
                                        </div>
                                        {item.industry && (
                                            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                                                {item.industry}
                                            </p>
                                        )}
                                    </div>
                                </div>

                                <div className="flex items-center gap-6">
                                    <div className="text-right">
                                        <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                                            {item.price !== undefined ? `¥${item.price.toFixed(2)}` : '--'}
                                        </p>
                                        {item.change !== undefined && (
                                            <p className={`text-xs ${item.change >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                                {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}%
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-2">
                                        {getTrendIcon(item.is_bullish)}
                                        <span className={`text-sm px-3 py-1 rounded-full ${getTrendClass(item.is_bullish)}`}>
                                            {getTrendLabel(item.is_bullish)}
                                        </span>
                                    </div>

                                    <ArrowRight className="w-5 h-5 text-slate-300 dark:text-slate-600 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors" />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="text-center text-xs text-slate-400">
                数据基于 MA 排列趋势扫描，仅供参考，不构成投资建议
            </div>
        </div>
    )
}
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, Minus, ArrowRight, RefreshCw, Search, Filter, X, Play } from 'lucide-react'
import type { Recommendation } from '@/types'

export default function Discovery() {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([])
    const [loading, setLoading] = useState(false)
    const [loaded, setLoaded] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterBullish, setFilterBullish] = useState<boolean | null>(null)
    const [progress, setProgress] = useState(0)
    const [logs, setLogs] = useState<string[]>([])
    const navigate = useNavigate()

    const addLog = (message: string) => {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`])
    }

    const fetchRecommendations = () => {
        if (loading) return
        
        setLoading(true)
        setError(null)
        setProgress(0)
        setLogs([])
        
        addLog('开始获取中线趋势股推荐...')

        // 使用 SSE 获取实时进度
        const eventSource = new EventSource('/api/recommendation/stream')
        
        eventSource.onmessage = (event) => {
            if (event.data === '[DONE]') {
                eventSource.close()
                return
            }
            
            try {
                const data = JSON.parse(event.data)
                
                if (data.type === 'log') {
                    addLog(data.message)
                } else if (data.type === 'progress') {
                    setProgress(data.percent)
                    addLog(`${data.step} (${data.current}/${data.total})`)
                } else if (data.type === 'result') {
                    addLog(`获取到 ${data.stocks.length} 只推荐股票`)
                    setRecommendations(data.stocks)
                    setLoaded(true)
                    setProgress(100)
                    setLoading(false)
                    eventSource.close()
                } else if (data.type === 'error') {
                    addLog(`错误: ${data.message}`)
                    setError(data.message)
                    setLoading(false)
                    eventSource.close()
                }
            } catch (e) {
                console.error('Failed to parse SSE data:', e)
            }
        }
        
        eventSource.onerror = (error) => {
            console.error('SSE error:', error)
            addLog('连接错误，请重试')
            setError('获取推荐数据失败，请检查网络连接')
            setLoading(false)
            eventSource.close()
        }
    }

    const handleSymbolSelect = (symbol: string) => {
        navigate(`/analysis?symbol=${symbol}`)
    }

    const getTrendIcon = (isBullish: boolean | undefined) => {
        if (isBullish === true) return <TrendingUp className="w-5 h-5 text-green-500" />
        if (isBullish === false) return <TrendingDown className="w-5 h-5 text-red-500" />
        return <Minus className="w-5 h-5 text-slate-400" />
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
                    onClick={fetchRecommendations}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-colors disabled:opacity-50"
                >
                    {loading ? (
                        <>
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            分析中...
                        </>
                    ) : (
                        <>
                            <Play className="w-4 h-4" />
                            {loaded ? '重新分析' : '开始分析'}
                        </>
                    )}
                </button>
            </div>

            {loading && (
                <div className="card">
                    <div className="p-8">
                        <div className="flex flex-col items-center justify-center">
                            <div className="relative w-16 h-16 mb-4">
                                <svg className="w-16 h-16 -rotate-90" viewBox="0 0 100 100">
                                    <circle
                                        cx="50"
                                        cy="50"
                                        r="45"
                                        fill="none"
                                        stroke="#e2e8f0"
                                        strokeWidth="8"
                                    />
                                    <circle
                                        cx="50"
                                        cy="50"
                                        r="45"
                                        fill="none"
                                        stroke="#3b82f6"
                                        strokeWidth="8"
                                        strokeDasharray={`${progress * 2.83} 283`}
                                        strokeLinecap="round"
                                        className="transition-all duration-300"
                                    />
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <span className="text-lg font-bold text-blue-600">{Math.round(progress)}%</span>
                                </div>
                            </div>
                            <p className="text-slate-500 dark:text-slate-400">正在扫描市场数据...</p>
                            <p className="text-sm text-slate-400 mt-2">基于 MA 排列和资金流向分析</p>
                        </div>
                        
                        <div className="mt-6 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50 dark:bg-slate-800/50">
                            <div className="px-4 py-2 border-b border-slate-200 dark:border-slate-700 flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                                <span className="text-sm font-medium text-slate-600 dark:text-slate-300">选股流程日志</span>
                            </div>
                            <div className="p-4 h-48 overflow-y-auto font-mono text-sm space-y-1">
                                {logs.map((log, index) => (
                                    <div key={index} className="text-slate-600 dark:text-slate-400">
                                        {log}
                                    </div>
                                ))}
                                {logs.length === 0 && (
                                    <div className="text-slate-400">等待日志...</div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {!loading && !loaded && (
                <div className="card">
                    <div className="p-12 text-center">
                        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center">
                            <TrendingUp className="w-10 h-10 text-blue-600 dark:text-blue-400" />
                        </div>
                        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">准备分析</h2>
                        <p className="text-slate-500 dark:text-slate-400 mb-6">
                            点击上方「开始分析」按钮，系统将基于 MA 排列趋势分析扫描市场，筛选出潜在的中线趋势股。
                        </p>
                        <div className="flex flex-wrap justify-center gap-4 text-sm text-slate-500">
                            <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full">MA 排列分析</span>
                            <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full">资金流向</span>
                            <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full">趋势强度</span>
                        </div>
                    </div>
                </div>
            )}

            {error && (
                <div className="card bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30">
                    <div className="p-4 flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-red-100 dark:bg-red-500/20 flex items-center justify-center">
                            <X className="w-5 h-5 text-red-600 dark:text-red-400" />
                        </div>
                        <div>
                            <p className="font-semibold text-red-700 dark:text-red-400">获取数据失败</p>
                            <p className="text-sm text-red-600 dark:text-red-500">{error}</p>
                        </div>
                        <button
                            onClick={fetchRecommendations}
                            className="ml-auto px-3 py-1.5 text-sm text-red-700 bg-red-100 dark:bg-red-500/20 rounded-lg hover:bg-red-200 dark:hover:bg-red-500/30 transition-colors"
                        >
                            重试
                        </button>
                    </div>
                </div>
            )}

            {loaded && !error && (
                <>
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
                                                ? 'bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400 shadow-sm'
                                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                                        }`}
                                    >
                                        多头
                                    </button>
                                    <button
                                        onClick={() => setFilterBullish(false)}
                                        className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                                            filterBullish === false
                                                ? 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400 shadow-sm'
                                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                                        }`}
                                    >
                                        空头
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            {filteredRecommendations.length > 0 ? (
                                filteredRecommendations.map((stock) => (
                                    <div
                                        key={stock.symbol}
                                        onClick={() => handleSymbolSelect(stock.symbol)}
                                        className="flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-blue-300 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-all cursor-pointer group"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${getTrendClass(stock.is_bullish)}`}>
                                                {getTrendIcon(stock.is_bullish)}
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <span className="font-semibold text-slate-900 dark:text-slate-100">{stock.name}</span>
                                                    <span className="text-sm text-slate-400 dark:text-slate-500">{stock.symbol}</span>
                                                </div>
                                                {stock.industry && (
                                                    <span className="text-xs text-slate-500 dark:text-slate-400">{stock.industry}</span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <div className="text-right">
                                                <p className="font-semibold text-slate-900 dark:text-slate-100">
                                                    {typeof stock.price === 'number' && stock.price > 0 
                                                        ? stock.price.toFixed(2) 
                                                        : '--'}
                                                </p>
                                                {stock.change !== undefined && (
                                                    <p className={`text-sm ${stock.change >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                                        {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                                                    </p>
                                                )}
                                            </div>
                                            <ArrowRight className="w-5 h-5 text-slate-400 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="py-12 text-center">
                                    <p className="text-slate-500 dark:text-slate-400">暂无符合条件的股票</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {logs.length > 0 && (
                        <div className="card">
                            <div className="border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50 dark:bg-slate-800/50">
                                <div className="px-4 py-2 border-b border-slate-200 dark:border-slate-700 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                    <span className="text-sm font-medium text-slate-600 dark:text-slate-300">选股流程日志</span>
                                </div>
                                <div className="p-4 h-48 overflow-y-auto font-mono text-sm space-y-1">
                                    {logs.map((log, index) => (
                                        <div key={index} className="text-slate-600 dark:text-slate-400">
                                            {log}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

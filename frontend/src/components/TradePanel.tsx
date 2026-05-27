import {
    ArrowDownRight,
    ArrowUpRight,
    History,
    Plus,
    X,
    Wallet,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { api } from '@/services/api'
import type { TradeBuyRequest, TradeRecord, TradeSellRequest, PortfolioSummaryResponse } from '@/types'

interface TradePanelProps {
    onTradeComplete: () => void
    trackingItems: any[]
}

type TradeMode = 'buy' | 'sell'

export default function TradePanel({ onTradeComplete, trackingItems }: TradePanelProps) {
    const [tradeMode, setTradeMode] = useState<TradeMode>('buy')
    const [showTradeModal, setShowTradeModal] = useState(false)
    const [tradeHistory, setTradeHistory] = useState<TradeRecord[]>([])
    const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummaryResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [tradeLoading, setTradeLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [formData, setFormData] = useState({
        symbol: '',
        name: '',
        quantity: '',
        price: '',
        fee: '',
        tax: '',
        notes: '',
    })

    const loadData = useCallback(async () => {
        setLoading(true)
        try {
            const [history, summary] = await Promise.all([
                api.getTradeHistory(),
                api.getPortfolioSummary(),
            ])
            setTradeHistory(history)
            setPortfolioSummary(summary)
            setError(null)
        } catch (e) {
            setError(e instanceof Error ? e.message : '加载失败')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        loadData()
    }, [loadData])

    const handleTrade = useCallback(async () => {
        if (!formData.symbol || !formData.quantity || !formData.price) {
            setError('请填写完整信息')
            return
        }

        const quantity = parseFloat(formData.quantity)
        const price = parseFloat(formData.price)
        
        if (quantity <= 0 || price <= 0) {
            setError('数量和价格必须大于0')
            return
        }

        setTradeLoading(true)
        setError(null)

        try {
            if (tradeMode === 'buy') {
                const request: TradeBuyRequest = {
                    symbol: formData.symbol,
                    name: formData.name || undefined,
                    quantity,
                    price,
                    fee: formData.fee ? parseFloat(formData.fee) : 0,
                    tax: formData.tax ? parseFloat(formData.tax) : 0,
                    notes: formData.notes || undefined,
                }
                await api.recordTradeBuy(request)
            } else {
                const request: TradeSellRequest = {
                    symbol: formData.symbol,
                    quantity,
                    price,
                    fee: formData.fee ? parseFloat(formData.fee) : 0,
                    tax: formData.tax ? parseFloat(formData.tax) : 0,
                    notes: formData.notes || undefined,
                }
                await api.recordTradeSell(request)
            }

            setShowTradeModal(false)
            setFormData({
                symbol: '',
                name: '',
                quantity: '',
                price: '',
                fee: '',
                tax: '',
                notes: '',
            })
            await loadData()
            onTradeComplete()
        } catch (e) {
            setError(e instanceof Error ? e.message : '交易失败')
        } finally {
            setTradeLoading(false)
        }
    }, [tradeMode, formData, loadData, onTradeComplete])

    const handleSymbolChange = useCallback((symbol: string) => {
        setFormData(prev => ({ ...prev, symbol }))
        const item = trackingItems.find(i => i.symbol === symbol)
        if (item) {
            setFormData(prev => ({
                ...prev,
                symbol,
                name: item.name || '',
                price: String(item.live_price || item.price || ''),
            }))
        }
    }, [trackingItems])

    const totalPnl = portfolioSummary
        ? portfolioSummary.realized_pnl + portfolioSummary.unrealized_pnl
        : 0
    const totalPnlPct = portfolioSummary && portfolioSummary.total_cost_basis > 0
        ? (totalPnl / portfolioSummary.total_cost_basis) * 100
        : 0

    return (
        <div className="space-y-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-blue-500/12 to-sky-500/10 px-4 py-3 dark:border-blue-500/20">
                    <div className="flex items-center gap-2">
                        <Wallet className="h-4 w-4 text-blue-500" />
                        <p className="text-xs uppercase tracking-[0.14em] text-slate-400">已投入资金</p>
                    </div>
                    <p className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-100">
                        {formatMoney(portfolioSummary?.total_invested || 0)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        累计买入金额
                    </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-emerald-500/12 to-teal-500/10 px-4 py-3 dark:border-emerald-500/20">
                    <div className="flex items-center gap-2">
                        <Plus className="h-4 w-4 text-emerald-500" />
                        <p className="text-xs uppercase tracking-[0.14em] text-slate-400">持仓标的</p>
                    </div>
                    <p className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-100">
                        {portfolioSummary?.num_symbols || 0} 只
                    </p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        当前持有股票数量
                    </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-rose-500/12 to-orange-500/10 px-4 py-3 dark:border-rose-500/20">
                    <div className="flex items-center gap-2">
                        <ArrowUpRight className="h-4 w-4 text-rose-500" />
                        <p className="text-xs uppercase tracking-[0.14em] text-slate-400">总盈利率</p>
                    </div>
                    <p className={`mt-2 text-xl font-semibold ${totalPnl >= 0 ? 'text-rose-600' : 'text-emerald-600'} dark:text-slate-100`}>
                        {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
                    </p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        已实现 + 浮动盈亏
                    </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-amber-500/12 to-orange-500/10 px-4 py-3 dark:border-amber-500/20">
                    <div className="flex items-center gap-2">
                        <ArrowDownRight className="h-4 w-4 text-amber-500" />
                        <p className="text-xs uppercase tracking-[0.14em] text-slate-400">总盈利金额</p>
                    </div>
                    <p className={`mt-2 text-xl font-semibold ${totalPnl >= 0 ? 'text-rose-600' : 'text-emerald-600'} dark:text-slate-100`}>
                        {totalPnl >= 0 ? '+' : ''}{formatMoney(totalPnl)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        已实现 {formatMoney(portfolioSummary?.realized_pnl || 0)} + 浮动 {formatMoney(portfolioSummary?.unrealized_pnl || 0)}
                    </p>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3">
                <button
                    type="button"
                    onClick={() => {
                        setTradeMode('buy')
                        setShowTradeModal(true)
                    }}
                    className="inline-flex items-center gap-2 rounded-xl bg-rose-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-rose-600"
                >
                    <ArrowUpRight className="h-4 w-4" />
                    买入
                </button>
                <button
                    type="button"
                    onClick={() => {
                        setTradeMode('sell')
                        setShowTradeModal(true)
                    }}
                    className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-600"
                >
                    <ArrowDownRight className="h-4 w-4" />
                    卖出
                </button>
            </div>

            {/* Trade History */}
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <div className="flex items-center gap-2">
                    <History className="h-4 w-4 text-slate-400" />
                    <h3 className="text-sm font-medium text-slate-700 dark:text-slate-200">交易记录</h3>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-8 text-slate-500 dark:text-slate-400">
                        加载中...
                    </div>
                ) : tradeHistory.length === 0 ? (
                    <div className="py-8 text-center text-slate-500 dark:text-slate-400">
                        暂无交易记录
                    </div>
                ) : (
                    <div className="mt-4 overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-700">
                                    <th className="text-left py-2 px-3 text-xs font-medium uppercase tracking-wider text-slate-400">日期</th>
                                    <th className="text-left py-2 px-3 text-xs font-medium uppercase tracking-wider text-slate-400">时间</th>
                                    <th className="text-left py-2 px-3 text-xs font-medium uppercase tracking-wider text-slate-400">股票</th>
                                    <th className="text-left py-2 px-3 text-xs font-medium uppercase tracking-wider text-slate-400">操作</th>
                                    <th className="text-right py-2 px-3 text-xs font-medium uppercase tracking-wider text-slate-400">数量</th>
                                    <th className="text-right py-2 px-3 text-xs font-medium uppercase tracking-wider text-slate-400">价格</th>
                                    <th className="text-right py-2 px-3 text-xs font-medium uppercase tracking-wider text-slate-400">金额</th>
                                    <th className="text-right py-2 px-3 text-xs font-medium uppercase tracking-wider text-slate-400">盈亏</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tradeHistory.map(trade => (
                                    <tr key={trade.id} className="border-b border-slate-100 dark:border-slate-800 last:border-0">
                                        <td className="py-3 px-3 text-slate-600 dark:text-slate-300">{trade.trade_date}</td>
                                        <td className="py-3 px-3 text-slate-500 dark:text-slate-400">{trade.trade_time}</td>
                                        <td className="py-3 px-3">
                                            <div className="font-medium text-slate-900 dark:text-slate-100">{trade.security_name || trade.symbol}</div>
                                            <div className="text-xs text-slate-400">{trade.symbol}</div>
                                        </td>
                                        <td className="py-3 px-3">
                                            <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                                                trade.trade_type === 'buy'
                                                    ? 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-300'
                                                    : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-300'
                                            }`}>
                                                {trade.trade_type === 'buy' ? '买入' : '卖出'}
                                            </span>
                                        </td>
                                        <td className="py-3 px-3 text-right text-slate-600 dark:text-slate-300">{trade.quantity}</td>
                                        <td className="py-3 px-3 text-right text-slate-600 dark:text-slate-300">{trade.price.toFixed(2)}</td>
                                        <td className="py-3 px-3 text-right font-medium text-slate-900 dark:text-slate-100">
                                            {formatMoney(trade.amount)}
                                        </td>
                                        <td className="py-3 px-3 text-right">
                                            {trade.trade_type === 'sell' && trade.pnl != null ? (
                                                <div className={`font-medium ${trade.pnl >= 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                                    {trade.pnl >= 0 ? '+' : ''}{formatMoney(trade.pnl)}
                                                    <span className="ml-1 text-xs">({trade.pnl_pct >= 0 ? '+' : ''}{trade.pnl_pct?.toFixed(2)}%)</span>
                                                </div>
                                            ) : (
                                                <span className="text-slate-400">-</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Trade Modal */}
            {showTradeModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div className="absolute inset-0 bg-black/50" onClick={() => setShowTradeModal(false)} />
                    <div className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-700 dark:bg-slate-900">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                                {tradeMode === 'buy' ? '买入股票' : '卖出股票'}
                            </h2>
                            <button
                                type="button"
                                onClick={() => setShowTradeModal(false)}
                                className="rounded-full p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        {error && (
                            <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300">
                                {error}
                            </div>
                        )}

                        <div className="mt-6 space-y-4">
                            <div>
                                <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
                                    股票代码
                                </label>
                                <select
                                    value={formData.symbol}
                                    onChange={e => handleSymbolChange(e.target.value)}
                                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                >
                                    <option value="">请选择股票</option>
                                    {trackingItems.map(item => (
                                        <option key={item.symbol} value={item.symbol}>
                                            {item.symbol} - {item.name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
                                    股票名称
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                    placeholder="股票名称"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
                                        数量（股）
                                    </label>
                                    <input
                                        type="number"
                                        value={formData.quantity}
                                        onChange={e => setFormData(prev => ({ ...prev, quantity: e.target.value }))}
                                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                        placeholder="数量"
                                        min="0"
                                        step="100"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
                                        价格（元）
                                    </label>
                                    <input
                                        type="number"
                                        value={formData.price}
                                        onChange={e => setFormData(prev => ({ ...prev, price: e.target.value }))}
                                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                        placeholder="价格"
                                        min="0"
                                        step="0.01"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
                                        手续费
                                    </label>
                                    <input
                                        type="number"
                                        value={formData.fee}
                                        onChange={e => setFormData(prev => ({ ...prev, fee: e.target.value }))}
                                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                        placeholder="0"
                                        min="0"
                                        step="0.01"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
                                        税费
                                    </label>
                                    <input
                                        type="number"
                                        value={formData.tax}
                                        onChange={e => setFormData(prev => ({ ...prev, tax: e.target.value }))}
                                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                        placeholder="0"
                                        min="0"
                                        step="0.01"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
                                    备注
                                </label>
                                <textarea
                                    value={formData.notes}
                                    onChange={e => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 min-h-[60px]"
                                    placeholder="备注信息（可选）"
                                />
                            </div>

                            {/* Preview */}
                            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
                                <p className="text-xs font-medium text-slate-500 dark:text-slate-400">交易预览</p>
                                <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                                    <div>
                                        <span className="text-slate-400">预估金额：</span>
                                        <span className="font-medium text-slate-900 dark:text-slate-100">
                                            {formatMoney((parseFloat(formData.quantity) || 0) * (parseFloat(formData.price) || 0))}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-slate-400">费用合计：</span>
                                        <span className="font-medium text-slate-900 dark:text-slate-100">
                                            {formatMoney((parseFloat(formData.fee) || 0) + (parseFloat(formData.tax) || 0))}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <button
                                type="button"
                                onClick={handleTrade}
                                disabled={tradeLoading}
                                className={`w-full rounded-xl px-4 py-3 text-sm font-medium text-white transition-colors ${
                                    tradeMode === 'buy'
                                        ? 'bg-rose-500 hover:bg-rose-600'
                                        : 'bg-emerald-500 hover:bg-emerald-600'
                                } disabled:opacity-50 disabled:cursor-not-allowed`}
                            >
                                {tradeLoading ? '处理中...' : `${tradeMode === 'buy' ? '确认买入' : '确认卖出'}`}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

function formatMoney(value: number): string {
    if (!Number.isFinite(value)) return '--'
    if (Math.abs(value) >= 100000000) {
        return `${(value / 100000000).toFixed(2)}亿`
    }
    if (Math.abs(value) >= 10000) {
        return `${(value / 10000).toFixed(2)}万`
    }
    return value.toFixed(2)
}

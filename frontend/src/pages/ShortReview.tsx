import { useEffect, useState } from 'react'
import { RefreshCw, Target, Clock3 } from 'lucide-react'
import { api, LearningStatus } from '@/services/api'

export default function ShortReview() {
    const [data, setData] = useState<LearningStatus | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const load = async () => { setLoading(true); setError(''); try { setData(await api.getLearningStatus()) } catch (e) { setError(e instanceof Error ? e.message : '加载失败') } finally { setLoading(false) } }
    useEffect(() => { void load() }, [])
    return <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex items-center justify-between"><div><h1 className="text-2xl font-bold">短线复盘</h1><p className="mt-1 text-sm text-slate-500">统计 2～5 个交易日预测方向，不代表实际交易收益。</p></div><button className="btn-secondary flex items-center gap-2" onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} />刷新</button></div>
        {error && <div className="card border-red-300 text-red-600">{error}</div>}
        {loading && !data ? <div className="card text-slate-500">正在加载复盘数据...</div> : data && <>
            <div className="grid gap-4 md:grid-cols-4">{[
                { label: '预测数', value: String(data.predictions), Icon: Target },
                { label: '已复盘', value: String(data.resolved), Icon: Clock3 },
                { label: '方向命中率', value: data.directional_hit_rate == null ? '暂无' : `${(data.directional_hit_rate * 100).toFixed(1)}%`, Icon: Target },
                { label: '待复盘', value: String(data.pending.length), Icon: Clock3 },
            ].map(({ label, value, Icon }) => <div className="card" key={label}><Icon className="h-5 w-5 text-blue-500" /><p className="mt-3 text-sm text-slate-500">{label}</p><p className="text-2xl font-bold">{value}</p></div>)}</div>
            <div className="grid gap-6 lg:grid-cols-2"><section className="card"><h2 className="font-semibold">错误类型</h2>{Object.keys(data.error_types).length ? <div className="mt-4 space-y-3">{Object.entries(data.error_types).map(([key, value]) => <div key={key}><div className="flex justify-between text-sm"><span>{key}</span><b>{value}</b></div><div className="mt-1 h-2 rounded bg-slate-100"><div className="h-2 rounded bg-amber-500" style={{ width: `${Math.min(100, value / Math.max(1, data.directional_samples) * 100)}%` }} /></div></div>)}</div> : <p className="mt-4 text-sm text-slate-500">暂无错误样本</p>}</section><section className="card"><h2 className="font-semibold">待复盘预测</h2>{data.pending.length ? <div className="mt-3 divide-y">{data.pending.slice(0, 10).map(item => <div className="flex items-center justify-between py-3 text-sm" key={item.id}><span className="font-medium">{item.symbol}</span><span className="text-slate-500">{item.trade_date} · {item.horizon}日 · {item.action}</span></div>)}</div> : <p className="mt-4 text-sm text-slate-500">没有待复盘预测</p>}</section></div>
            <p className="text-xs text-slate-400">数据指标：{data.metric}</p>
        </>}
    </div>
}

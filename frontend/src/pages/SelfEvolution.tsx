import { useEffect, useState } from 'react'
import { Brain, RefreshCw, ShieldCheck } from 'lucide-react'
import { api, LearningStatus } from '@/services/api'

const labels: Record<string, string> = { market: '市场环境', industry_money: '行业资金', stock_money: '个股资金', relative_strength: '相对强度', liquidity: '流动性', news_policy: '新闻政策', sentiment: '市场情绪', technical: '技术面', expectation_gap: '预期差' }

export default function SelfEvolution() {
    const [data, setData] = useState<LearningStatus | null>(null)
    const [loading, setLoading] = useState(true)
    const load = async () => { setLoading(true); try { setData(await api.getLearningStatus()) } finally { setLoading(false) } }
    useEffect(() => { void load() }, [])
    return <div className="mx-auto max-w-6xl space-y-6"><div className="flex items-center justify-between"><div><h1 className="text-2xl font-bold">自我进化</h1><p className="mt-1 text-sm text-slate-500">系统从已复盘样本中提炼经验，并在时间切分验证后更新因子权重。</p></div><button className="btn-secondary flex items-center gap-2" onClick={() => void load()}><RefreshCw className={loading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} />刷新</button></div>{!data ? <div className="card text-slate-500">正在加载学习状态...</div> : <><div className="card flex items-center gap-4"><Brain className="h-8 w-8 text-indigo-500" /><div><p className="text-sm text-slate-500">当前策略版本</p><p className="text-xl font-bold">{data.policy.id == null ? '基础规则' : `版本 #${data.policy.id}`}</p></div><ShieldCheck className="ml-auto h-6 w-6 text-emerald-500" /></div><section className="card"><h2 className="font-semibold">当前因子权重</h2><div className="mt-5 grid gap-4 md:grid-cols-3">{Object.entries(data.policy.weights).map(([key, value]) => <div key={key}><div className="flex justify-between text-sm"><span>{labels[key] || key}</span><b>{value.toFixed(1)}</b></div><div className="mt-1 h-2 rounded bg-slate-100"><div className="h-2 rounded bg-indigo-500" style={{ width: `${value}%` }} /></div></div>)}</div></section><section className="card"><h2 className="font-semibold">经验提炼</h2>{data.lessons.length ? <div className="mt-3 space-y-3">{data.lessons.map(item => <div className="border-l-2 border-amber-400 pl-3" key={item.error_type}><p className="font-medium">{item.error_type} · {item.samples} 次</p><p className="mt-1 text-sm text-slate-500">{item.guidance}</p></div>)}</div> : <p className="mt-3 text-sm text-slate-500">样本不足，暂不调整策略权重。</p>}</section></>}</div>
}

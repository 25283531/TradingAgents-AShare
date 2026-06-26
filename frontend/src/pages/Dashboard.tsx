import { TrendingUp, Activity, FileText, CheckCircle, ArrowRight, XCircle, Clock, ListTodo, Loader2, TrendingDown, Minus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '@/services/api'
import { useAnalysisStore } from '@/stores/analysisStore'
import { useAuthStore } from '@/stores/authStore'
import type { JobStatus, Report, TrackingBoardResponse } from '@/types'

export default function Dashboard() {
    const { agents, isAnalyzing } = useAnalysisStore()
    const { user } = useAuthStore()
    const [reportTotal, setReportTotal] = useState<number | null>(null)
    const [recentReports, setRecentReports] = useState<Report[]>([])
    const [trackingBoard, setTrackingBoard] = useState<TrackingBoardResponse | null>(null)
    const [dashboardError, setDashboardError] = useState<string | null>(null)
    const [runningJobs, setRunningJobs] = useState<JobStatus[]>([])
    const [recentJobs, setRecentJobs] = useState<JobStatus[]>([])
    const [jobsLoading, setJobsLoading] = useState(false)
    const [cancellingJobId, setCancellingJobId] = useState<string | null>(null)
    const navigate = useNavigate()

    const completedAgents = agents.filter(a => a.status === 'completed').length
    const inProgressAgents = agents.filter(a => a.status === 'in_progress').length

    useEffect(() => {
        if (!user?.id) return
        let cancelled = false

        api.getReports(undefined, 0, 5)
            .then(res => {
                if (cancelled) return
                setReportTotal(res.total)
                setRecentReports(res.reports)
            })
            .catch(error => {
                if (cancelled) return
                console.error('Failed to load recent reports:', error)
                setReportTotal(null)
                setDashboardError(prev => prev || (error instanceof Error ? error.message : '加载控制台数据失败'))
            })

        api.getDashboardTrackingBoard()
            .then(res => {
                if (cancelled) return
                setTrackingBoard(res)
            })

        // 获取运行中的任务
        setJobsLoading(true)
        api.getJobs(undefined, 100, 0)
            .then(res => {
                if (cancelled) return
                const running = res.jobs.filter(j => ['running', 'pending', 'timeout'].includes(j.status))
                const recent = res.jobs
                    .filter(j => j.status === 'completed' || j.status === 'failed')
                    .slice(0, 5)
                setRunningJobs(running)
                setRecentJobs(recent)
            })
            .catch(err => {
                if (cancelled) return
                console.error('Failed to load jobs:', err)
            })
            .finally(() => {
                if (!cancelled) setJobsLoading(false)
            })

        return () => {
            cancelled = true
        }
    }, [user?.id])

    const handleCancelJob = async (jobId: string) => {
        if (!confirm('确定要取消这个任务吗？')) return
        setCancellingJobId(jobId)
        try {
            await api.cancelJob(jobId)
            setRunningJobs(prev => prev.filter(j => j.job_id !== jobId))
        } catch (err) {
            alert(err instanceof Error ? err.message : '取消任务失败')
        } finally {
            setCancellingJobId(null)
        }
    }

    return (
        <div className="space-y-6">
            {dashboardError && (
                    <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
                        {dashboardError}
                    </div>
                )}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">控制台</h1>
                        <p className="mt-1 text-slate-500 dark:text-slate-400">
                            {user?.email ? `当前账户：${user.email}` : '欢迎使用 TradingAgents 智能分析系统'}
                        </p>
                    </div>
                </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                <StatCard
                    icon={Activity}
                    label="Agent 状态"
                    value={`${inProgressAgents} 进行中`}
                    subValue={`${completedAgents} 已完成`}
                    color="blue"
                />
                <StatCard
                    icon={CheckCircle}
                    label="分析任务"
                    value={isAnalyzing ? '分析中' : '空闲'}
                    subValue={isAnalyzing ? '请稍候...' : '准备就绪'}
                    color={isAnalyzing ? 'orange' : 'green'}
                />
                <StatCard
                    icon={FileText}
                    label="累计报告"
                    value={reportTotal !== null ? `${reportTotal}` : '-'}
                    subValue="份分析报告"
                    color="purple"
                />
                <StatCard
                    icon={TrendingUp}
                    label="系统状态"
                    value="正常"
                    subValue="所有服务运行中"
                    color="green"
                />
            </div>

            <TrackingBoardSummary
                trackingBoard={trackingBoard}
                onOpen={() => navigate('/tracking-board')}
            />

            <div className="card">
                <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">快速开始</h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <QuickActionCard
                        title="开始新分析"
                        description="输入股票代码，启动多 Agent 智能分析"
                        action="开始分析"
                        onClick={() => navigate('/analysis')}
                    />
                    <QuickActionCard
                        title="查看历史报告"
                        description="浏览已完成的分析报告"
                        action="查看报告"
                        onClick={() => navigate('/reports')}
                    />
                    <QuickActionCard
                        title="系统设置"
                        description="配置 API 和分析参数"
                        action="打开设置"
                        onClick={() => navigate('/settings')}
                    />
                </div>
            </div>

            <div className="card">
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">最近分析</h2>
                    {recentReports.length > 0 && (
                        <button
                            onClick={() => navigate('/reports')}
                            className="flex items-center gap-1 text-sm text-blue-600 hover:underline dark:text-blue-400"
                        >
                            查看全部 <ArrowRight className="h-3.5 w-3.5" />
                        </button>
                    )}
                </div>

                {recentReports.length === 0 ? (
                    <p className="py-8 text-center text-slate-400 dark:text-slate-500">
                        暂无分析记录，
                        <button onClick={() => navigate('/analysis')} className="text-blue-500 hover:underline">
                            开始新分析
                        </button>
                    </p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-700">
                                    <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">股票</th>
                                    <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">决策</th>
                                    <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">中期趋势强度</th>
                                    <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">行业题材热度</th>
                                    <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">量化收割风险提示</th>
                                    <th className="text-right py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">时间</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                {recentReports.map(report => {
                                    const decisionColor = report.decision?.toUpperCase().includes('BUY') || report.decision?.includes('增持')
                                        ? 'text-red-600 dark:text-red-400'
                                        : report.decision?.toUpperCase().includes('SELL') || report.decision?.includes('减持')
                                            ? 'text-green-600 dark:text-green-400'
                                            : 'text-slate-500 dark:text-slate-400'

                                    const getTrendStrengthIcon = (strength?: string) => {
                                        if (!strength) return <Minus className="w-4 h-4 text-slate-400" />
                                        if (strength.includes('强') || strength.includes('高')) return <TrendingUp className="w-4 h-4 text-green-500" />
                                        if (strength.includes('弱') || strength.includes('低')) return <TrendingDown className="w-4 h-4 text-red-500" />
                                        return <Minus className="w-4 h-4 text-slate-400" />
                                    }

                                    const getHotnessColor = (hotness?: string) => {
                                        if (!hotness) return 'text-slate-400'
                                        if (hotness.includes('热') || hotness.includes('高')) return 'text-red-500 dark:text-red-400'
                                        if (hotness.includes('冷') || hotness.includes('低')) return 'text-blue-500 dark:text-blue-400'
                                        return 'text-slate-500'
                                    }

                                    const getRiskColor = (risk?: string) => {
                                        if (!risk) return 'text-slate-400'
                                        if (risk.includes('高') || risk.includes('风险')) return 'text-red-500 dark:text-red-400'
                                        if (risk.includes('低') || risk.includes('安全')) return 'text-green-500 dark:text-green-400'
                                        return 'text-amber-500 dark:text-amber-400'
                                    }

                                    return (
                                        <tr
                                            key={report.id}
                                            className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
                                            onClick={() => navigate(`/reports?report=${report.id}`)}
                                        >
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-500/10">
                                                        <FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                                    </div>
                                                    <div>
                                                        <p className="font-medium text-slate-900 dark:text-slate-100 text-sm">{report.name || report.symbol}</p>
                                                        <p className="text-xs text-slate-400 dark:text-slate-500">{report.trade_date}</p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className={`text-sm font-medium ${decisionColor}`}>
                                                    {report.decision || '-'}
                                                </span>
                                                {report.confidence != null && (
                                                    <span className="text-xs text-slate-400 ml-2">{report.confidence}%</span>
                                                )}
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-2">
                                                    {getTrendStrengthIcon(report.medium_term_trend_strength)}
                                                    <span className="text-sm text-slate-600 dark:text-slate-300">
                                                        {report.medium_term_trend_strength || '-'}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className={`text-sm ${getHotnessColor(report.sector_topic_hotness)}`}>
                                                    {report.sector_topic_hotness || '-'}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className={`text-sm ${getRiskColor(report.quant_harvest_risk)}`}>
                                                    {report.quant_harvest_risk || '-'}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-right">
                                                <p className="text-xs text-slate-400 dark:text-slate-500">
                                                    {report.created_at ? new Date(report.created_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
                                                </p>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* 任务管理面板 */}
            <div className="card">
                <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <ListTodo className="h-5 w-5 text-slate-500" />
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">任务管理</h2>
                        {jobsLoading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
                    </div>
                    {runningJobs.length > 0 && (
                        <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-700 dark:bg-orange-500/20 dark:text-orange-300">
                            {runningJobs.length} 个任务进行中
                        </span>
                    )}
                </div>

                {/* 运行中/队列中的任务 */}
                {runningJobs.length > 0 ? (
                    <div className="mb-4 space-y-2">
                        <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400">进行中的任务</h3>
                        {runningJobs.map(job => (
                            <div
                                key={job.job_id}
                                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/50"
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                                        job.status === 'running' ? 'bg-blue-100 dark:bg-blue-500/20' :
                                        job.status === 'timeout' ? 'bg-orange-100 dark:bg-orange-500/20' :
                                        'bg-slate-100 dark:bg-slate-700'
                                    }`}>
                                        {job.status === 'running' ? (
                                            <Activity className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                        ) : job.status === 'timeout' ? (
                                            <Clock className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                                        ) : (
                                            <Clock className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                                        )}
                                    </div>
                                    <div>
                                        <p className="font-medium text-slate-900 dark:text-slate-100">{job.symbol}</p>
                                        <p className="text-xs text-slate-500 dark:text-slate-400">
                                            {job.status === 'running' ? '分析中' : job.status === 'timeout' ? '超时等待完成' : '排队中'}
                                            {' · '}
                                            {job.created_at ? new Date(job.created_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
                                        </p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleCancelJob(job.job_id)}
                                    disabled={cancellingJobId === job.job_id}
                                    className="flex items-center gap-1 rounded-lg bg-rose-100 px-3 py-1.5 text-xs font-medium text-rose-700 transition-colors hover:bg-rose-200 disabled:opacity-50 dark:bg-rose-500/20 dark:text-rose-300 dark:hover:bg-rose-500/30"
                                >
                                    {cancellingJobId === job.job_id ? (
                                        <Loader2 className="h-3 w-3 animate-spin" />
                                    ) : (
                                        <XCircle className="h-3 w-3" />
                                    )}
                                    取消
                                </button>
                            </div>
                        ))}
                    </div>
                ) : !jobsLoading && (
                    <p className="py-4 text-center text-sm text-slate-400 dark:text-slate-500">
                        暂无进行中的任务
                    </p>
                )}

                {/* 最近的任务结果 */}
                {recentJobs.length > 0 && (
                    <div className="space-y-2">
                        <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400">最近任务</h3>
                        <div className="divide-y divide-slate-100 dark:divide-slate-700">
                            {recentJobs.map(job => (
                                <div
                                    key={job.job_id}
                                    className="flex cursor-pointer items-center justify-between py-2 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/30"
                                    onClick={() => navigate(`/reports?job=${job.job_id}`)}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                                            job.status === 'completed' ? 'bg-green-100 dark:bg-green-500/20' : 'bg-red-100 dark:bg-red-500/20'
                                        }`}>
                                            {job.status === 'completed' ? (
                                                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                                            ) : (
                                                <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                                            )}
                                        </div>
                                        <div>
                                            <p className="font-medium text-slate-900 dark:text-slate-100">{job.symbol}</p>
                                            <p className="text-xs text-slate-500 dark:text-slate-400">
                                                {job.status === 'completed' ? '已完成' : '失败'}
                                                {job.error && job.status === 'failed' ? ` · ${job.error.slice(0, 20)}` : ''}
                                            </p>
                                        </div>
                                    </div>
                                    <p className="text-xs text-slate-400 dark:text-slate-500">
                                        {job.finished_at ? new Date(job.finished_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
        </div>
)
}

function TrackingBoardSummary({
    trackingBoard,
    onOpen,
}: {
    trackingBoard: TrackingBoardResponse | null
    onOpen: () => void
}) {
    const itemCount = trackingBoard?.items.length ?? 0
    const quotedCount = trackingBoard?.items.filter(item => item.quote_source).length ?? 0
    const latestQuoteTime = trackingBoard?.items
        .map(item => item.quote_time)
        .filter((value): value is string => Boolean(value))[0] ?? null

    return (
        <div className="card">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">跟踪看板摘要</h2>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                        控制台仅展示元数据，持仓明细、区间图和交易建议请进入完整看板查看。
                    </p>
                </div>
                <button
                    type="button"
                    onClick={onOpen}
                    className="flex items-center gap-1 text-sm text-blue-600 hover:underline dark:text-blue-400"
                >
                    查看完整看板 <ArrowRight className="h-3.5 w-3.5" />
                </button>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                <MetaCard
                    label="跟踪标的"
                    value={`${itemCount} 只`}
                    subValue={itemCount > 0 ? `共 ${itemCount} 只标的` : '尚未导入持仓'}
                />
                <MetaCard
                    label="价格覆盖"
                    value={itemCount > 0 ? `${quotedCount}/${itemCount}` : '--'}
                    subValue={trackingBoard ? `刷新间隔 ${trackingBoard.refresh_interval_seconds}s` : '等待看板数据'}
                />
                <MetaCard
                    label="最近更新"
                    value={formatDashboardTime(latestQuoteTime)}
                    subValue={trackingBoard?.previous_trade_date ? `上一交易日 ${trackingBoard.previous_trade_date}` : '暂无交易日信息'}
                />
                <MetaCard
                    label="状态"
                    value={itemCount > 0 ? '已就绪' : '待导入'}
                    subValue={itemCount > 0 ? '明细已收起，点击进入查看' : '前往跟踪看板导入持仓'}
                />
            </div>
        </div>
    )
}

function MetaCard({
    label,
    value,
    subValue,
}: {
    label: string
    value: string
    subValue: string
}) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/40">
            <p className="text-xs uppercase tracking-[0.14em] text-slate-400">{label}</p>
            <p className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{subValue}</p>
        </div>
    )
}

function formatDashboardTime(value?: string | null): string {
    if (!value) return '--'
    const parsed = new Date(value.replace(' ', 'T'))
    if (Number.isNaN(parsed.getTime())) return value
    return parsed.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    })
}

interface StatCardProps {
    icon: React.ComponentType<{ className?: string }>
    label: string
    value: string
    subValue: string
    color: 'blue' | 'green' | 'orange' | 'purple' | 'red'
}

function StatCard({ icon: Icon, label, value, subValue, color }: StatCardProps) {
    const colorClasses = {
        blue: 'bg-blue-100 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400',
        green: 'bg-green-100 dark:bg-green-500/10 text-green-600 dark:text-green-400',
        orange: 'bg-orange-100 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400',
        purple: 'bg-purple-100 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400',
        red: 'bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400',
    }

    return (
        <div className="card card-hover">
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
                    <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
                    <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">{subValue}</p>
                </div>
                <div className={`rounded-lg p-3 ${colorClasses[color]}`}>
                    <Icon className="h-5 w-5" />
                </div>
            </div>
        </div>
    )
}

interface QuickActionCardProps {
    title: string
    description: string
    action: string
    onClick: () => void
}

function QuickActionCard({ title, description, action, onClick }: QuickActionCardProps) {
    return (
        <button
            onClick={onClick}
            className="block w-full rounded-lg border border-slate-200 bg-white p-4 text-left transition-all duration-200 hover:border-blue-400 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800/30 dark:hover:border-blue-500 dark:hover:bg-slate-800/50"
        >
            <h3 className="font-medium text-slate-900 dark:text-slate-100">{title}</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
            <span className="mt-3 inline-block text-sm text-blue-600 dark:text-blue-400">
                {action} →
            </span>
        </button>
    )
}

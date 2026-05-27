import {
    Plus,
    X,
    Search,
    Loader2,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from '@/services/api'
import type { PortfolioPositionInput, StockSearchResult } from '@/types'

interface PositionImportFormProps {
    onSave: (positions: PortfolioPositionInput[]) => void
    onCancel: () => void
}

interface PositionRow {
    id: string
    symbol: string
    name: string
    current_position: string
    average_cost: string
    market_value: string
}

export default function PositionImportForm({ onSave, onCancel }: PositionImportFormProps) {
    const [positions, setPositions] = useState<PositionRow[]>([{
        id: '1',
        symbol: '',
        name: '',
        current_position: '',
        average_cost: '',
        market_value: '',
    }])
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState<StockSearchResult[]>([])
    const [searchLoading, setSearchLoading] = useState(false)
    const [showDropdown, setShowDropdown] = useState(false)
    const [focusedRowId, setFocusedRowId] = useState<string | null>(null)
    const [selectedRowId, setSelectedRowId] = useState<string | null>(null)
    const searchTimerRef = useRef<ReturnType<typeof setTimeout>>()
    const dropdownRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setShowDropdown(false)
                setSelectedRowId(null)
            }
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [])

    useEffect(() => {
        if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
        if (!searchQuery.trim()) {
            setSearchResults([])
            setShowDropdown(false)
            setSearchLoading(false)
            return
        }
        setSearchLoading(true)
        searchTimerRef.current = setTimeout(async () => {
            try {
                const res = await api.searchStocks(searchQuery.trim())
                setSearchResults(res.results)
                setShowDropdown(true)
            } catch {
                setShowDropdown(false)
            }
            setSearchLoading(false)
        }, 300)
    }, [searchQuery])

    const handleStockSelect = useCallback((rowId: string, stock: StockSearchResult) => {
        setPositions(prev => prev.map(row =>
            row.id === rowId
                ? { ...row, symbol: stock.symbol, name: stock.name }
                : row
        ))
        setSearchQuery('')
        setShowDropdown(false)
        setSelectedRowId(rowId)
    }, [])

    const handleAddRow = useCallback(() => {
        const newId = String(Date.now())
        setPositions(prev => [...prev, {
            id: newId,
            symbol: '',
            name: '',
            current_position: '',
            average_cost: '',
            market_value: '',
        }])
    }, [])

    const handleRemoveRow = useCallback((rowId: string) => {
        if (positions.length > 1) {
            setPositions(prev => prev.filter(row => row.id !== rowId))
        }
    }, [positions.length])

    const handleInputChange = useCallback((rowId: string, field: keyof PositionRow, value: string) => {
        setPositions(prev => prev.map(row =>
            row.id === rowId
                ? { ...row, [field]: value }
                : row
        ))
    }, [])

    const handleSubmit = useCallback(() => {
        const validPositions: PortfolioPositionInput[] = positions
            .filter(row => row.symbol.trim() && row.current_position.trim())
            .map(row => ({
                symbol: row.symbol.trim(),
                name: row.name.trim() || undefined,
                current_position: row.current_position.trim() ? Number(row.current_position) : undefined,
                average_cost: row.average_cost.trim() ? Number(row.average_cost) : undefined,
                market_value: row.market_value.trim() ? Number(row.market_value) : undefined,
            }))

        if (validPositions.length === 0) {
            alert('请至少填写一只股票的持仓信息')
            return
        }

        onSave(validPositions)
    }, [positions, onSave])

    return (
        <div className="space-y-4">
            {/* Form Header */}
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-slate-700 dark:text-slate-200">添加持仓</h3>
                <button
                    type="button"
                    onClick={onCancel}
                    className="rounded-full p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>

            {/* Form Body */}
            <div className="space-y-3">
                {positions.map((row, index) => (
                    <div key={row.id} className="group">
                        <div className="flex items-center gap-2">
                            <span className="w-6 text-xs text-slate-400">{index + 1}</span>
                            <div className="flex-1 grid grid-cols-1 gap-2 sm:grid-cols-5">
                                {/* Symbol Search */}
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                                    <input
                                        type="text"
                                        value={row.symbol}
                                        onChange={e => handleInputChange(row.id, 'symbol', e.target.value)}
                                        onFocus={() => {
                                            setFocusedRowId(row.id)
                                            setSelectedRowId(row.id)
                                        }}
                                        onBlur={() => setTimeout(() => setFocusedRowId(null), 200)}
                                        placeholder="股票代码"
                                        className="w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:placeholder:text-slate-500"
                                    />
                                    {focusedRowId === row.id && selectedRowId === row.id && showDropdown && searchResults.length > 0 && (
                                        <div
                                            ref={dropdownRef}
                                            className="absolute z-50 mt-1 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"
                                        >
                                            {searchLoading && (
                                                <div className="flex items-center justify-center py-2 text-slate-500">
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                </div>
                                            )}
                                            {!searchLoading && searchResults.map((stock, i) => (
                                                <button
                                                    key={`${row.id}-${i}`}
                                                    type="button"
                                                    onClick={() => handleStockSelect(row.id, stock)}
                                                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                                                >
                                                    <span className="font-medium text-slate-900 dark:text-slate-100">{stock.symbol}</span>
                                                    <span className="text-slate-500 dark:text-slate-400">{stock.name}</span>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                {/* Name */}
                                <input
                                    type="text"
                                    value={row.name}
                                    onChange={e => handleInputChange(row.id, 'name', e.target.value)}
                                    placeholder="股票名称"
                                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:placeholder:text-slate-500"
                                />

                                {/* Position */}
                                <input
                                    type="number"
                                    value={row.current_position}
                                    onChange={e => handleInputChange(row.id, 'current_position', e.target.value)}
                                    placeholder="持仓数"
                                    min="0"
                                    step="100"
                                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:placeholder:text-slate-500"
                                />

                                {/* Cost */}
                                <input
                                    type="number"
                                    value={row.average_cost}
                                    onChange={e => handleInputChange(row.id, 'average_cost', e.target.value)}
                                    placeholder="成本价"
                                    min="0"
                                    step="0.01"
                                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:placeholder:text-slate-500"
                                />

                                {/* Market Value */}
                                <div className="flex items-center gap-2">
                                    <input
                                        type="number"
                                        value={row.market_value}
                                        onChange={e => handleInputChange(row.id, 'market_value', e.target.value)}
                                        placeholder="市值（可选）"
                                        min="0"
                                        step="0.01"
                                        className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:placeholder:text-slate-500"
                                    />
                                    {positions.length > 1 && (
                                        <button
                                            type="button"
                                            onClick={() => handleRemoveRow(row.id)}
                                            className="rounded-full p-2 text-slate-400 opacity-0 transition-opacity hover:text-rose-500 group-hover:opacity-100"
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Add Row Button */}
            <button
                type="button"
                onClick={handleAddRow}
                className="inline-flex items-center gap-2 rounded-xl border border-dashed border-slate-300 px-4 py-2.5 text-sm text-slate-500 transition-colors hover:border-slate-400 hover:text-slate-700 dark:border-slate-600 dark:hover:border-slate-500"
            >
                <Plus className="h-4 w-4" />
                添加一行
            </button>

            {/* Submit Button */}
            <div className="flex justify-end gap-2 pt-2">
                <button
                    type="button"
                    onClick={onCancel}
                    className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                    取消
                </button>
                <button
                    type="button"
                    onClick={handleSubmit}
                    className="rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-600"
                >
                    保存持仓
                </button>
            </div>
        </div>
    )
}

import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { Recommendation } from '@/types'

interface DiscoveryState {
    recommendations: Recommendation[]
    loading: boolean
    loaded: boolean
    error: string | null
    progress: number
    logs: string[]
    analysisTime: string | null

    setRecommendations: (recommendations: Recommendation[]) => void
    setLoading: (loading: boolean) => void
    setLoaded: (loaded: boolean) => void
    setError: (error: string | null) => void
    setProgress: (progress: number) => void
    addLog: (message: string) => void
    clearLogs: () => void
    setAnalysisTime: (time: string | null) => void
    reset: () => void
}

const initialState = {
    recommendations: [] as Recommendation[],
    loading: false,
    loaded: false,
    error: null as string | null,
    progress: 0,
    logs: [] as string[],
    analysisTime: null as string | null,
}

export const useDiscoveryStore = create<DiscoveryState>()(
    persist(
        (set) => ({
            ...initialState,

            setRecommendations: (recommendations) => set({ recommendations }),
            setLoading: (loading) => set({ loading }),
            setLoaded: (loaded) => set({ loaded }),
            setError: (error) => set({ error }),
            setProgress: (progress) => set({ progress }),
            addLog: (message) => set((state) => ({
                logs: [...state.logs, `[${new Date().toLocaleTimeString()}] ${message}`],
            })),
            clearLogs: () => set({ logs: [] }),
            setAnalysisTime: (analysisTime) => set({ analysisTime }),
            reset: () => set(initialState),
        }),
        {
            name: 'tradingagents-discovery',
            storage: createJSONStorage(() => localStorage),
            partialize: (state) => ({
                recommendations: state.recommendations,
                loaded: state.loaded,
                analysisTime: state.analysisTime,
            }),
        },
    ),
)

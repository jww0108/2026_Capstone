"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import type { AnalysisRequest, AnalysisResult } from "@/types/analysis"

const STORAGE_KEY = "git2value:analysis"

export type AnalysisSession = {
  request: AnalysisRequest
  result: AnalysisResult
  analyzedAt: string
}

type AnalysisContextValue = {
  session: AnalysisSession | null
  setSession: (session: AnalysisSession) => void
  clearSession: () => void
  isHydrated: boolean
}

const AnalysisContext = createContext<AnalysisContextValue | null>(null)

function readStoredSession(): AnalysisSession | null {
  if (typeof window === "undefined") return null
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as AnalysisSession
  } catch {
    return null
  }
}

function writeStoredSession(session: AnalysisSession | null) {
  if (typeof window === "undefined") return
  if (session) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  } else {
    sessionStorage.removeItem(STORAGE_KEY)
  }
}

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<AnalysisSession | null>(null)
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    setSessionState(readStoredSession())
    setIsHydrated(true)
  }, [])

  const setSession = useCallback((next: AnalysisSession) => {
    setSessionState(next)
    writeStoredSession(next)
  }, [])

  const clearSession = useCallback(() => {
    setSessionState(null)
    writeStoredSession(null)
  }, [])

  const value = useMemo(
    () => ({ session, setSession, clearSession, isHydrated }),
    [session, setSession, clearSession, isHydrated]
  )

  return <AnalysisContext.Provider value={value}>{children}</AnalysisContext.Provider>
}

export function useAnalysisContext() {
  const ctx = useContext(AnalysisContext)
  if (!ctx) {
    throw new Error("useAnalysisContext must be used within AnalysisProvider")
  }
  return ctx
}

export function useAnalysis(options?: { redirectIfMissing?: boolean }) {
  const { session, isHydrated } = useAnalysisContext()
  const redirectIfMissing = options?.redirectIfMissing ?? false

  useEffect(() => {
    if (!redirectIfMissing || !isHydrated || session) return
    window.location.href = "/"
  }, [redirectIfMissing, isHydrated, session])

  return {
    session,
    result: session?.result ?? null,
    request: session?.request ?? null,
    isHydrated,
    isReady: isHydrated && session != null,
  }
}

export function usePendingAnalysisRequest() {
  const { session, setSession, isHydrated } = useAnalysisContext()
  return { session, setSession, isHydrated }
}

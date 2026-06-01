import type { AnalysisRequest } from "@/types/analysis"

export const PENDING_ANALYSIS_KEY = "git2value:pending-request"

export function savePendingAnalysisRequest(request: AnalysisRequest) {
  if (typeof window === "undefined") return
  sessionStorage.setItem(PENDING_ANALYSIS_KEY, JSON.stringify(request))
}

export function readPendingAnalysisRequest(): AnalysisRequest | null {
  if (typeof window === "undefined") return null
  try {
    const raw = sessionStorage.getItem(PENDING_ANALYSIS_KEY)
    if (!raw) return null
    return JSON.parse(raw) as AnalysisRequest
  } catch {
    return null
  }
}

export function clearPendingAnalysisRequest() {
  if (typeof window === "undefined") return
  sessionStorage.removeItem(PENDING_ANALYSIS_KEY)
}

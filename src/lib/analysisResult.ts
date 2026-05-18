import { report } from "@/data/mockReport"
import type { AnalysisResult } from "@/types/analysis"

export type StartAnalysisPayload = {
  githubId: string
  repositories: string[]
}

export type AnalysisStatus = {
  analysisId: string
  currentStep: number
  progress: number
  status: "READY" | "RUNNING" | "COMPLETED" | "FAILED"
}

// 현재는 시연용 mock 데이터를 반환합니다.
// 백엔드 연결 시에는 이 파일의 함수 내부만 fetch 호출로 교체하면 됩니다.
export function getAnalysisResult(): AnalysisResult {
  return report
}

export async function startAnalysis(_payload: StartAnalysisPayload): Promise<{ analysisId: string }> {
  return { analysisId: "demo-analysis" }
}

export async function getAnalysisStatus(analysisId = "demo-analysis"): Promise<AnalysisStatus> {
  return {
    analysisId,
    currentStep: 6,
    progress: 100,
    status: "COMPLETED",
  }
}

export async function fetchAnalysisResult(_analysisId = "demo-analysis"): Promise<AnalysisResult> {
  // 예시:
  // const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/analysis/${analysisId}`)
  // return mapApiResultToAnalysisResult(await res.json())
  return getAnalysisResult()
}

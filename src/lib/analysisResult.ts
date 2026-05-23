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
  message?: string
}

const DEMO_ANALYSIS_ID = "demo-analysis"

// API 연동 전에는 이 파일이 mock 데이터 진입점입니다.
// 백엔드가 붙으면 각 함수 내부의 mock 반환부를 fetch 호출로 교체하면 됩니다.
export function getAnalysisResult(): AnalysisResult {
  return report
}

export async function startAnalysis(_payload: StartAnalysisPayload): Promise<{ analysisId: string }> {
  // 추후 교체 예시:
  // const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/analysis`, {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify(payload),
  // })
  // return res.json()
  return { analysisId: DEMO_ANALYSIS_ID }
}

export async function getAnalysisStatus(analysisId = DEMO_ANALYSIS_ID): Promise<AnalysisStatus> {
  // 추후 교체 예시:
  // const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/analysis/${analysisId}/status`)
  // return res.json()
  return {
    analysisId,
    currentStep: 1,
    progress: 10,
    status: "RUNNING",
    message: "시연용 시간 기반 진행 중입니다.",
  }
}

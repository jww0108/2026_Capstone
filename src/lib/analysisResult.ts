import { report } from "@/data/mockReport"
import { mapAnalyzeResponse } from "@/lib/mapAnalyzeResponse"
import type { AnalyzeRequest, AnalyzeResponse } from "@/types/api"
import type { AnalysisRequest, AnalysisResult } from "@/types/analysis"

export class AnalyzePortfolioError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number
  ) {
    super(message)
    this.name = "AnalyzePortfolioError"
  }
}

function getApiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL?.trim()
  if (!base) {
    throw new AnalyzePortfolioError("API 서버 주소가 설정되지 않았습니다. (.env.local 확인)")
  }
  return base.replace(/\/+$/, "")
}

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string | Array<{ msg?: string }>; error?: string }
    if (typeof body.detail === "string") return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg
    if (body.error) return body.error
  } catch {
    // ignore JSON parse failure
  }
  return `분석 요청에 실패했습니다. (HTTP ${res.status})`
}

export async function analyzePortfolio(payload: AnalyzeRequest): Promise<AnalysisResult> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
    return report
  }

  const res = await fetch(`${getApiBaseUrl()}/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const message = await parseErrorMessage(res)
    throw new AnalyzePortfolioError(message, res.status)
  }

  const body = (await res.json()) as AnalyzeResponse

  if (body.status === "error" || body.error) {
    throw new AnalyzePortfolioError(body.error ?? "분석 중 오류가 발생했습니다.", 500)
  }

  return mapAnalyzeResponse(body, { githubId: payload.github_username })
}

export type { AnalyzeRequest, AnalysisRequest, AnalysisResult }

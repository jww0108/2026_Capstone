"use client"

import Image from "next/image"
import { PageShell } from "@/components/PageShell"
import { Breadcrumb, InfoTooltip } from "@/components/Common"
import { RepoAnalysisTabs } from "@/components/portfolio/RepoAnalysisTabs"
import { useAnalysis } from "@/context/AnalysisContext"

export default function PortfolioPage() {
  const { result, isHydrated } = useAnalysis({ redirectIfMissing: true })

  if (!isHydrated || !result) {
    return null
  }

  const repos = result.repos.slice(0, 3)

  return (
    <PageShell active="포트폴리오 진단">
      <Breadcrumb current="포트폴리오 진단" />

      <section className="mb-3">
        <h1 className="text-[40px] font-black tracking-[-0.045em] text-slate-950">
          포트폴리오 진단 <InfoTooltip text="레포지토리별 README, 구조, 커밋, 테스트, CI/CD, 배포 상태를 종합 진단합니다." />
        </h1>
        <div className="mt-2 flex items-center justify-between gap-8">
          <p className="text-lg font-bold text-slate-700">
            각 레포지토리에 대해 README, 구조, 커밋, 테스트, CI/CD, 배포 등을 종합적으로 진단합니다.
          </p>
          <div className="shrink-0 rounded-full border border-slate-200 bg-white px-7 py-2.5 shadow-md shadow-slate-200/60">
            <Image
              src="/images/status.png"
              alt="상태 범례: 양호, 보통, 개선 필요, 없음, 필수 미흡"
              width={514}
              height={48}
              className="h-12 w-auto object-contain"
              priority
            />
          </div>
        </div>
      </section>

      <RepoAnalysisTabs repos={repos} fallbackScore={result.score} />
    </PageShell>
  )
}

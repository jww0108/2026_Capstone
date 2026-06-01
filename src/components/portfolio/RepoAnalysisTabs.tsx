"use client"

import { useMemo, useState } from "react"
import { FolderGit2 } from "lucide-react"
import { RepoAnalysisPanel } from "@/components/portfolio/RepoAnalysisPanel"
import { cn } from "@/lib/utils"
import type { RepoAnalysis, RepoScore } from "@/types/analysis"

export function RepoAnalysisTabs({
  repos,
  fallbackScore,
}: {
  repos: RepoAnalysis[]
  fallbackScore: RepoScore
}) {
  const visibleRepos = useMemo(() => repos.slice(0, 3), [repos])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const selectedRepo = visibleRepos[selectedIndex] ?? visibleRepos[0]
  const total = visibleRepos.length

  if (!selectedRepo) return null

  return (
    <>
      {total > 1 && (
        <div data-no-print className="mb-4 grid grid-cols-3 gap-3">
          {visibleRepos.map((repo, index) => {
            const selected = index === selectedIndex
            const score = repo.score?.total ?? fallbackScore.total

            return (
              <button
                key={`${repo.name}-${index}`}
                type="button"
                onClick={() => setSelectedIndex(index)}
                className={cn(
                  "group min-w-0 rounded-2xl border bg-white px-4 py-3 text-left shadow-sm transition",
                  selected
                    ? "border-blue-300 bg-blue-50/70 shadow-blue-100/80"
                    : "border-slate-200 hover:border-blue-200 hover:bg-slate-50"
                )}
                aria-pressed={selected}
              >
                <div className="flex items-center justify-between gap-3">
                  <span
                    className={cn(
                      "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-black ring-1",
                      selected ? "bg-blue-600 text-white ring-blue-600" : "bg-slate-100 text-slate-600 ring-slate-200"
                    )}
                  >
                    <FolderGit2 className="h-4 w-4" />
                    포트폴리오 {index + 1}
                  </span>
                  <b className={cn("text-sm font-black", selected ? "text-blue-700" : "text-slate-500")}>
                    {score.toFixed(1)}점
                  </b>
                </div>
                <div className="mt-2 truncate text-[16px] font-black tracking-[-0.02em] text-slate-950">
                  {repo.name}
                </div>
                <div className="mt-1 truncate text-[13px] font-extrabold text-slate-500">
                  {repo.type} · {repo.period}
                </div>
              </button>
            )
          })}
        </div>
      )}

      <RepoAnalysisPanel repo={selectedRepo} index={selectedIndex} total={total} fallbackScore={fallbackScore} />
    </>
  )
}

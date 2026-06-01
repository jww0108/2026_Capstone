"use client"

import { useState } from "react"
import { Briefcase } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Chip } from "@/components/Common"
import { cn } from "@/lib/utils"
import type { DomainJobPickUI, MultiDomainPicksUI } from "@/types/analysis"

export function DomainJobPicksPanel({ data }: { data: MultiDomainPicksUI }) {
  const [selectedDomain, setSelectedDomain] = useState(data.domains[0] ?? "")
  const picks = data.picksByDomain[selectedDomain] ?? []

  if (data.domains.length === 0) return null

  return (
    <Card className="mt-5 p-5">
      <h2 className="flex items-center gap-2 text-[26px] font-black tracking-[-0.03em] text-slate-950">
        <Briefcase className="h-7 w-7 text-blue-600" />
        도메인별 유사 공고
      </h2>
      <p className="mt-2 text-[15px] font-bold text-slate-600">
        혼합 프로젝트로 감지된 도메인별 유사 공고입니다. 공고 본문을 참고해 지원 전략을 세울 수 있습니다.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {data.domains.map((domain) => {
          const selected = domain === selectedDomain
          return (
            <button
              key={domain}
              type="button"
              onClick={() => setSelectedDomain(domain)}
              className={cn(
                "rounded-full px-4 py-2 text-sm font-black ring-1 transition",
                selected
                  ? "bg-blue-600 text-white ring-blue-600"
                  : "bg-white text-slate-700 ring-slate-200 hover:bg-slate-50"
              )}
            >
              {domain}
            </button>
          )
        })}
      </div>

      <div className="mt-4 space-y-4">
        {picks.map((pick) => (
          <DomainPickCard key={`${pick.company}-${pick.position}`} pick={pick} />
        ))}
      </div>
    </Card>
  )
}

function DomainPickCard({ pick }: { pick: DomainJobPickUI }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-[18px] font-black tracking-[-0.02em] text-slate-950">{pick.position}</h3>
          <p className="mt-1 text-[15px] font-extrabold text-slate-600">{pick.company}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip tone="blue">유사도 {pick.similarity}</Chip>
          <Chip tone="gray">{pick.category}</Chip>
          <Chip tone={pick.expLabel.includes("신입") ? "green" : "gray"}>{pick.expLabel}</Chip>
        </div>
      </div>
      {pick.postingText && (
        <details open className="mt-3 rounded-xl border border-slate-200 bg-white">
          <summary className="cursor-pointer px-4 py-2.5 text-[14px] font-black text-blue-700">
            공고 본문
          </summary>
          <pre className="whitespace-pre-wrap border-t border-slate-100 px-4 py-3 text-[13px] font-bold leading-6 text-slate-700">
            {pick.postingText}
          </pre>
        </details>
      )}
    </div>
  )
}

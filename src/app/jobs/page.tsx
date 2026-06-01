"use client"

import Image from "next/image"
import Link from "next/link"
import { Filter, ShieldCheck, Target } from "lucide-react"
import { PageShell } from "@/components/PageShell"
import { Card } from "@/components/ui/card"
import { Bar, Breadcrumb, Chip, FooterActions, InfoTooltip } from "@/components/Common"
import { Button } from "@/components/ui/button"
import { DomainJobPicksPanel } from "@/components/jobs/DomainJobPicksPanel"
import { useAnalysis } from "@/context/AnalysisContext"
import { getDomainMatchStatIcon, getTechMatchNoteIcon } from "@/lib/domainIcons"
import { cn, scoreToPercent } from "@/lib/utils"

export default function JobsPage() {
  const { result: report, isHydrated } = useAnalysis({ redirectIfMissing: true })

  if (!isHydrated || !report) {
    return null
  }

  const quickStats = [
    { label: "분석 공고", value: report.jobSummary.totalPostings, icon: "search" },
    { label: "매칭 후보", value: report.jobSummary.recommendedPostings, icon: "target" },
    { label: "평균 점수", value: report.jobSummary.averageScore, icon: "score" },
    { label: "도메인 일치", value: report.jobSummary.domainMatchRatio, icon: "domain" },
  ]

  return (
    <PageShell active="직무 매칭">
      <Breadcrumb current="직무 매칭" />

      <div className="mb-4">
        <h1 className="flex items-center gap-2 text-[40px] font-black tracking-[-0.045em] text-slate-950">
          직무 매칭
          <InfoTooltip text="포트폴리오 신호와 채용공고 유사도를 비교해 유사 공고를 연결합니다." />
        </h1>
        <div className="mt-3 grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_500px]">
          <p className="pt-1 text-lg font-bold leading-7 text-slate-700">
            FAISS 유사도 검색과 도메인 분석으로 포트폴리오와 가까운 공고를 보여줍니다.
          </p>
          <Card className="border-amber-200 bg-amber-50/70 px-5 py-3 shadow-sm">
            <div className="flex items-center gap-3">
              <Image src="/images/light.png" alt="추천 활용 팁" width={34} height={32} className="h-8 w-8 object-contain" />
              <p className="text-[15px] font-black leading-6 text-slate-800">
                README, 기술 스택, 프로젝트 설명을 보강하면 직무 매칭 품질을 높일 수 있어요.
              </p>
            </div>
          </Card>
        </div>
      </div>

      {(report.warnings?.domainMismatch || report.warnings?.domainCheck) && (
        <div className="mb-4 space-y-3">
          {report.warnings.domainMismatch && (
            <Card className="border-orange-200 bg-orange-50/70 px-5 py-3 shadow-sm">
              <p className="text-[15px] font-black leading-6 text-orange-900">{report.warnings.domainMismatch}</p>
            </Card>
          )}
          {report.warnings.domainCheck && (
            <Card className="border-amber-200 bg-amber-50/70 px-5 py-3 shadow-sm">
              <p className="text-[15px] font-black leading-6 text-amber-900">{report.warnings.domainCheck}</p>
            </Card>
          )}
        </div>
      )}

      {(report.isMultiDomain || (report.detectedDomains && report.detectedDomains.length > 1)) && (
        <Card className="mb-4 px-5 py-3 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            {report.isMultiDomain && <Chip tone="purple">혼합 프로젝트</Chip>}
            {report.detectedDomains?.map((domain) => (
              <Chip key={domain} tone="blue">
                {domain}
              </Chip>
            ))}
          </div>
        </Card>
      )}

      {report.jobMatchingMeta?.rerankNote && (
        <Card className="mb-4 border-purple-200 bg-purple-50/70 px-5 py-3 shadow-sm">
          <p className="text-[15px] font-black leading-6 text-purple-900">{report.jobMatchingMeta.rerankNote}</p>
        </Card>
      )}

      <Card className="p-5">
        <div>
          <h2 className="flex items-center gap-3 text-[26px] font-black tracking-[-0.03em]">
            매칭 공고 TOP 5
            <Chip>신입 기준 필터 적용</Chip>
          </h2>
          <p className="mt-2 text-[15px] font-bold text-slate-600">
            유사도 점수, 경력 조건, 도메인 일치 신호를 함께 고려해 정렬했습니다.
          </p>
        </div>

        <div className="mt-4 grid grid-cols-4 gap-4">
          {quickStats.map((item) => (
            <StatCard key={item.label} label={item.label} value={item.value} icon={item.icon} />
          ))}
        </div>

        <div className="mt-5 overflow-hidden rounded-2xl border border-slate-200">
          <div className="grid grid-cols-[68px_minmax(0,1.45fr)_210px_170px_170px] items-center bg-slate-50 px-4 py-3 text-[14px] font-black text-slate-500">
            <span>순위</span>
            <span>직무 / 회사</span>
            <span>
              유효 점수 <InfoTooltip text="채용공고와 포트폴리오 신호의 유사도를 나타낸 값입니다. 높을수록 매칭도가 좋습니다." />
            </span>
            <span>경력 조건</span>
            <span>도메인 일치</span>
          </div>

          <div className="divide-y divide-slate-200">
            {report.jobs.slice(0, 5).map((j) => (
              <div key={j.rank} className="px-4 py-3.5">
                <div className="grid grid-cols-[68px_minmax(0,1.45fr)_210px_170px_170px] items-center gap-3">
                  <div className="grid h-10 w-10 place-items-center rounded-xl bg-blue-50 text-[22px] font-black text-blue-600">
                    {j.rank}
                  </div>
                  <div className="flex min-w-0 items-center gap-3">
                    <Avatar name={j.company} rank={j.rank} />
                    <div className="min-w-0">
                      <div className="truncate text-[18px] font-black tracking-[-0.02em] text-slate-950">{j.title}</div>
                      <p className="mt-0.5 text-[14px] font-extrabold text-slate-600">{j.company}</p>
                      {j.category && j.category !== "—" && (
                        <p className="mt-0.5 text-[13px] font-bold text-slate-500">카테고리: {j.category}</p>
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-[15px] font-black text-slate-950">{j.score}</div>
                    {j.similarity && (
                      <p className="mt-0.5 text-[12px] font-bold text-slate-500">원점수 {j.similarity}</p>
                    )}
                    <div className="mt-1.5 w-[150px]">
                      <Bar value={scoreToPercent(j.score)} />
                    </div>
                  </div>
                  <div>
                    <Chip tone={j.exp === "신입" ? "green" : j.exp === "경력 무관" ? "green" : "gray"}>{j.exp}</Chip>
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Chip tone={j.domain === "강함" ? "green" : j.domain === "보통" ? "blue" : j.domain === "낮음" ? "gray" : "orange"}>{j.domain}</Chip>
                      {j.domainBoosted && <Chip tone="purple">가산</Chip>}
                    </div>
                  </div>
                </div>
                {j.postingText && (
                  <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50/70">
                    <summary className="cursor-pointer px-4 py-2.5 text-[14px] font-black text-blue-700">
                      공고 본문 보기
                    </summary>
                    <pre className="whitespace-pre-wrap border-t border-slate-200 px-4 py-3 text-[13px] font-bold leading-6 text-slate-700">
                      {j.postingText}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>
      </Card>

      {report.multiDomainPicks && <DomainJobPicksPanel data={report.multiDomainPicks} />}

      <div className="mt-5 grid grid-cols-2 items-stretch gap-5">
        <Card className="h-full p-5">
          <h2 className="flex items-center gap-2 text-[22px] font-black tracking-[-0.03em]">
            <ShieldCheck className="h-6 w-6 text-blue-600" />매칭 근거
          </h2>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {report.techMatchNotes.map((item) => {
              const Icon = getTechMatchNoteIcon(item)
              return (
                <ReasonItem
                  key={`${item.type}-${item.label}`}
                  icon={<Icon className="h-[18px] w-[18px]" />}
                  label={item.label}
                  note={item.note}
                  type={item.type}
                />
              )
            })}
          </div>
          {report.companyTypes && report.companyTypes.length > 0 && (
            <div className="mt-4">
              <p className="text-[14px] font-black text-slate-500">공고 유형</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-[14px] font-bold text-slate-700">
                {report.companyTypes.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>

        <Card className="h-full p-5">
          <h2 className="flex items-center gap-2 text-[22px] font-black tracking-[-0.03em]">
            <Filter className="h-6 w-6 text-blue-600" />매칭 기준 요약
          </h2>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <RuleItem title="경력 조건" desc="신입·경력무관·경력 미기재 우선 반영" />
            <RuleItem title="텍스트 유사도" desc="FAISS 기반 공고-포트폴리오 유사도 비교" />
            <RuleItem title="도메인 보정" desc="프로젝트 도메인과 직무 방향 일치 여부 반영" />
            <RuleItem title="표시 결과 제한" desc="최대 5개 공고만 우선순위 중심으로 표시" />
            <RuleItem title="기술 스택 반영" desc="보유 기술과 공고 요구 기술의 겹침 정도 반영" />
            <RuleItem title="중복 공고 정리" desc="유사 공고는 대표 직무 중심으로 묶어 해석" />
            {report.jumpitCategory && (
              <RuleItem title="점핏 카테고리" desc={report.jumpitCategory} />
            )}
            {report.isMultiDomain && (
              <RuleItem title="다중 도메인" desc="혼합 프로젝트는 도메인별 유사 공고를 함께 제공" />
            )}
          </div>
          {report.techLearningSuggestions && report.techLearningSuggestions.length > 0 && (
            <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/60 px-4 py-3">
              <p className="text-[14px] font-black text-blue-800">학습 제안</p>
              <ul className="mt-2 list-disc pl-5 text-[14px] font-bold text-slate-700">
                {report.techLearningSuggestions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      </div>

      <FooterActions
        left={
          <Link href="/portfolio">
            <Button variant="secondary" className="w-60 font-black">← 포트폴리오 진단 보기</Button>
          </Link>
        }
        center={
          <Link href="/result">
            <Button variant="secondary" className="w-60 font-black">결과 요약으로 돌아가기</Button>
          </Link>
        }
        right={
          <Link href="/salary">
            <Button className="w-72 font-black">시장 연봉 밴드 보기 →</Button>
          </Link>
        }
      />
    </PageShell>
  )
}

function StatCard({ label, value, icon }: { label: string; value: string; icon: string }) {
  const Icon =
    icon === "target" ? Target : icon === "score" ? ShieldCheck : icon === "domain" ? getDomainMatchStatIcon() : Filter

  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3.5">
      <div className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-blue-50 text-blue-600 ring-1 ring-blue-100">
        <Icon className="h-6 w-6" />
      </div>
      <div>
        <div className="text-[13px] font-black text-slate-500">{label}</div>
        <div className="mt-0.5 text-[22px] font-black tracking-[-0.03em] text-slate-950">{value}</div>
      </div>
    </div>
  )
}

function ReasonItem({
  icon,
  label,
  note,
  type,
  className,
}: {
  icon: React.ReactNode
  label: string
  note: string
  type: string
  className?: string
}) {
  return (
    <div className={cn("flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3", className)}>
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-blue-100">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <b className="block truncate text-[15px] font-black text-slate-900">{label}</b>
        <p className="mt-1 text-[13px] font-extrabold leading-5 text-slate-600">{note}</p>
      </div>
      <span className="shrink-0 rounded-full bg-blue-50 px-3 py-1 text-[11px] font-black text-blue-700 ring-1 ring-blue-100">
        {type}
      </span>
    </div>
  )
}

function RuleItem({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3.5">
      <b className="block text-[15px] font-black text-slate-950">{title}</b>
      <p className="mt-1.5 text-[13px] font-extrabold leading-5 text-slate-600">{desc}</p>
    </div>
  )
}

function Avatar({ name, rank }: { name: string; rank: number }) {
  const label = /[A-Za-z]+/.test(name)
    ? name.match(/[A-Za-z]+/)?.[0].slice(0, 2).toUpperCase()
    : name.slice(0, 1)
  const colors = [
    "from-violet-600 to-blue-600",
    "from-slate-950 to-emerald-500",
    "from-rose-500 to-red-600",
    "from-slate-950 to-black",
    "from-emerald-400 to-teal-600",
  ]

  return (
    <div className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-gradient-to-br ${colors[rank - 1]} text-lg font-black text-white shadow-sm`}>
      {label}
    </div>
  )
}

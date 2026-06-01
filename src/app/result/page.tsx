"use client"

import Image from "next/image"
import Link from "next/link"
import { CalendarDays, Github, Hexagon, Users } from "lucide-react"
import { PageShell } from "@/components/PageShell"
import { Card } from "@/components/ui/card"
import { Bar, Chip, InfoTooltip } from "@/components/Common"
import { ScoreRing } from "@/components/ScoreRing"
import { useAnalysis } from "@/context/AnalysisContext"
import { getDomainIcon } from "@/lib/domainIcons"

const moduleCards = [
  {
    title: "포트폴리오 진단",
    desc: "레포 구조, 구성 신호, 개선 포인트를 정리합니다.",
    href: "/portfolio",
    image: "/images/module-portfolio.png",
    button: "/images/button1.png",
    tone: "green",
  },
  {
    title: "직무 매칭",
    desc: "FAISS 유사도와 도메인 분석으로 유사 공고를 연결합니다.",
    href: "/jobs",
    image: "/images/module-jobs.png",
    button: "/images/button2.png",
    tone: "purple",
  },
  {
    title: "시장 연봉 밴드",
    desc: "신입~3년차 연봉 데이터를 기반으로 분석합니다.",
    href: "/salary",
    image: "/images/module-salary.png",
    button: "/images/button3.png",
    tone: "orange",
  },
]

export default function SummaryPage() {
  const { result, isHydrated } = useAnalysis({ redirectIfMissing: true })

  if (!isHydrated || !result) {
    return null
  }

  const levelTitle = `${result.applicant.domain} 포트폴리오 ${result.level.grade} 구성 수준`
  const DomainIcon = getDomainIcon(result.applicant.domain)
  const showLevelDescription =
    result.level.description &&
    result.level.description !== result.summary.positioning

  return (
    <PageShell active="결과 요약">
      <h1 className="text-[42px] font-black tracking-[-0.05em] text-slate-950">분석이 완료되었습니다!</h1>
      <p className="mt-2 text-[19px] font-extrabold text-slate-600">입력한 GitHub 포트폴리오의 해석 결과입니다.</p>

      <Card className="glass-card mt-5 p-5 pt-4">
        <h2 className="text-[28px] font-black tracking-[-0.04em] text-slate-950">
          GitHub 포트폴리오 종합 결과
          {result.scoreMeta && (
            <InfoTooltip
              className="ml-2"
              text={`${result.scoreMeta.method} (${result.scoreMeta.breakdownNote})`}
            />
          )}
        </h2>
        <div className="mt-2 grid grid-cols-[250px_1fr_1fr] items-center gap-7">
          <ScoreRing value={result.score.total} />

          <div>
            <div className="flex items-center gap-5">
              <div className="grid h-[76px] w-[76px] shrink-0 place-items-center rounded-full bg-blue-50 text-blue-600 ring-8 ring-blue-50/70">
                <DomainIcon className="h-10 w-10" />
              </div>
              <div>
                <h3 className="text-[30px] font-black tracking-[-0.04em] text-slate-950">{levelTitle}</h3>
                <p className="mt-1 text-[17px] font-extrabold leading-7 text-slate-700">
                  {result.summary.positioning || result.level.description}
                </p>
                {showLevelDescription && (
                  <p className="mt-2 text-[15px] font-bold leading-6 text-slate-600">
                    {result.level.description}
                  </p>
                )}
              </div>
            </div>

            {result.detectedDomains && result.detectedDomains.length > 1 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {result.isMultiDomain && <Chip tone="purple">혼합 프로젝트</Chip>}
                {result.detectedDomains.map((domain) => (
                  <Chip key={domain} tone="blue">
                    {domain}
                  </Chip>
                ))}
              </div>
            )}

            <div className="mt-5 grid grid-cols-3 overflow-hidden rounded-xl border border-slate-200 bg-white text-sm">
              <Mini icon={<Github />} label="GitHub ID" value={result.applicant.githubId} />
              <Mini icon={<Users />} label="지원자 경력" value={result.applicant.career} />
              <Mini icon={<CalendarDays />} label="분석 레포지토리" value={`${result.applicant.repoCount}개`} />
              <Mini icon={<Hexagon />} label="주요 기술 스택" value={result.applicant.techStack.join(", ") || "—"} />
              <Mini icon={<DomainIcon />} label="주요 도메인" value={result.applicant.domain} />
              <Mini icon={<Users />} label="레포 유형" value={result.applicant.repoType} />
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-[23px] font-black tracking-[-0.035em] text-slate-950">핵심 포트폴리오 지표</h3>
            <Score label="개발 활동량" val={`${result.score.activity} / 60`} pct={(result.score.activity / 60) * 100} image="/images/develop-activity.png" />
            <Score label="프로젝트 운영도" val={`${result.score.management.toFixed(1)} / 30`} pct={(result.score.management / 30) * 100} color="bg-purple-500" image="/images/project-management.png" />
            <Score label="작업 일관성" val={`${result.score.consistency} / 10`} pct={(result.score.consistency / 10) * 100} color="bg-emerald-500" image="/images/work-consistency.png" />
            {result.scoreDetail && (
              <p className="mt-3 text-[13px] font-bold leading-5 text-slate-500">
                상세 지표 합계 {result.scoreDetail.totalScore.toFixed(1)} / {result.scoreDetail.maxScore}
                {result.scoreMeta?.breakdownNote ? ` (${result.scoreMeta.breakdownNote})` : ""}
              </p>
            )}
          </div>
        </div>
      </Card>

      {result.scoreDetail && (
        <Card className="mt-4 p-5">
          <h3 className="text-[22px] font-black tracking-[-0.035em] text-slate-950">점수 상세 해석</h3>
          {result.scoreDetail.scoreModel && (
            <p className="mt-1 text-[14px] font-bold text-slate-600">{result.scoreDetail.scoreModel}</p>
          )}
          {result.scoreDetail.potentialGainTotal != null && (
            <p className="mt-1 text-[14px] font-bold text-blue-700">
              개선 여지: +{result.scoreDetail.potentialGainTotal.toFixed(1)}점
            </p>
          )}
          <div className="mt-4 grid grid-cols-3 gap-4">
            {result.scoreDetail.axes.map((axis) => (
              <details key={axis.key} className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <summary className="cursor-pointer list-none">
                  <div className="flex items-center justify-between">
                    <b className="text-[15px] font-black text-slate-900">{axis.label}</b>
                    <span className="text-[14px] font-black text-slate-700">
                      {axis.score.toFixed(1)} / {axis.maxScore}
                    </span>
                  </div>
                </summary>
                <ul className="mt-2 space-y-1.5 text-[13px] font-bold text-slate-600">
                  {axis.items.map((item) => (
                    <li key={item.key}>
                      {item.label}: {item.score.toFixed(1)} / {item.maxScore}
                      {item.potentialGain != null ? ` · +${item.potentialGain.toFixed(1)} 가능` : ""}
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
        </Card>
      )}

      {(result.summary.strengths.length > 0 || result.summary.quickWins.length > 0) && (
        <div className="mt-4 grid grid-cols-2 gap-4">
          {result.summary.strengths.length > 0 && (
            <Card className="border-emerald-100 bg-emerald-50/50 p-5">
              <h3 className="text-lg font-black text-emerald-800">강점</h3>
              <ul className="mt-2 list-disc pl-5 text-[15px] font-bold text-slate-700">
                {result.summary.strengths.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Card>
          )}
          {result.summary.quickWins.length > 0 && (
            <Card className="border-blue-100 bg-blue-50/50 p-5">
              <h3 className="text-lg font-black text-blue-800">실행 가능한 개선</h3>
              <ul className="mt-2 list-disc pl-5 text-[15px] font-bold text-slate-700">
                {result.summary.quickWins.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}

      {result.summaryText && (
        <Card className="mt-4 p-5">
          <details className="group">
            <summary className="cursor-pointer text-lg font-black text-slate-950">
              상세 분석 리포트
            </summary>
            <pre className="mt-3 whitespace-pre-wrap text-[14px] font-bold leading-7 text-slate-700">
              {result.summaryText}
            </pre>
          </details>
        </Card>
      )}

      <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/70 px-5 py-4 text-[16px] font-extrabold leading-7 text-slate-700">
        <InfoTooltip text="세부 피드백은 포트폴리오 진단 화면에서 레포별로 확인할 수 있습니다." /> 요약 화면은 전체 수준과 상세 분석 진입점을 제공합니다. 레포별 개선 항목은 포트폴리오 진단에서 확인하세요.
      </div>

      <h2 className="mt-4 text-[24px] font-black tracking-[-0.035em] text-slate-950">상세 분석 보기</h2>
      <div className="mt-3 grid grid-cols-3 gap-5">
        {moduleCards.map((module) => (
          <DetailModuleCard key={module.title} {...module} />
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 bg-white px-5 py-3 text-[15px] font-extrabold text-slate-600">
        <InfoTooltip text="결과는 포트폴리오와 채용 데이터 기반의 참고 지표이며, 실제 채용 결과는 기업과 상황에 따라 달라질 수 있습니다." /> 분석 결과는 참고용입니다. 실제 채용 및 연봉은 회사, 지역, 협상 조건, 채용 시점 등에 따라 달라질 수 있습니다.
      </div>

      {result.meta && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-5 py-3 text-[14px] font-bold text-slate-600">
          <p className="font-black text-slate-700">분석 정보</p>
          <p className="mt-1">
            {result.meta.version} · 분석 {result.meta.analysisTimeSeconds}초 · 레포 {result.meta.reposAnalyzed}개
            {result.meta.llmAvailable ? " · LLM 사용 가능" : " · LLM 미사용"}
          </p>
        </div>
      )}
    </PageShell>
  )
}

function DetailModuleCard({
  title,
  desc,
  href,
  image,
  button,
  tone,
}: {
  title: string
  desc: string
  href: string
  image: string
  button: string
  tone: string
}) {
  const style = {
    green: {
      card: "border-emerald-200 bg-gradient-to-br from-white via-white to-emerald-50/45 hover:border-emerald-300",
    },
    purple: {
      card: "border-purple-200 bg-gradient-to-br from-white via-white to-purple-50/45 hover:border-purple-300",
    },
    orange: {
      card: "border-orange-200 bg-gradient-to-br from-white via-white to-orange-50/45 hover:border-orange-300",
    },
  }[tone as "green" | "purple" | "orange"]

  return (
    <Card className={`h-[148px] p-4 transition ${style.card}`}>
      <div className="grid h-full grid-cols-[76px_1fr] items-start gap-4">
        <Image src={image} alt="" width={70} height={70} className="mt-1 h-[70px] w-[70px] object-contain" />
        <div className="flex h-full min-w-0 flex-col justify-start pt-1">
          <h3 className="text-[24px] font-black tracking-[-0.04em] text-slate-950">{title}</h3>
          <p className="mt-1 max-w-[360px] text-[15px] font-extrabold leading-tight text-slate-600">{desc}</p>
          <Link href={href} className="mt-2 inline-flex w-fit">
            <Image src={button} alt="자세히 보기" width={145} height={40} className="h-10 w-[145px] object-contain transition hover:scale-[1.02]" />
          </Link>
        </div>
      </div>
    </Card>
  )
}

function Mini({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 border-r border-t p-3 first:border-t-0 [&:nth-child(-n+3)]:border-t-0 [&:nth-child(3n)]:border-r-0">
      <span className="grid h-8 w-8 place-items-center rounded-full bg-slate-50 text-slate-600 [&_svg]:h-4 [&_svg]:w-4">{icon}</span>
      <div>
        <p className="text-[13px] font-extrabold text-slate-500">{label}</p>
        <b className="text-[15px] font-black text-slate-950">{value}</b>
      </div>
    </div>
  )
}

function Score({ label, val, pct, color = "bg-blue-600", image }: { label: string; val: string; pct: number; color?: string; image: string }) {
  return (
    <div className="mt-5 grid grid-cols-[56px_1fr] gap-4">
      <Image src={image} alt="" width={52} height={52} className="h-[52px] w-[52px] object-contain" />
      <div>
        <div className="mb-2 flex justify-between">
          <b className="text-[17px] font-black text-slate-950">{label}</b>
          <b className="text-xl font-black text-slate-950">{val}</b>
        </div>
        <Bar value={pct} color={color} />
      </div>
    </div>
  )
}

import Image from "next/image"
import Link from "next/link"
import { CheckCircle2, FileText, Users } from "lucide-react"
import { PageShell } from "@/components/PageShell"
import { Breadcrumb, Card, Chip, FooterActions, InfoTooltip, StatRow } from "@/components/Common"
import { Button } from "@/components/ui/button"
import { ScoreRing } from "@/components/ScoreRing"
import { getAnalysisResult } from "@/lib/analysisResult"
import type { EvaluationItem, Tone } from "@/types/analysis"

export default function PortfolioPage() {
  const report = getAnalysisResult()
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
              alt="상태 범례: 양호, 보통, 개선 필요, 필수 미흡, 알 수 없음"
              width={514}
              height={48}
              className="h-12 w-auto object-contain"
              priority
            />
          </div>
        </div>
      </section>

      <Card className="p-5">
        <div className="grid grid-cols-[1.08fr_230px_1fr] items-center gap-6">
          <div className="flex items-center gap-5">
            <Image
              src="/images/fileImg.png"
              alt="repository"
              width={72}
              height={62}
              className="h-[66px] w-[78px] shrink-0 object-contain"
            />
            <div className="min-w-0">
              <Chip>포트폴리오 1 / 3</Chip>
              <h2 className="mt-3 truncate text-[32px] font-black leading-tight tracking-[-0.045em] text-slate-950">
                {report.repo.name}
              </h2>
              <p className="mt-2 text-lg font-extrabold text-slate-700">
                {report.repo.projectSummary}
              </p>
            </div>
          </div>

          <div className="border-x px-7 text-center">
            <ScoreRing value={report.score.total} size={150} />
          </div>

          <div className="grid grid-cols-2 gap-x-8 gap-y-5">
            <Meta label="레포 유형" value={report.repo.type} image="/images/person.png" />
            <Meta label="작성자 수" value={report.repo.people} image="/images/person.png" />
            <Meta label="포크 여부" value={report.repo.isFork ? "포크" : "포크 아님"} image="/images/fork.png" />
            <div>
              <p className="text-sm font-black text-slate-500">주요 기술 스택</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {report.repo.techStack.map((t) => (
                  <Chip key={t} tone="gray">
                    {t}
                  </Chip>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div className="mt-4 grid grid-cols-[1fr_540px] items-stretch gap-5">
        <div className="flex h-full flex-col gap-4">
          <Card className="flex-1 p-5">
            <h2 className="mb-3 flex items-center gap-2 text-xl font-black text-slate-950">
              <CheckCircle2 className="h-6 w-6 text-blue-600" />핵심 평가 항목
            </h2>
            {report.repo.evaluations.map((item) => (
              <Eval key={item.title} item={item} />
            ))}
          </Card>

          <Card className="flex-1 p-5">
            <h2 className="mb-3 flex items-center gap-2 text-xl font-black text-slate-950">
              <FileText className="h-6 w-6 text-blue-600" />팀 레포 필수 점검 항목
            </h2>
            {report.repo.teamChecks.map((item) => (
              <Eval key={item.title} item={item} />
            ))}
          </Card>
        </div>

        <div className="flex h-full flex-col gap-4">
          <Card className="p-5">
            <h2 className="mb-3 text-xl font-black text-slate-950">개발 활동 요약</h2>
            <StatRow label="전체 커밋 수" value={`${report.repo.commitsTotal}개`} />
            <StatRow label="지원자 커밋 수" value={report.repo.commitsUser} />
            <StatRow label="지원자 유효 LOC" value={report.repo.locUser} />
            <StatRow label="활성 기간 (전체)" value={report.repo.activeWeeks} />
            <StatRow label="활성 주당 평균 커밋" value={report.repo.weeklyCommits} />
          </Card>

          <Card className="border-blue-100 bg-blue-50/60 p-5">
            <h2 className="flex items-center gap-2 text-xl font-black text-blue-700">
              <Users className="h-6 w-6" />협업 신호
            </h2>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-[15px] font-bold leading-6 text-slate-700">
              {report.repo.collaborationSignals.map((signal) => (
                <li key={signal}>{signal}</li>
              ))}
            </ul>
          </Card>

          <Card className="flex-1 border-purple-100 bg-purple-50/50 p-5">
            <h2 className="text-xl font-black text-purple-700">종합 의견</h2>
            <p className="mt-3 text-[15px] font-bold leading-7 text-slate-700">
              {report.repo.overallOpinion}
            </p>
          </Card>
        </div>
      </div>

      <FooterActions
        center={
          <Link href="/result">
            <Button variant="secondary" className="w-72 font-black">결과 요약으로 돌아가기</Button>
          </Link>
        }
        right={
          <Link href="/jobs">
            <Button className="w-80 font-black">직무 매칭 보기 →</Button>
          </Link>
        }
      />
    </PageShell>
  )
}

function Meta({ label, value, image }: { label: string; value: string; image: string }) {
  return (
    <div className="flex items-start gap-3">
      <Image src={image} alt="" width={45} height={45} className="h-10 w-10 object-contain" />
      <div>
        <p className="text-sm font-black text-slate-500">{label}</p>
        <b className="mt-1 block text-lg font-black text-slate-950">{value}</b>
      </div>
    </div>
  )
}

function Eval({ item }: { item: EvaluationItem }) {
  const toneMap: Record<EvaluationItem["tone"], Tone> = {
    ok: "green",
    warn: "orange",
    bad: "red",
    info: "blue",
  }

  const iconTone = {
    ok: "bg-emerald-500",
    warn: "bg-orange-500",
    bad: "bg-red-500",
    info: "bg-blue-600",
  }[item.tone]

  const marker = item.tone === "ok" ? "✓" : item.tone === "info" ? "i" : "!"

  return (
    <div className="flex items-center gap-4 border-t py-3 first:border-t-0">
      <div className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-black text-white ${iconTone}`}>
        {marker}
      </div>
      <div className="min-w-0 flex-1">
        <b className="text-lg font-black text-slate-950">{item.title}</b>
        <p className="mt-0.5 text-[15px] font-bold leading-6 text-slate-600">{item.desc}</p>
      </div>
      <Chip tone={toneMap[item.tone]}>{item.status}</Chip>
    </div>
  )
}

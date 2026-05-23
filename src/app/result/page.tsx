import Image from "next/image"
import Link from "next/link"
import { CalendarDays, Gamepad2, Github, Hexagon, Users } from "lucide-react"
import { PageShell } from "@/components/PageShell"
import { Card } from "@/components/ui/card"
import { Bar, InfoTooltip } from "@/components/Common"
import { ScoreRing } from "@/components/ScoreRing"
import { getAnalysisResult } from "@/lib/analysisResult"

const moduleCards = [
  {
    title: "포트폴리오 진단",
    desc: "레포 구조, 품질, 개선점을 종합 진단합니다.",
    href: "/portfolio",
    image: "/images/module-portfolio.png",
    button: "/images/button1.png",
    tone: "green",
  },
  {
    title: "직무 매칭",
    desc: "FAISS 유사도와 도메인 분석으로 직무를 추천합니다.",
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
  const report = getAnalysisResult()
  return (
    <PageShell active="결과 요약">
      <h1 className="text-[42px] font-black tracking-[-0.05em] text-slate-950">분석이 완료되었습니다!</h1>
      <p className="mt-2 text-[19px] font-extrabold text-slate-600">입력하신 GitHub 포트폴리오에 대한 종합 분석 결과입니다.</p>

      <Card className="glass-card mt-5 p-5 pt-4">
        <h2 className="text-[28px] font-black tracking-[-0.04em] text-slate-950">GitHub 포트폴리오 종합 결과</h2>
        <div className="mt-2 grid grid-cols-[250px_1fr_1fr] items-center gap-7">
          <ScoreRing value={report.score.total} />

          <div>
            <div className="flex items-center gap-5">
              <div className="grid h-[76px] w-[76px] shrink-0 place-items-center rounded-full bg-blue-50 text-blue-600 ring-8 ring-blue-50/70">
                <Gamepad2 className="h-10 w-10" />
              </div>
              <div>
                <h3 className="text-[30px] font-black tracking-[-0.04em] text-slate-950">게임 개발 Entry 수준</h3>
                <p className="mt-1 text-[17px] font-extrabold leading-7 text-slate-700">
                  기본 개발 역량은 보유하고 있으며,
                  <br />
                  <b className="font-black text-blue-600">프로젝트 완성도와 결과물 보강</b>이 필요해요.
                </p>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-3 overflow-hidden rounded-xl border border-slate-200 bg-white text-sm">
              <Mini icon={<Github />} label="GitHub ID" value={report.applicant.githubId} />
              <Mini icon={<Users />} label="지원자 경력" value={report.applicant.career} />
              <Mini icon={<CalendarDays />} label="분석 레포지토리" value={`${report.applicant.repoCount}개`} />
              <Mini icon={<Hexagon />} label="주요 기술 스택" value={report.applicant.techStack.join(", ")} />
              <Mini icon={<Gamepad2 />} label="주요 도메인" value={report.applicant.domain} />
              <Mini icon={<Users />} label="레포 유형" value={report.applicant.repoType} />
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-[23px] font-black tracking-[-0.035em] text-slate-950">핵심 역량 점수</h3>
            <Score label="개발 활동량" val={`${report.score.activity} / 60`} pct={(report.score.activity / 60) * 100} image="/images/develop-activity.png" />
            <Score label="프로젝트 관리도" val={`${report.score.management.toFixed(1)} / 30`} pct={(report.score.management / 30) * 100} color="bg-purple-500" image="/images/project-management.png" />
            <Score label="작업 일관성" val={`${report.score.consistency} / 10`} pct={(report.score.consistency / 10) * 100} color="bg-emerald-500" image="/images/work-consistency.png" />
          </div>
        </div>
      </Card>

      <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/70 px-5 py-4 text-[16px] font-extrabold leading-7 text-slate-700">
        <InfoTooltip text="세부 피드백은 포트폴리오 진단 화면에서 레포별로 확인할 수 있습니다." /> 요약 화면은 전체 수준과 상세 분석 진입점을 제공합니다. 레포별 개선 항목은 포트폴리오 진단에서 확인하세요.
      </div>

      <h2 className="mt-4 text-[24px] font-black tracking-[-0.035em] text-slate-950">상세 분석 보기</h2>
      <div className="mt-3 grid grid-cols-3 gap-5">
        {moduleCards.map((module) => <DetailModuleCard key={module.title} {...module} />)}
      </div>

      <div className="mt-4 rounded-xl border border-slate-200 bg-white px-5 py-3 text-[15px] font-extrabold text-slate-600">
        <InfoTooltip text="결과는 포트폴리오와 채용 데이터 기반의 참고 지표이며, 실제 평가는 기업과 상황에 따라 달라질 수 있습니다." /> 분석 결과는 참고용입니다. 실제 채용 및 연봉은 회사, 지역, 개인 역량, 최신성 등에 따라 달라질 수 있습니다.
      </div>
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
        <Image
          src={image}
          alt=""
          width={70}
          height={70}
          className="mt-1 h-[70px] w-[70px] object-contain"
        />
        <div className="flex h-full min-w-0 flex-col justify-start pt-1">
          <h3 className="text-[24px] font-black tracking-[-0.04em] text-slate-950">{title}</h3>
          <p className="mt-1 max-w-[360px] text-[15px] font-extrabold leading-tight text-slate-600">{desc}</p>
          <Link href={href} className="mt-2 inline-flex w-fit">
            <Image
              src={button}
              alt="자세히 보기"
              width={145}
              height={40}
              className="h-10 w-[145px] object-contain transition hover:scale-[1.02]"
            />
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

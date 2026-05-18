import Link from "next/link"
import { PageShell } from "@/components/PageShell"
import { Bar, Breadcrumb, Card, Chip, FooterActions, InfoTooltip, PageTitle, StatRow } from "@/components/Common"
import { Button } from "@/components/ui/button"
import { getAnalysisResult } from "@/lib/analysisResult"

export default function JobsPage() {
  const report = getAnalysisResult()
  return (
    <PageShell active="직무 매칭">
      <Breadcrumb current="직무 매칭" />
      <PageTitle title="직무 매칭" desc="FAISS 유사도 검색과 도메인 분석을 통해 지원자에게 적합한 직무를 추천합니다." />

      <div className="grid grid-cols-[1fr_470px] gap-5">
        <Card className="p-5">
          <h2 className="flex items-center gap-3 text-[26px] font-black tracking-[-0.03em]">
            추천 직무 TOP 5
            <Chip>신입/경력무관/경력 미기재 기준</Chip>
          </h2>

          <div className="mt-4 grid grid-cols-[64px_1fr_190px_150px_150px] border-b pb-2.5 text-[15px] font-black text-slate-500">
            <span>순위</span>
            <span>직무 / 회사</span>
            <span>
              유효 점수 <InfoTooltip text="채용공고와 포트폴리오 신호의 유사도를 나타낸 값입니다. 높을수록 매칭도가 좋습니다." />
            </span>
            <span>경력 조건</span>
            <span>도메인 일치</span>
          </div>

          {report.jobs.map((j) => (
            <div
              key={j.rank}
              className="grid grid-cols-[64px_1fr_190px_150px_150px] items-center border-b py-2.5 last:border-b-0"
            >
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-blue-50 text-2xl font-black text-blue-600">
                {j.rank}
              </div>
              <div className="flex items-center gap-4">
                <Avatar name={j.company} rank={j.rank} />
                <div>
                  <b className="text-[18px] font-black tracking-[-0.02em]">{j.title}</b>
                  <p className="text-[15px] font-extrabold text-slate-600">{j.company}</p>
                </div>
              </div>
              <div>
                <b className="text-base font-black">{j.score}</b>
                <div className="mt-1.5 w-36">
                  <Bar value={j.rank === 1 ? 80 : j.rank === 2 ? 72 : j.rank === 3 ? 68 : j.rank === 4 ? 64 : 60} />
                </div>
              </div>
              <div className="justify-self-start">
                <Chip tone={j.exp === "신입" ? "green" : j.exp === "경력 무관" ? "green" : "gray"}>{j.exp}</Chip>
              </div>
              <div className="justify-self-start">
                <Chip tone={j.domain === "도메인 일치" ? "green" : j.domain === "보통" ? "blue" : j.domain === "낮음" ? "gray" : "orange"}>{j.domain}</Chip>
              </div>
            </div>
          ))}

          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
            <h3 className="flex items-center gap-3 text-[20px] font-black tracking-[-0.03em]">
              매칭 분포 안내
              <span className="text-[14px] font-extrabold text-slate-500">상위 공고의 유효 점수 분포</span>
            </h3>
            <div className="mt-3 grid grid-cols-4 overflow-hidden rounded-xl border border-slate-200 bg-white">
              {report.matchDistribution.map((item, index) => (
                <Dist key={item.label} active={index === 1} label={item.label} value={item.count} />
              ))}
            </div>
            <p className="mt-3 rounded-xl bg-white px-4 py-3 text-[15px] font-extrabold leading-6 text-slate-600">
              <InfoTooltip text="FAISS 기반 유사도 점수를 구간별로 나눈 분포입니다." /> 유사도 점수가 낮을수록 공고와의 일치도가 낮다는 의미입니다.
            </p>

            <div className="mt-3 flex items-center gap-3 rounded-xl border border-amber-100 bg-amber-50/70 px-4 py-3">
              <img src="/images/light.png" alt="추천 활용 팁" className="h-7 w-7 shrink-0 object-contain" />
              <p className="text-[16px] font-black leading-none text-slate-800">
                README, 기술 스택, 프로젝트 설명을 보강하면 더 높은 매칭 점수를 받을 수 있어요.
              </p>
            </div>
          </div>
        </Card>

        <div className="flex h-full flex-col gap-5">
          <Card className="flex-1 p-5">
            <h2 className="text-[22px] font-black tracking-[-0.03em]">매칭 분석 요약</h2>
            <div className="mt-3 space-y-1">
              <StatRow label="분석된 채용공고 수" value={report.jobSummary.totalPostings} />
              <StatRow label="추천 가능 공고 수" value={report.jobSummary.recommendedPostings} />
              <StatRow label="평균 유효 점수" value={report.jobSummary.averageScore} />
              <StatRow label="도메인 일치 상위 비율" value={report.jobSummary.domainMatchRatio} />
            </div>
          </Card>

          <Card className="flex-1 p-5">
            <h2 className="text-[22px] font-black tracking-[-0.03em]">기술 스택 매칭 분석</h2>
            <div className="mt-3 space-y-2.5">
              {report.techMatchNotes.map((item) => (
                <div key={item.label} className="rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <b className="text-[16px] font-black text-slate-900">{item.label}</b>
                    <span className="shrink-0 rounded-full bg-blue-50 px-3 py-1 text-xs font-black text-blue-700 ring-1 ring-blue-100">
                      {item.type}
                    </span>
                  </div>
                  <p className="mt-1 text-[14px] font-extrabold text-slate-600">{item.note}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
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
    <div className={`grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br ${colors[rank - 1]} text-lg font-black text-white shadow-sm`}>
      {label}
    </div>
  )
}

function Dist({ label, value, active }: { label: string; value: string; active?: boolean }) {
  return (
    <div className={`px-2.5 py-2.5 text-center text-[14px] font-extrabold ${active ? "bg-blue-600 text-white" : "bg-blue-50/60 text-slate-700"}`}>
      <p>{label}</p>
      <b className="mt-1 block text-[15px] font-black">{value}</b>
    </div>
  )
}

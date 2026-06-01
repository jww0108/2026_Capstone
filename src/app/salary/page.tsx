"use client"

import Image from "next/image"
import Link from "next/link"
import { BriefcaseBusiness, Database, FileWarning } from "lucide-react"
import { PageShell } from "@/components/PageShell"
import { Card } from "@/components/ui/card"
import { Breadcrumb, Chip, FooterActions, InfoTooltip } from "@/components/Common"
import { SalaryBand } from "@/components/SalaryBand"
import { Button } from "@/components/ui/button"
import { useAnalysis } from "@/context/AnalysisContext"
import { getRangePosition, parseMoneyToNumber } from "@/lib/utils"

export default function SalaryPage() {
  const { result: report, isHydrated } = useAnalysis({ redirectIfMissing: true })

  if (!isHydrated || !report) {
    return null
  }

  const hasPlatforms = report.salary.platforms.length > 0
  const hasRelatedJobs = report.salary.relatedJobs.length > 0
  const salaryLow = parseMoneyToNumber(report.salary.low)
  const salaryMedian = parseMoneyToNumber(report.salary.median)
  const salaryHigh = parseMoneyToNumber(report.salary.high)
  const { axisMin, axisMax, ticks } = getSalaryAxis(salaryLow, salaryHigh)
  const lowPosition = getRangePosition(salaryLow, axisMin, axisMax)
  const medianPosition = getRangePosition(salaryMedian, axisMin, axisMax)
  const highPosition = getRangePosition(salaryHigh, axisMin, axisMax)

  return (
    <PageShell active="시장 연봉 밴드">
      <Breadcrumb current="시장 연봉 밴드" />

      <div className="mb-4">
        <h1 className="flex items-center gap-2 text-[38px] font-black tracking-[-0.045em] text-slate-950">
          시장 연봉 밴드
          <InfoTooltip text="선택 직무의 신입~3년차 채용공고 기반 연봉 범위를 요약합니다." />
        </h1>
        <p className="mt-2 text-[17px] font-bold text-slate-700">
          선택된 매칭 직무의 신입~3년차 시장 연봉 범위를 확인할 수 있습니다.
        </p>
      </div>

      <Card className="px-6 py-4">
        <div className="grid grid-cols-[1.25fr_0.7fr_1fr] items-center divide-x divide-slate-200">
          <div className="flex items-center gap-4 pr-6">
            <div className="grid h-12 w-12 min-w-12 place-items-center rounded-xl bg-blue-50 text-blue-600">
              <BriefcaseBusiness className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <p className="text-[15px] font-black text-slate-500">선택된 매칭 직무</p>
              <div className="mt-1 flex flex-wrap items-center gap-3">
                <h2 className="text-[26px] font-black leading-none tracking-[-0.04em] text-blue-600">
                  {report.salary.role}
                </h2>
                {report.domainConsistent === true && (
                  <Chip tone="green">도메인 일치</Chip>
                )}
                {report.domainConsistent === false && (
                  <Chip tone="orange">도메인 검토 필요</Chip>
                )}
              </div>
            </div>
          </div>

          <div className="px-8">
            <p className="text-[15px] font-black text-slate-500">경력 구간</p>
            <b className="mt-1 block text-[27px] font-black leading-tight tracking-[-0.04em]">
              {report.salary.careerRange}
            </b>
          </div>

          <div className="px-8">
            <p className="text-[15px] font-black text-slate-500">데이터 출처</p>
            <b className="mt-1 block whitespace-nowrap text-[18px] font-black tracking-[-0.025em]">
              {report.salary.source}
            </b>
          </div>
        </div>
        {report.salary.note && (
          <p className="mt-3 border-t border-slate-200 pt-3 text-[14px] font-bold leading-6 text-slate-600">
            {report.salary.note}
          </p>
        )}
      </Card>

      <div className="mt-4 grid grid-cols-[1.3fr_1fr] items-stretch gap-4">
        <Card className="p-5">
          <h2 className="text-[24px] font-black tracking-[-0.035em]">
            시장 연봉 밴드 (연간) <InfoTooltip text="선택 직무의 채용공고 데이터를 기반으로 시장 중앙값과 분포 범위를 보여줍니다." />
          </h2>

          <div className="mt-5 grid grid-cols-[0.88fr_1.12fr] gap-5">
            <div>
              <p className="text-[18px] font-black tracking-[-0.035em] text-slate-800">시장 중앙값</p>
              <p className="mt-1 text-[58px] font-black leading-none tracking-[-0.06em] text-blue-600">
                {report.salary.median.replace("만원", "")}<span className="text-[28px] tracking-[-0.04em]">만원</span>
              </p>
            </div>

            <div className="min-w-0 border-l border-slate-200 pl-7">
              <p className="text-[18px] font-black tracking-[-0.035em] text-slate-800">실제 분포 범위</p>
              <p className="mt-3 break-keep text-[25px] font-black leading-tight tracking-[-0.055em] text-slate-950">
                {report.salary.low} ~ {report.salary.high}
              </p>
            </div>
          </div>

          <SalaryBand
            lowPosition={lowPosition}
            medianPosition={medianPosition}
            highPosition={highPosition}
            lowValue={report.salary.low}
            medianValue={report.salary.median}
            highValue={report.salary.high}
            ticks={ticks}
          />

          <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-[15px] font-black leading-6 text-slate-600">
            <InfoTooltip text="연봉 밴드는 시장 참고 범위이며, 회사 조건과 개인 협상력에 따라 달라질 수 있습니다." /> 본 수치는 개인 연봉 예측값이 아니라, 동일 직무·유사 경력 구간의 채용공고 기반 시장 참고 범위입니다.
          </div>
          {report.salary.rangeDescription && (
            <p className="mt-3 text-[14px] font-bold leading-6 text-slate-600">
              {report.salary.rangeDescription}
            </p>
          )}
        </Card>

        {hasPlatforms ? (
          <Card className="p-5">
            <h2 className="text-[24px] font-black tracking-[-0.035em]">
              플랫폼 데이터 <InfoTooltip text="연봉 데이터가 존재하는 플랫폼별 중앙값과 분포 범위를 비교합니다." />
            </h2>
            <div className="mt-4 space-y-3">
              {report.salary.platforms.map((platform) => (
                <Platform key={platform.name} {...platform} />
              ))}
            </div>
            {report.salary.platforms.length >= 2 && (
              <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-[15px] font-black text-emerald-700">
                ✓ 복수 플랫폼의 연봉 데이터를 함께 참고했습니다.
              </div>
            )}
          </Card>
        ) : (
          <NoDataCard />
        )}
      </div>

      <div className="mt-4 grid grid-cols-[1.3fr_1fr] items-stretch gap-4">
        {hasRelatedJobs ? (
          <Card className="p-5">
            <h2 className="text-[22px] font-black tracking-[-0.035em]">
              참고 직무 연봉 비교 <InfoTooltip text="매칭 직무와 도메인 또는 기술이 인접한 직무가 있을 때만 표시되는 참고 지표입니다." />
            </h2>
            <div className="mt-3 overflow-hidden rounded-xl border border-slate-200">
              <table className="w-full text-[15px] font-black">
                <thead className="bg-slate-50 text-left text-[14px] text-slate-500">
                  <tr className="border-b border-slate-200">
                    <th className="px-4 py-2.5">직무</th>
                    <th className="px-4 py-2.5">중앙값</th>
                    <th className="px-4 py-2.5">분포 범위</th>
                    <th className="px-4 py-2.5 text-right">비교</th>
                  </tr>
                </thead>
                <tbody>
                  {report.salary.relatedJobs.map((row) => (
                    <tr className="border-b border-slate-200 last:border-b-0" key={row[0]}>
                      {row.map((cell, index) => (
                        <td
                          className={`px-4 py-2.5 ${
                            index === 3
                              ? cell.startsWith("+")
                                ? "text-right font-black text-red-500"
                                : "text-right font-black text-blue-600"
                              : "text-slate-800"
                          }`}
                          key={cell}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ) : (
          <NoDataCard />
        )}

        <Card className="relative overflow-hidden border-blue-100 bg-blue-50/50 p-5 pb-8">
          <h2 className="flex items-center gap-2 text-[22px] font-black tracking-[-0.035em]">
            <Database className="h-6 w-6 text-blue-600" />데이터 해석 기준
          </h2>
          <ul className="relative z-10 mt-4 space-y-3 pr-24 text-[16px] font-black leading-7 text-slate-700">
            <li>✓ GitHub 점수는 연봉 계산에 직접 반영하지 않습니다.</li>
            <li>✓ 참고 직무는 도메인 유사성이 있을 때만 표시됩니다.</li>
            <li>✓ 회사 규모별 연봉은 데이터 신뢰도 문제로 제외했습니다.</li>
          </ul>
          <Image
            src="/images/mascot.png"
            alt="Git2Value 마스코트"
            width={118}
            height={118}
            className="pointer-events-none absolute bottom-3 right-4 h-[108px] w-[108px] object-contain drop-shadow-sm"
          />
        </Card>
      </div>

      <Card className="mt-4 border-orange-100 bg-orange-50/40 px-5 py-4">
        <div className="flex items-start gap-3">
          <Image src="/images/light.png" alt="" width={30} height={28} className="mt-0.5 h-7 w-7 object-contain" />
          <div>
            <h2 className="text-[21px] font-black tracking-[-0.035em]">연봉 참고 안내</h2>
            <div className="mt-2 grid grid-cols-2 gap-4 text-[16px] font-black leading-7 text-slate-700">
              <p>✓ 회사 규모, 지역, 복지, 협상력에 따라 실제 연봉은 달라질 수 있습니다.</p>
              <p>✓ 본 결과는 지원 전략 수립을 위한 참고 자료로 활용하는 것이 좋습니다.</p>
            </div>
          </div>
        </div>
      </Card>

      <FooterActions
        left={
          <Link href="/jobs">
            <Button variant="secondary" className="w-72 font-black">← 직무 매칭으로 돌아가기</Button>
          </Link>
        }
        right={
          <Link href="/result">
            <Button className="w-80 font-black">결과 요약으로 돌아가기 →</Button>
          </Link>
        }
      />
    </PageShell>
  )
}

function getSalaryAxis(low: number, high: number) {
  const rawMin = Math.min(low, high)
  const rawMax = Math.max(low, high)
  const axisMin = Math.max(0, Math.floor((rawMin - 250) / 500) * 500)
  const axisMax = Math.ceil((rawMax + 250) / 500) * 500
  const step = (axisMax - axisMin) / 4
  const ticks = Array.from({ length: 5 }, (_, index) => Math.round(axisMin + step * index))

  return { axisMin, axisMax, ticks }
}

function Platform({
  name,
  logo,
  median,
  range,
  count,
}: {
  name: string
  logo: string
  median: string
  range: string
  count: string
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3.5 py-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2.5">
          <b className={logo === "jumpit" ? "shrink-0 text-[19px] font-black text-red-500" : "shrink-0 text-[19px] font-black text-slate-900"}>{logo}</b>
          <span className="truncate text-[18px] font-black text-slate-800">{name}</span>
        </div>
        <span className="shrink-0 rounded-full bg-slate-50 px-3 py-1 text-[15px] font-black text-slate-600 ring-1 ring-slate-200">{count}</span>
      </div>
      <div className="mt-2.5 grid grid-cols-[0.9fr_1.1fr] gap-2.5">
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="text-[15px] font-black leading-5 text-slate-500">중앙값</p>
          <b className="mt-0.5 block whitespace-nowrap text-[20px] font-black leading-tight tracking-[-0.045em] text-slate-950">{median}</b>
        </div>
        <div className="rounded-lg bg-slate-50 px-3 py-2">
          <p className="text-[15px] font-black leading-5 text-slate-500">분포</p>
          <b className="mt-0.5 block whitespace-nowrap text-[19px] font-black leading-tight tracking-[-0.055em] text-slate-950">{range}</b>
        </div>
      </div>
    </div>
  )
}

function NoDataCard() {
  return (
    <Card className="border-slate-200 bg-slate-50 p-5">
      <h2 className="flex items-center gap-2 text-xl font-black text-slate-900">
        <FileWarning className="h-6 w-6 text-slate-500" />표시 가능한 참고 데이터가 부족합니다.
      </h2>
      <p className="mt-2 text-base font-extrabold text-slate-600">현재 매칭 직무의 연봉 밴드만 제공됩니다.</p>
    </Card>
  )
}

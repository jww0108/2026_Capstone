import Image from "next/image"
import Link from "next/link"
import { BriefcaseBusiness, Building2 } from "lucide-react"
import { PageShell } from "@/components/PageShell"
import { Breadcrumb, Card, Chip, FooterActions, InfoTooltip, PageTitle } from "@/components/Common"
import { Button } from "@/components/ui/button"
import { getAnalysisResult } from "@/lib/analysisResult"

export default function SalaryPage() {
  const report = getAnalysisResult()
  return (
    <PageShell active="시장 연봉 밴드">
      <Breadcrumb current="시장 연봉 밴드" />
      <PageTitle
        title="시장 연봉 밴드"
        desc="선택된 매칭 직무의 신입~3년차 시장 연봉 범위를 확인할 수 있습니다."
      />

      <Card className="px-7 py-5">
        <div className="grid grid-cols-[1.15fr_0.65fr_1fr] items-center divide-x divide-slate-200">
          <div className="flex items-center gap-4 pr-6">
            <div className="grid h-14 w-14 min-w-14 place-items-center rounded-xl bg-blue-50 text-blue-600">
              <BriefcaseBusiness className="h-7 w-7" />
            </div>
            <div className="min-w-0">
              <p className="text-base font-black text-slate-500">선택된 매칭 직무</p>
              <div className="mt-1 flex flex-wrap items-center gap-3">
                <h2 className="text-[27px] font-black leading-none tracking-[-0.04em] text-blue-600">
                  {report.salary.role}
                </h2>
                <Chip tone="green">도메인 일치</Chip>
              </div>
            </div>
          </div>

          <div className="px-10">
            <p className="text-base font-black text-slate-500">경력 구간</p>
            <b className="mt-1 block text-[28px] font-black leading-tight tracking-[-0.04em]">
              {report.salary.careerRange}
            </b>
          </div>

          <div className="px-10">
            <p className="text-base font-black text-slate-500">데이터 출처</p>
            <b className="mt-1 block whitespace-nowrap text-xl font-black tracking-[-0.025em]">
              {report.salary.source}
            </b>
          </div>
        </div>
      </Card>

      <div className="mt-4 grid grid-cols-[1fr_720px] items-stretch gap-5">
        <div className="flex h-full flex-col gap-4">
          <Card className="flex-[1.55] px-7 py-5">
            <h2 className="text-2xl font-black tracking-[-0.035em]">
              시장 연봉 밴드 (연간) <InfoTooltip text="선택 직무의 채용공고 데이터를 기반으로 시장 중앙값과 분포 범위를 보여줍니다." />
            </h2>

            <div className="mt-5 grid grid-cols-[0.86fr_1.14fr] gap-7">
              <div>
                <p className="text-xl font-black tracking-[-0.035em] text-slate-800">시장 중앙값</p>
                <p className="mt-2 text-[58px] font-black leading-none tracking-[-0.06em] text-blue-600">
                  {report.salary.median.replace("만원", "")}<span className="text-3xl tracking-[-0.04em]">만원</span>
                </p>
              </div>

              <div className="border-l border-slate-200 pl-9">
                <p className="text-xl font-black tracking-[-0.035em] text-slate-800">실제 분포 범위</p>
                <p className="mt-3 whitespace-nowrap text-[29px] font-black leading-tight tracking-[-0.055em] text-slate-950">
                  {report.salary.low} ~ {report.salary.high}
                </p>
              </div>
            </div>

            <div className="mt-7 px-2">
              <div className="relative h-[116px]">
                <div className="absolute left-1 right-1 top-[72px] h-4 rounded-full bg-gradient-to-r from-blue-300 via-blue-600 to-emerald-500" />
                <Marker className="left-[15.5%]" label="하위 25%" value={report.salary.low} tone="slate" />
                <Marker className="left-1/2" label="중앙값" value={report.salary.median} tone="blue" center />
                <Marker className="left-[88%]" label="상위 25%" value={report.salary.high} tone="slate" />
              </div>

              <div className="grid grid-cols-5 text-center text-base font-black text-slate-500">
                <span>2,500만원</span>
                <span>3,000만원</span>
                <span>3,500만원</span>
                <span>4,000만원</span>
                <span>4,500만원</span>
              </div>
            </div>

            <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 px-5 py-3 text-base font-black text-slate-600">
              <InfoTooltip text="연봉 밴드는 시장 참고 범위이며, 회사 조건과 개인 협상력에 따라 달라질 수 있습니다." /> 연봉은 회사 규모, 지역, 복지, 협상력 등에 따라 달라질 수 있습니다.
            </div>
          </Card>

          <Card className="flex flex-1 flex-col px-6 pt-4 pb-6">
            <h2 className="text-xl font-black tracking-[-0.035em]">
              회사 규모별 연봉 분포 <InfoTooltip text="회사 규모별로 기대할 수 있는 신입~3년차 연봉 범위를 참고용으로 정리합니다." />
            </h2>
            <div className="mt-8 grid grid-cols-4 gap-3">
              {report.salary.companySizes.map(([type, size, low, high]) => (
                <div key={type} className="rounded-xl border border-slate-200 bg-white px-4 py-4">
                  <div className="flex items-start gap-3">
                    <div className="grid h-10 w-10 min-w-10 place-items-center rounded-lg bg-blue-50 text-blue-700">
                      <Building2 className="h-6 w-6" />
                    </div>
                    <div>
                      <b className="block text-base font-black leading-none text-slate-900">{type}</b>
                      <p className="mt-1 text-sm font-black leading-tight text-slate-500">({size})</p>
                    </div>
                  </div>
                  <p className="mt-3 text-center text-lg font-black leading-tight tracking-[-0.035em] text-slate-950">
                    {low}<br />{high}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="flex h-full flex-col gap-4">
          <Card className="px-6 py-5">
            <h2 className="text-2xl font-black tracking-[-0.035em]">
              플랫폼 교차 검증 <InfoTooltip text="점핏과 원티드 데이터가 비슷한 범위를 보이는지 비교해 신뢰도를 확인합니다." />
            </h2>
            <div className="mt-2">
              {report.salary.platforms.map((platform) => (
                <Platform key={platform.name} {...platform} />
              ))}
            </div>
            <div className="mt-3 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 font-black text-emerald-700">
              ✓ 두 플랫폼의 연봉 데이터가 유사하게 나타나 신뢰도가 높습니다.
            </div>
          </Card>

          <Card className="flex-1 px-6 py-5">
            <h2 className="text-xl font-black tracking-[-0.035em]">
              참고 직무 연봉 비교 (신입 ~ 3년) <InfoTooltip text="추천 직무와 인접한 직무의 연봉 범위를 함께 보여주는 참고 지표입니다." />
            </h2>
            <table className="mt-3 w-full text-[15px] font-black">
              <thead className="text-left text-sm text-slate-500">
                <tr className="border-b">
                  <th className="pb-2">직무</th>
                  <th className="pb-2">중앙값</th>
                  <th className="pb-2">분포 범위</th>
                  <th className="pb-2 text-right">비교</th>
                </tr>
              </thead>
              <tbody>
                {report.salary.relatedJobs.map((row) => (
                  <tr className="border-b last:border-b-0" key={row[0]}>
                    {row.map((cell, index) => (
                      <td
                        className={`py-[7px] ${
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
          </Card>

          <Card className="border-orange-100 bg-orange-50/40 px-6 py-5">
            <h2 className="flex items-center gap-2 text-xl font-black tracking-[-0.035em]">
              <Image src="/images/light.png" alt="" width={30} height={28} />연봉 협상 팁
            </h2>
            <ul className="mt-3 space-y-2 text-base font-black leading-7 text-slate-700">
              <li>✓ 본인의 기술 스택과 프로젝트 경험을 구체적으로 연결해 어필하세요.</li>
              <li>✓ 연봉 외 복지, 성장 가능성, 팀 문화도 함께 고려하세요.</li>
            </ul>
          </Card>
        </div>
      </div>

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

function Marker({
  className,
  label,
  value,
  tone,
  center = false,
}: {
  className: string
  label: string
  value: string
  tone: "blue" | "slate"
  center?: boolean
}) {
  const textColor = tone === "blue" ? "text-blue-600" : "text-slate-800"
  const bgColor = tone === "blue" ? "bg-blue-50" : "bg-slate-100"
  const borderColor = tone === "blue" ? "border-blue-600" : "border-slate-300"

  return (
    <div className={`absolute top-0 w-max -translate-x-1/2 text-center ${className}`}>
      <div className={`inline-flex whitespace-nowrap rounded-full px-4 py-1 text-sm font-black ${bgColor} ${textColor}`}>
        {label}
      </div>
      <p className={`mt-1 whitespace-nowrap text-base font-black ${textColor}`}>{value}</p>
      {center ? (
        <>
          <div className="mx-auto mt-2 h-5 w-5 rounded-full border-[5px] border-blue-600 bg-white" />
          <div className={`mx-auto -mt-px h-[19px] w-0 border-l-2 ${borderColor}`} />
        </>
      ) : (
        <div className={`mx-auto mt-2 h-[30px] w-0 border-l-2 ${borderColor}`} />
      )}
    </div>
  )
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
    <div className="grid grid-cols-[86px_1fr_112px_174px_80px] items-center border-b py-3 last:border-b-0">
      <b className={logo === "jumpit" ? "font-black text-red-500" : "font-black text-slate-900"}>{logo}</b>
      <span className="font-black text-slate-800">{name} (2025.05)</span>
      <div>
        <p className="text-sm font-black text-slate-500">중앙값</p>
        <b className="font-black">{median}</b>
      </div>
      <div>
        <p className="text-sm font-black text-slate-500">분포</p>
        <b className="font-black">{range}</b>
      </div>
      <div className="text-right">
        <p className="text-sm font-black text-slate-500">공고 수</p>
        <b className="font-black">{count}</b>
      </div>
    </div>
  )
}

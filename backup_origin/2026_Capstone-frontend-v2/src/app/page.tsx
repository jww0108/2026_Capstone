"use client"

import Image from "next/image"
import { useRouter } from "next/navigation"
import { useState, type ReactNode } from "react"
import { Github, Link as LinkIcon, Rocket, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { InfoTooltip } from "@/components/Common"
import { PublicHeader } from "@/components/Header"
import { landingGuideRows, landingProcessItems, landingResultCards, type LandingResultCard } from "@/data/uiContent"

export default function MainInputPage() {
  const router = useRouter()
  const [githubId, setGithubId] = useState("")
  const [repos, setRepos] = useState(["", "", ""])

  return (
    <div className="min-h-screen soft-grid-bg">
      <PublicHeader />
      <main className="mx-auto max-w-[1720px] px-10 py-6">
        <section className="grid items-stretch gap-10 lg:grid-cols-[1.05fr_.95fr]">
          <Card className="glass-card flex h-full flex-col p-10">
            <h1 className="text-[54px] font-black tracking-[-0.055em] text-slate-950">
              GitHub 포트폴리오 <span className="text-blue-600">분석 시작</span>
            </h1>
            <p className="mt-5 text-[22px] font-extrabold leading-9 text-slate-600">
              GitHub ID와 대표 레포지토리를 입력하면 포트폴리오 진단, 직무 매칭,
              <br />시장 연봉 밴드를 분석합니다.
            </p>

            <div className="mt-8 flex flex-1 flex-col justify-between gap-6">
              <div className="space-y-6">
                <div>
                  <label className="mb-2 block text-xl font-black text-slate-950">GitHub ID</label>
                  <div className="relative">
                    <Github className="absolute left-4 top-1/2 h-6 w-6 -translate-y-1/2 text-slate-400" />
                    <input
                      className="h-14 w-full rounded-xl border border-slate-200 bg-white pl-14 text-lg font-extrabold outline-none transition placeholder:font-bold placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                      placeholder="예: user"
                      value={githubId}
                      onChange={(e) => setGithubId(e.target.value)}
                    />
                  </div>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-xl font-black text-slate-950">
                      분석할 레포지토리 <InfoTooltip text="분석할 GitHub 레포지토리 URL을 최대 3개까지 입력할 수 있습니다. 공개 레포만 분석됩니다." />
                    </label>
                  </div>
                  <div className="space-y-3">
                    {repos.map((repo, idx) => (
                      <div className="relative" key={idx}>
                        <LinkIcon className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                        <input
                          className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-14 text-lg font-extrabold outline-none transition placeholder:font-bold placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                          placeholder="https://github.com/user/repository"
                          value={repo}
                          onChange={(e) => setRepos(repos.map((r, i) => (i === idx ? e.target.value : r)))}
                        />
                      </div>
                    ))}
                  </div>
                  <p className="mt-2 text-base font-extrabold text-slate-500">대표 프로젝트 중심으로 최대 3개까지 분석합니다.</p>
                </div>
              </div>

              <div className="pt-1">
                <Button size="lg" className="h-14 w-full text-xl font-black" onClick={() => router.push("/loading")}>
                  <Rocket className="h-6 w-6" />분석 시작하기
                </Button>
                <p className="mt-3 text-center text-base font-extrabold text-slate-500">◷ 예상 소요 시간: 약 30초 ~ 2분</p>
              </div>
            </div>
          </Card>

          <div className="grid h-full grid-rows-[minmax(0,1fr)_auto] gap-5">
            <Card className="glass-card flex min-h-[348px] items-center justify-center overflow-hidden bg-[#eef5ff] p-0">
              <Image
                src="/images/hero-dashboard.png"
                alt="Git2Value dashboard preview"
                width={747}
                height={331}
                priority
                className="h-full w-full object-contain"
              />
            </Card>

            <div className="grid min-h-[214px] grid-cols-[1fr_.46fr] gap-5">
              <Card className="glass-card flex h-full flex-col p-6">
                <h2 className="text-2xl font-black text-slate-950">분석 결과</h2>
                <div className="mt-4 flex flex-1 flex-col justify-between gap-2.5">
                  {landingResultCards.map((item) => <ResultItem key={item.title} {...item} />)}
                </div>
              </Card>

              <Card className="glass-card flex h-full flex-col p-6">
                <h2 className="text-2xl font-black text-slate-950">시작 안내</h2>
                <div className="mt-4 flex flex-1 flex-col justify-between text-[15px] font-black leading-6 text-slate-700">
                  {landingGuideRows.map((row, index) => {
                    const Icon = row.icon
                    return (
                      <div key={row.lines.join("-")}>
                        <GuideRow icon={<Icon className="h-7 w-7 text-slate-900" />} lines={row.lines} />
                        {index < landingGuideRows.length - 1 && <div className="mt-3 border-t" />}
                      </div>
                    )
                  })}
                </div>
              </Card>
            </div>
          </div>
        </section>

        <Card className="glass-card mt-6 p-5">
          <div className="relative grid grid-cols-3 items-center">
            <StepConnector className="left-[30.65%]" />
            <StepConnector className="left-[66.35%]" />
            {landingProcessItems.map(({ title, desc, Icon }, index) => (
              <div
                key={title}
                className={`grid grid-cols-[86px_minmax(220px,1fr)] items-center gap-5 ${
                  index === 0 ? "justify-self-start pl-3" : index === 1 ? "justify-self-center" : "justify-self-end pr-12"
                }`}
              >
                <div className="grid h-20 w-20 place-items-center rounded-full bg-blue-50 text-blue-600">
                  <Icon className="h-12 w-12" />
                </div>
                <div className="min-w-[220px]">
                  <h3 className="text-2xl font-black text-blue-600">{title}</h3>
                  <p className="mt-2 whitespace-pre text-[17px] font-extrabold leading-7 text-slate-600">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </main>
    </div>
  )
}

function StepConnector({ className }: { className: string }) {
  return (
    <div className={`pointer-events-none absolute top-1/2 z-10 flex -translate-x-1/2 -translate-y-1/2 items-center gap-4 ${className}`}>
      <span className="h-0 w-14 border-t-2 border-dotted border-slate-300" />
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-blue-600 text-white shadow-sm">
        <ArrowRight className="h-5 w-5" />
      </span>
      <span className="h-0 w-14 border-t-2 border-dotted border-slate-300" />
    </div>
  )
}

function ResultItem({ title, desc, image, tone }: LandingResultCard) {
  const style =
    tone === "emerald"
      ? "border-emerald-200 bg-emerald-50/30"
      : tone === "purple"
        ? "border-purple-200 bg-purple-50/30"
        : "border-orange-200 bg-orange-50/30"

  return (
    <div className={`flex min-h-[52px] items-center gap-3 rounded-xl border px-3 py-2.5 transition hover:shadow-sm ${style}`}>
      <Image src={image} alt="" width={42} height={42} className="h-10 w-10 object-contain" />
      <div className="min-w-0 flex-1">
        <b className="block text-[17px] font-black leading-5 text-slate-950">{title}</b>
        <p className="mt-0.5 line-clamp-1 text-[13px] font-extrabold leading-5 text-slate-600">{desc}</p>
      </div>
      <span className="text-2xl font-black text-slate-400">›</span>
    </div>
  )
}

function GuideRow({ icon, lines }: { icon: ReactNode; lines: string[] }) {
  return (
    <p className="flex items-center gap-3">
      <span className="grid h-10 w-10 place-items-center rounded-full bg-slate-50">{icon}</span>
      <span>{lines.map((line) => <span className="block" key={line}>{line}</span>)}</span>
    </p>
  )
}

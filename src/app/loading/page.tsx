"use client"

import { useEffect, useRef, useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { Check, HelpCircle, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { WorkHeader } from "@/components/Header"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useAnalysisContext } from "@/context/AnalysisContext"
import { loadingSteps } from "@/data/uiContent"
import { analyzePortfolio, AnalyzePortfolioError } from "@/lib/analysisResult"
import {
  clearPendingAnalysisRequest,
  readPendingAnalysisRequest,
} from "@/lib/pendingAnalysis"
import { clampPercent } from "@/lib/utils"
import type { AnalysisRequest } from "@/types/analysis"

const AUTO_REDIRECT = true
const STEP_DELAY = 1450
const RESULT_DELAY = 800

type StepStatus = "done" | "active" | "waiting"

export default function LoadingPage() {
  const router = useRouter()
  const { setSession, isHydrated } = useAnalysisContext()
  const [pendingRequest, setPendingRequest] = useState<AnalysisRequest | null>(null)
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(6)
  const [isComplete, setIsComplete] = useState(false)
  const [failedMessage, setFailedMessage] = useState("")
  const analysisStarted = useRef(false)

  useEffect(() => {
    if (!isHydrated) return
    const request = readPendingAnalysisRequest()
    if (!request) {
      router.replace("/")
      return
    }
    setPendingRequest(request)
  }, [isHydrated, router])

  useEffect(() => {
    if (!pendingRequest || analysisStarted.current || failedMessage) return
    analysisStarted.current = true

    analyzePortfolio(pendingRequest)
      .then((result) => {
        clearPendingAnalysisRequest()
        setSession({
          request: pendingRequest,
          result,
          analyzedAt: new Date().toISOString(),
        })
        setCurrentStep(loadingSteps.length - 1)
        setProgress(100)
        setIsComplete(true)
      })
      .catch((error: unknown) => {
        clearPendingAnalysisRequest()
        if (error instanceof AnalyzePortfolioError) {
          if (error.statusCode === 503) {
            setFailedMessage("분석 서버가 준비되지 않았습니다. 잠시 후 다시 시도해 주세요.")
          } else if (error.statusCode === 400) {
            setFailedMessage(error.message)
          } else {
            setFailedMessage(error.message || "분석 중 문제가 발생했습니다.")
          }
        } else {
          setFailedMessage("네트워크 오류가 발생했습니다. 연결 상태를 확인해 주세요.")
        }
      })
  }, [pendingRequest, failedMessage, setSession])

  useEffect(() => {
    if (failedMessage || isComplete) return

    const stepTimer = window.setTimeout(() => {
      setCurrentStep((prev) => Math.min(prev + 1, loadingSteps.length - 2))
    }, STEP_DELAY)

    return () => window.clearTimeout(stepTimer)
  }, [currentStep, failedMessage, isComplete])

  useEffect(() => {
    if (failedMessage || isComplete) return

    const targetProgress = Math.min(96, Math.round(((currentStep + 1) / loadingSteps.length) * 100))
    const progressTimer = window.setInterval(
      () => setProgress((prev) => (prev >= targetProgress ? prev : Math.min(targetProgress, prev + 1))),
      35
    )
    return () => window.clearInterval(progressTimer)
  }, [currentStep, failedMessage, isComplete])

  useEffect(() => {
    if (!isComplete || !AUTO_REDIRECT) return
    const redirectTimer = window.setTimeout(() => router.push("/result"), RESULT_DELAY)
    return () => window.clearTimeout(redirectTimer)
  }, [isComplete, router])

  const getStepStatus = (index: number): StepStatus => {
    if (isComplete || index < currentStep) return "done"
    if (index === currentStep) return "active"
    return "waiting"
  }

  const activeStepTitle = failedMessage
    ? "분석 상태 확인 필요"
    : isComplete
      ? "분석 결과 리포트 생성 완료"
      : loadingSteps[currentStep]?.title ?? "분석 중"
  const safeProgress = clampPercent(progress)

  const githubId = pendingRequest?.github_username ?? "—"
  const repoCount = pendingRequest?.repos.length ?? 0
  const career = pendingRequest?.applicant_years === 0 ? "신입 0년차" : `${pendingRequest?.applicant_years ?? 0}년차`

  return (
    <div className="min-h-screen bg-slate-50">
      <WorkHeader mode="loading" />
      <main className="pt-16">
        <div className="mx-auto max-w-[1600px] px-12 py-6">
          <Card className="glass-card p-12">
            <h1 className="flex items-center gap-3 text-[40px] font-black tracking-[-0.045em]">
              GitHub 포트폴리오 분석 중
              {!isComplete ? <Loader2 className="h-8 w-8 animate-spin text-blue-600" /> : <Check className="h-8 w-8 rounded-full bg-emerald-500 p-1 text-white" />}
            </h1>
            <p className="mt-4 text-lg font-bold text-slate-600">
              입력하신 정보를 기반으로 GitHub 레포지토리를 분석하고 있습니다.
            </p>

            <div className="mt-8 grid grid-cols-3 rounded-2xl bg-slate-50 p-6 ring-1 ring-slate-100">
              <InfoBlock image="/images/githubID_logo.png" label="GitHub ID" value={githubId} />
              <InfoBlock image="/images/repository_logo.png" label="분석 레포지토리" value={`${repoCount}개`} />
              <InfoBlock image="/images/experience_logo.png" label="지원자 경력" value={career} />
            </div>

            <div className="mt-8 grid grid-cols-[1fr_380px] gap-7">
              <Card className="p-7 shadow-none">
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <h2 className="text-2xl font-black">분석 진행 단계</h2>
                    <p className="mt-2 text-sm font-bold text-slate-500">현재 단계: {activeStepTitle}</p>
                  </div>
                  <span className="rounded-full bg-blue-50 px-4 py-2 text-sm font-black text-blue-700">
                    {failedMessage ? "확인 필요" : isComplete ? "완료" : `${currentStep + 1} / ${loadingSteps.length}`}
                  </span>
                </div>

                {failedMessage && (
                  <div className="mt-4 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-base font-black text-red-700">
                    {failedMessage}
                  </div>
                )}

                <div className="mt-6">
                  {loadingSteps.map((step, index) => (
                    <StepItem
                      key={step.title}
                      index={index}
                      title={step.title}
                      description={step.description}
                      status={getStepStatus(index)}
                    />
                  ))}
                </div>
              </Card>

              <Card className="p-8 shadow-none">
                <h2 className="text-2xl font-black">분석 진행률</h2>
                <div
                  className="mx-auto mt-10 grid h-56 w-56 place-items-center rounded-full border-[18px] border-blue-100"
                  style={{
                    background: `conic-gradient(#2563eb ${safeProgress * 3.6}deg,#eef2ff 0deg)`,
                    transition: "background 180ms linear",
                  }}
                >
                  <div className="grid h-40 w-40 place-items-center rounded-full bg-white">
                    <div className="text-center">
                      <b className="text-5xl font-black">{Math.round(safeProgress)}%</b>
                      <p className="mt-1 font-black text-slate-500">
                        {failedMessage ? "대기" : isComplete ? "완료" : "분석 중..."}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="mt-8 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm font-bold leading-6 text-slate-700">
                  <div className="flex items-center gap-2 text-slate-950">
                    <Image src="/images/light.png" alt="" width={26} height={24} />
                    분석 진행 안내
                  </div>
                  <ul className="mt-2 list-disc pl-5">
                    <li>서버에서 E2E 분석이 진행되는 동안 단계별 진행 상태를 표시합니다.</li>
                    <li>분석이 완료되면 자동으로 결과 화면으로 이동합니다.</li>
                    <li>분석 실패 시 이 화면에서 문제를 확인할 수 있습니다.</li>
                  </ul>
                </div>
              </Card>
            </div>

            <div className="mt-7 flex items-center justify-between rounded-2xl border p-5">
              <div className="flex items-center gap-4">
                <Image src="/images/mascot.png" alt="Git2Value mascot" width={113} height={95} className="h-[92px] w-[110px] object-contain" />
                <div>
                  <b className="text-xl font-black">
                    {failedMessage
                      ? "문제 해결 가이드를 확인해 주세요."
                      : isComplete
                        ? "분석이 완료되었습니다!"
                        : "잠시만 기다려주세요!"}
                  </b>
                  <p className="font-bold text-slate-600">
                    {failedMessage
                      ? "입력값, GitHub 접근 권한, 서버 상태를 확인하면 대부분 해결할 수 있습니다."
                      : isComplete
                        ? "곧 결과 요약 화면으로 이동합니다."
                        : "정확하고 신뢰할 수 있는 분석 결과를 제공하기 위해 최선을 다해 분석하고 있습니다."}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-sm font-black text-slate-600">분석 진행 중 문제가 발생했나요?</span>
                <Link href="/help">
                  <Button variant="secondary" className="font-black">
                    <HelpCircle className="h-5 w-5" />
                    문제 해결 가이드 보기
                  </Button>
                </Link>
                {isComplete && (
                  <Link href="/result">
                    <Button className="font-black">결과 확인하기</Button>
                  </Link>
                )}
                {failedMessage && (
                  <Link href="/">
                    <Button className="font-black">다시 입력하기</Button>
                  </Link>
                )}
              </div>
            </div>
          </Card>
          <p className="mt-8 text-center text-sm font-bold text-slate-500">© 2024 Git2Value. All rights reserved.</p>
        </div>
      </main>
    </div>
  )
}

function StepItem({
  index,
  title,
  description,
  status,
}: {
  index: number
  title: string
  description: string
  status: StepStatus
}) {
  const isDone = status === "done"
  const isActive = status === "active"
  return (
    <div
      className={`flex items-center gap-5 border-l-2 py-4 pl-5 transition-all duration-300 ${
        isDone ? "border-emerald-400" : isActive ? "rounded-xl border-blue-500 bg-blue-50/70" : "border-slate-200"
      }`}
    >
      <div
        className={`grid h-8 w-8 -translate-x-[37px] place-items-center rounded-full text-sm font-black transition-all duration-300 ${
          isDone ? "bg-emerald-500 text-white" : isActive ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-600"
        }`}
      >
        {isDone ? <Check className="h-5 w-5" /> : index + 1}
      </div>
      <div className="-ml-8 flex-1">
        <h3 className={`text-xl font-black ${isActive ? "text-blue-700" : "text-slate-950"}`}>
          {index + 1}. {title}
        </h3>
        <p className="mt-1 text-base font-bold text-slate-600">{description}</p>
      </div>
      <div className="flex min-w-[110px] items-center justify-end gap-3">
        {isDone && <span className="rounded-full bg-emerald-50 px-4 py-1 text-sm font-black text-emerald-700">완료</span>}
        {isActive && (
          <>
            <span className="rounded-full bg-blue-100 px-4 py-1 text-sm font-black text-blue-700">진행 중</span>
            <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          </>
        )}
        {status === "waiting" && (
          <span className="rounded-full bg-slate-100 px-4 py-1 text-sm font-black text-slate-600">대기</span>
        )}
      </div>
    </div>
  )
}

function InfoBlock({ image, label, value }: { image: string; label: string; value: string }) {
  return (
    <div className="flex items-center justify-center gap-4 border-r last:border-r-0">
      <Image src={image} alt="" width={56} height={44} className="h-11 w-14 object-contain" />
      <div>
        <p className="text-sm font-black text-slate-500">{label}</p>
        <p className="text-xl font-black">{value}</p>
      </div>
    </div>
  )
}

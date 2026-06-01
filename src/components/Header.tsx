"use client"

import { useState } from "react"
import Link from "next/link"
import { CheckCircle2, Download, RotateCcw, Share2, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { BrandLogo } from "@/components/BrandLogo"
import { InfoTooltip } from "@/components/Common"

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-40 h-20 border-b border-slate-200 bg-white/92 backdrop-blur">
      <div className="mx-auto flex h-full max-w-[1720px] items-center justify-between px-10">
        <BrandLogo variant="main" />
        <nav className="flex items-center gap-12 text-[19px] font-extrabold text-slate-900">
          <a className="cursor-pointer">About</a>
          <Link href="/help">Guide</Link>
        </nav>
      </div>
    </header>
  )
}

export function WorkHeader({ mode = "result" }: { mode?: "loading" | "result" | "help" }) {
  const [toastMessage, setToastMessage] = useState("")
  const [isSavingPdf, setIsSavingPdf] = useState(false)

  const showToast = (message: string) => {
    setToastMessage(message)
    window.setTimeout(() => setToastMessage(""), 2200)
  }

  const handleShare = async () => {
    const url = window.location.href

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url)
      } else {
        const textarea = document.createElement("textarea")
        textarea.value = url
        textarea.style.position = "fixed"
        textarea.style.left = "-9999px"
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand("copy")
        document.body.removeChild(textarea)
      }

      showToast("결과 링크가 복사되었습니다.")
    } catch {
      showToast("링크 복사에 실패했습니다. 주소창의 URL을 직접 복사해주세요.")
    }
  }

  const handleSavePdf = () => {
    const target = document.querySelector<HTMLElement>("[data-pdf-content]") ?? document.querySelector<HTMLElement>("main")

    if (!target) {
      showToast("PDF로 저장할 화면 영역을 찾지 못했습니다.")
      return
    }

    try {
      setToastMessage("")
      setIsSavingPdf(true)
      document.body.classList.add("pdf-print-mode")

      const printContentWidth = 1440
      const pageWidthPx = ((297 - 16) / 25.4) * 96
      const pageHeightPx = ((210 - 16) / 25.4) * 96
      const targetHeight = Math.max(target.scrollHeight, target.offsetHeight)
      const fitScale = Math.min(0.98, pageWidthPx / printContentWidth, pageHeightPx / Math.max(targetHeight, 1))
      const printScale = Math.max(0.54, fitScale)

      document.documentElement.style.setProperty("--pdf-content-width", `${printContentWidth}px`)
      document.documentElement.style.setProperty("--pdf-scale", printScale.toFixed(3))

      const cleanup = () => {
        document.body.classList.remove("pdf-print-mode")
        document.documentElement.style.removeProperty("--pdf-scale")
        document.documentElement.style.removeProperty("--pdf-content-width")
        setIsSavingPdf(false)
        window.removeEventListener("afterprint", cleanup)
      }

      window.addEventListener("afterprint", cleanup)

      window.setTimeout(() => {
        window.print()
      }, 180)

      window.setTimeout(() => {
        if (document.body.classList.contains("pdf-print-mode")) {
          cleanup()
        }
      }, 3200)
    } catch (error) {
      console.error(error)
      document.body.classList.remove("pdf-print-mode")
      document.documentElement.style.removeProperty("--pdf-scale")
      document.documentElement.style.removeProperty("--pdf-content-width")
      setIsSavingPdf(false)
      showToast("PDF 저장 중 문제가 발생했습니다.")
    }
  }

  return (
    <>
      <header className="fixed left-0 top-0 z-40 h-16 w-full border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="flex h-full items-center justify-between px-8">
          <BrandLogo variant="service" />
          {mode === "loading" ? (
            <div className="flex items-center gap-4">
              <Link href="/" className="flex items-center gap-2 text-base font-extrabold text-slate-700"><InfoTooltip text="Git2Value 입력 화면과 서비스 흐름을 확인할 수 있습니다." />서비스 소개</Link>
              <Button variant="secondary" className="font-extrabold"><X className="h-5 w-5" />분석 취소</Button>
            </div>
          ) : mode === "help" ? (
            <Link href="/loading"><Button variant="secondary" className="px-6 font-extrabold">← 분석 진행 화면으로 돌아가기</Button></Link>
          ) : (
            <div className="flex items-center gap-4">
              <Button variant="secondary" className="font-extrabold" onClick={handleSavePdf} disabled={isSavingPdf}>
                <Download className="h-5 w-5" />{isSavingPdf ? "PDF 생성 중" : "PDF 저장"}
              </Button>
              <Button variant="secondary" className="font-extrabold" onClick={handleShare}>
                <Share2 className="h-5 w-5" />결과 공유
              </Button>
              <Link href="/"><Button variant="secondary" className="border-blue-300 font-extrabold text-blue-700"><RotateCcw className="h-5 w-5" />다시 분석하기</Button></Link>
            </div>
          )}
        </div>
      </header>

      {toastMessage && (
        <div data-no-print className="fixed bottom-6 left-6 z-[80] flex max-w-[360px] items-center gap-3 rounded-2xl border border-blue-100 bg-white px-5 py-4 text-base font-black text-slate-800 shadow-xl shadow-slate-300/40">
          <CheckCircle2 className="h-6 w-6 shrink-0 text-blue-600" />
          <span>{toastMessage}</span>
        </div>
      )}
    </>
  )
}

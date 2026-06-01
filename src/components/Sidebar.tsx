"use client"
import Image from "next/image"
import Link from "next/link"
import { BarChart3, BriefcaseBusiness, CircleCheck, FileInput, Activity, WalletCards } from "lucide-react"
import { cn } from "@/lib/utils"

const items = [
  ["입력 정보", "/", FileInput],
  ["분석 진행", "/loading", Activity],
  ["결과 요약", "/result", BarChart3],
  ["포트폴리오 진단", "/portfolio", CircleCheck],
  ["직무 매칭", "/jobs", BriefcaseBusiness],
  ["시장 연봉 밴드", "/salary", WalletCards],
] as const

export function Sidebar({ active }: { active: string }) {
  return (
    <aside className="fixed left-0 top-16 h-[calc(100vh-4rem)] w-[270px] border-r border-slate-200 bg-white px-4 py-8">
      <nav className="space-y-4">
        {items.map(([label, href, Icon]) => (
          <Link key={label} href={href} className={cn("flex h-16 items-center gap-5 rounded-2xl px-5 text-xl font-black leading-none tracking-[-0.01em] text-slate-800 transition hover:bg-blue-50/80", active === label && "bg-blue-50 text-blue-700 shadow-sm ring-1 ring-blue-100") }>
            <Icon className="h-7 w-7 shrink-0 stroke-[2.4]" /><span className="whitespace-nowrap">{label}</span>
          </Link>
        ))}
      </nav>
    </aside>
  )
}

export function HelpSidebar() {
  return (
    <aside className="fixed left-0 top-16 flex h-[calc(100vh-4rem)] w-[270px] items-center justify-center border-r border-slate-200 bg-white p-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-soft">
        <Image src="/images/mascot.png" alt="Git2Value mascot" width={130} height={110} className="mx-auto mb-4 h-[110px] w-[130px] object-contain" />
        <p className="text-lg font-black text-slate-950">문제가 해결되지 않나요?</p>
        <p className="mt-2 text-sm font-bold leading-6 text-slate-600">문의하기를 통해<br/>상세한 도움을 받을 수 있어요.</p>
        <button className="mt-5 h-11 w-full rounded-xl border border-slate-200 bg-white font-black text-blue-700 transition hover:border-blue-200 hover:bg-blue-50">문의하기 ↗</button>
      </div>
    </aside>
  )
}

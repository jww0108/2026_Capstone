import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

const pageInfoText: Record<string, string> = {
  "직무 매칭": "포트폴리오 신호와 채용공고 유사도를 비교해 적합한 직무를 추천합니다.",
  "시장 연봉 밴드": "선택 직무의 신입~3년차 채용공고 기반 연봉 범위를 요약합니다.",
}

export function Breadcrumb({ current }: { current: string }) {
  return <div className="mb-5 text-base font-extrabold text-slate-500">결과 요약 <span className="mx-4 text-slate-400">›</span> <span className="text-slate-950">{current}</span></div>
}

export function InfoTooltip({ text, className }: { text: string; className?: string }) {
  return (
    <span
      className={cn("group relative inline-flex align-middle", className)}
      tabIndex={0}
      aria-label={text}
    >
      <span className="grid h-[19px] w-[19px] cursor-help place-items-center rounded-full border border-slate-300 bg-white text-[12px] font-black leading-none text-slate-500 transition group-hover:border-blue-300 group-hover:text-blue-600 group-focus:border-blue-300 group-focus:text-blue-600">
        i
      </span>
      <span className="pointer-events-none absolute left-1/2 top-[calc(100%+8px)] z-50 hidden w-max max-w-[280px] -translate-x-1/2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-[13px] font-extrabold leading-5 text-slate-700 shadow-lg shadow-slate-200/80 group-hover:block group-focus:block">
        {text}
        <span className="absolute -top-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border-l border-t border-slate-200 bg-white" />
      </span>
    </span>
  )
}

export function PageTitle({ title, desc, info }: { title: string; desc: string; info?: string }) {
  const tooltip = info ?? pageInfoText[title] ?? "이 화면에서 확인할 수 있는 핵심 분석 정보입니다."

  return (
    <div className="mb-6">
      <h1 className="flex items-center gap-2 text-[40px] font-black tracking-[-0.045em] text-slate-950">
        {title}
        <InfoTooltip text={tooltip} />
      </h1>
      <p className="mt-3 text-lg font-bold text-slate-700">{desc}</p>
    </div>
  )
}

export function StatRow({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between py-2.5 text-base"><span className="font-bold text-slate-600">{label}</span><b className="text-lg font-black text-slate-950">{value}</b></div>
}

export function Bar({ value, color = "bg-blue-600" }: { value: number; color?: string }) {
  return <div className="h-2.5 rounded-full bg-slate-200"><div className={cn("h-full rounded-full", color)} style={{ width: `${value}%` }} /></div>
}

export function Chip({ children, tone = "blue" }: { children: React.ReactNode; tone?: "blue" | "green" | "orange" | "red" | "gray" | "purple" }) {
  const map = {
    blue: "bg-blue-50 text-blue-700 ring-blue-100",
    green: "bg-emerald-50 text-emerald-700 ring-emerald-100",
    orange: "bg-orange-50 text-orange-700 ring-orange-100",
    red: "bg-red-50 text-red-700 ring-red-100",
    gray: "bg-slate-100 text-slate-600 ring-slate-200",
    purple: "bg-purple-50 text-purple-700 ring-purple-100",
  }
  return <span className={cn("inline-flex items-center rounded-full px-3 py-1 text-sm font-black ring-1", map[tone])}>{children}</span>
}

export function FooterActions({ left, right, center }: { left?: React.ReactNode; center?: React.ReactNode; right?: React.ReactNode }) {
  return <div className="mt-6 flex items-center justify-between gap-4"><div>{left}</div><div className="ml-auto flex gap-4">{center}{right}</div></div>
}

export { Card }

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function clampPercent(value: number) {
  if (!Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, value))
}

export function scoreToPercent(score: string | number) {
  const numeric = typeof score === "number" ? score : Number(String(score).replace("%", ""))
  if (!Number.isFinite(numeric)) return 0
  return clampPercent(numeric <= 1 ? numeric * 100 : numeric)
}

export function parseMoneyToNumber(value: string | number) {
  if (typeof value === "number") return value
  const numeric = Number(String(value).replace(/[^0-9.-]/g, ""))
  return Number.isFinite(numeric) ? numeric : 0
}

/** KRW 원 단위 → "3,701만원" 형식 (만원 단위) */
export function formatMoneyWon(amount: number): string {
  if (!Number.isFinite(amount)) return "—"
  const man = Math.round(amount / 10_000)
  return `${man.toLocaleString("ko-KR")}만원`
}

export function formatMoneyRangeWon(low: number, high: number): string {
  return `${formatMoneyWon(low)} ~ ${formatMoneyWon(high)}`
}

export function getRangePosition(value: number, min: number, max: number) {
  if (!Number.isFinite(value) || !Number.isFinite(min) || !Number.isFinite(max) || max <= min) return 50
  return clampPercent(((value - min) / (max - min)) * 100)
}

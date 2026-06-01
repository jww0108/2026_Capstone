"use client"

import { useEffect, useMemo, useState } from "react"
import { clampPercent } from "@/lib/utils"

export function ScoreRing({ value = 70.8, size = 178 }: { value?: number; size?: number }) {
  const stroke = 14
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const targetValue = useMemo(() => clampPercent(value), [value])
  const [animatedValue, setAnimatedValue] = useState(0)

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setAnimatedValue(targetValue))
    return () => window.cancelAnimationFrame(frame)
  }, [targetValue])

  const dash = circumference - (animatedValue / 100) * circumference

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        className="-rotate-90"
        role="img"
        aria-label={`포트폴리오 분석 점수 ${targetValue}점`}
      >
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#e9eef7" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#2563eb"
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dash}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.22, 1, 0.36, 1)" }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-5xl font-extrabold tracking-tight text-slate-950">{value}</div>
        <div className="text-lg font-bold text-slate-600">/ 100</div>
      </div>
    </div>
  )
}

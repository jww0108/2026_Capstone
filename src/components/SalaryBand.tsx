"use client"

import { useEffect, useState } from "react"

function clampPosition(value: number) {
  if (!Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, value))
}

export function SalaryBand({
  lowPosition,
  medianPosition,
  highPosition,
  lowValue,
  medianValue,
  highValue,
  ticks,
}: {
  lowPosition: number
  medianPosition: number
  highPosition: number
  lowValue: string
  medianValue: string
  highValue: string
  ticks: number[]
}) {
  const low = clampPosition(lowPosition)
  const median = clampPosition(medianPosition)
  const high = clampPosition(highPosition)
  const [active, setActive] = useState(false)

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setActive(true))
    return () => window.cancelAnimationFrame(frame)
  }, [])

  return (
    <div className="mt-7 px-3">
      <div className="relative h-[112px]">
        <div className="absolute left-0 right-0 top-[70px] h-4 rounded-full bg-slate-200" />
        <div
          className="salary-band-fill absolute top-[70px] h-4 rounded-full bg-gradient-to-r from-blue-300 via-blue-600 to-emerald-500 transition-[left,width,transform,opacity] duration-700 ease-out"
          style={{
            left: `${active ? low : median}%`,
            width: `${active ? Math.max(0, high - low) : 0}%`,
            transform: active ? "scaleY(1)" : "scaleY(0.25)",
            transformOrigin: "center bottom",
            opacity: active ? 1 : 0.35,
          }}
        />
        <SalaryMarker position={low} label="하위 25%" value={lowValue} tone="slate" active={active} />
        <SalaryMarker position={median} label="중앙값" value={medianValue} tone="blue" center active={active} />
        <SalaryMarker position={high} label="상위 25%" value={highValue} tone="slate" active={active} />
      </div>

      <div className="flex justify-between text-center text-[14px] font-black text-slate-500">
        {ticks.map((tick) => (
          <span key={tick}>{tick.toLocaleString()}만원</span>
        ))}
      </div>
    </div>
  )
}

function SalaryMarker({
  position,
  label,
  value,
  tone,
  center = false,
  active,
}: {
  position: number
  label: string
  value: string
  tone: "blue" | "slate"
  center?: boolean
  active: boolean
}) {
  const safePosition = clampPosition(position)
  const visiblePosition = active ? safePosition : 50
  const textColor = tone === "blue" ? "text-blue-600" : "text-slate-800"
  const bgColor = tone === "blue" ? "bg-blue-50" : "bg-slate-100"
  const borderColor = tone === "blue" ? "border-blue-600" : "border-slate-300"
  const edgeClass = safePosition <= 6 ? "translate-x-0" : safePosition >= 94 ? "-translate-x-full" : "-translate-x-1/2"

  return (
    <div
      className={`salary-band-marker absolute top-0 w-max text-center transition-[left,opacity,transform] duration-700 ease-out ${edgeClass}`}
      style={{ left: `${visiblePosition}%`, opacity: active ? 1 : 0.2 }}
    >
      <div className={`inline-flex whitespace-nowrap rounded-full px-3 py-1 text-[13px] font-black ${bgColor} ${textColor}`}>
        {label}
      </div>
      <p className={`mt-1 whitespace-nowrap text-[14px] font-black ${textColor}`}>{value}</p>
      {center ? (
        <>
          <div className="mx-auto mt-2 h-5 w-5 rounded-full border-[5px] border-blue-600 bg-white" />
          <div className={`mx-auto -mt-px h-[21px] w-0 border-l-2 ${borderColor}`} />
        </>
      ) : (
        <div className={`mx-auto mt-2 h-[32px] w-0 border-l-2 ${borderColor}`} />
      )}
    </div>
  )
}

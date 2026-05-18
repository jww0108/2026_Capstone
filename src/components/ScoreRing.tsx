export function ScoreRing({ value = 70.8, size = 178 }: { value?: number; size?: number }) {
  const stroke = 14
  const radius = (size - stroke) / 2
  const c = 2 * Math.PI * radius
  const dash = c - (value / 100) * c
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={radius} stroke="#e9eef7" strokeWidth={stroke} fill="none" />
        <circle cx={size/2} cy={size/2} r={radius} stroke="#2563eb" strokeWidth={stroke} fill="none" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={dash} />
      </svg>
      <div className="absolute text-center">
        <div className="text-5xl font-extrabold tracking-tight text-slate-950">{value}</div>
        <div className="text-lg font-bold text-slate-600">/ 100</div>
      </div>
    </div>
  )
}

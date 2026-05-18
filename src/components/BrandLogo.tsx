import Image from "next/image"
import Link from "next/link"

export function BrandLogo({ variant = "service" }: { variant?: "main" | "service" }) {
  const isMain = variant === "main"
  const src = isMain ? "/images/Git2Value.png" : "/images/Git2Value_logo.png"
  const width = isMain ? 66 : 45
  const height = isMain ? 58 : 39

  return (
    <Link href="/" className="flex items-center gap-3 text-slate-950 transition hover:opacity-90">
      <Image src={src} alt="Git2Value logo" width={width} height={height} priority className="h-auto shrink-0" />
      <span className={`${isMain ? "text-[34px]" : "text-3xl"} font-black tracking-[-0.04em]`}>Git2Value</span>
    </Link>
  )
}

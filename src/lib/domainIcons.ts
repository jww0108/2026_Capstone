import {
  AlertCircle,
  Brain,
  CloudCog,
  Code2,
  Database,
  Gamepad2,
  GitCompare,
  Layers,
  Monitor,
  Server,
  ShieldCheck,
  Wrench,
  type LucideIcon,
} from "lucide-react"

const EXACT_DOMAIN_ICONS: Record<string, LucideIcon> = {
  "게임 개발": Gamepad2,
  "ML/AI": Brain,
  "웹 프론트엔드": Monitor,
  "서버/백엔드": Server,
  "DevOps/인프라": CloudCog,
  "빅데이터 엔지니어": Database,
  "도구 개발": Wrench,
}

const KEYWORD_DOMAIN_ICONS: Array<{ keywords: string[]; icon: LucideIcon }> = [
  { keywords: ["게임"], icon: Gamepad2 },
  { keywords: ["프론트"], icon: Monitor },
  { keywords: ["백엔드", "서버"], icon: Server },
  { keywords: ["ML", "AI"], icon: Brain },
  { keywords: ["DevOps", "인프라"], icon: CloudCog },
  { keywords: ["빅데이터", "데이터"], icon: Database },
  { keywords: ["도구"], icon: Wrench },
]

function normalizeDomain(domain: string): string {
  return domain.trim()
}

export function getDomainIcon(domain: string): LucideIcon {
  const normalized = normalizeDomain(domain)
  if (!normalized || normalized === "—") {
    return Layers
  }

  const exact = EXACT_DOMAIN_ICONS[normalized]
  if (exact) {
    return exact
  }

  for (const { keywords, icon } of KEYWORD_DOMAIN_ICONS) {
    if (keywords.some((keyword) => normalized.includes(keyword))) {
      return icon
    }
  }

  return Layers
}

export function getTechMatchNoteIcon(note: { label: string; type: string }): LucideIcon {
  if (note.type === "주요 도메인" || note.type === "감지 도메인") {
    return getDomainIcon(note.label)
  }
  if (note.type === "보유 기술") {
    return Code2
  }
  if (note.type === "보완 권장") {
    return AlertCircle
  }
  return ShieldCheck
}

export function getDomainMatchStatIcon(): LucideIcon {
  return GitCompare
}

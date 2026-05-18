import type { ComponentType } from "react"
import { ClipboardList, FileText, Github, Link as LinkIcon, Search } from "lucide-react"

export type LandingResultCard = {
  title: string
  desc: string
  image: string
  tone: "emerald" | "purple" | "orange"
}

export const landingResultCards: LandingResultCard[] = [
  {
    title: "포트폴리오 진단",
    desc: "강점과 개선점을 진단하고 상세 리포트를 제공합니다.",
    image: "/images/module-portfolio.png",
    tone: "emerald",
  },
  {
    title: "직무 매칭",
    desc: "보유 스킬과 경험을 기반으로 최적의 직무를 추천합니다.",
    image: "/images/module-jobs.png",
    tone: "purple",
  },
  {
    title: "시장 연봉 밴드",
    desc: "직무 및 경력에 맞는 시장 연봉 밴드를 분석합니다.",
    image: "/images/module-salary.png",
    tone: "orange",
  },
]

export const landingProcessItems: Array<{
  title: string
  desc: string
  Icon: ComponentType<{ className?: string }>
}> = [
  { title: "1. 정보 입력", desc: "GitHub ID와 대표 레포,\n경력을 입력합니다.", Icon: ClipboardList },
  { title: "2. 분석 진행", desc: "AI가 포트폴리오를 분석하고\n데이터를 수집합니다.", Icon: Search },
  { title: "3. 결과 리포트", desc: "진단, 매칭, 연봉 정보를\n한눈에 확인하세요.", Icon: FileText },
]

export const landingGuideRows = [
  { icon: Github, lines: ["GitHub ID를", "입력하세요"] },
  { icon: LinkIcon, lines: ["레포는 최대", "3개까지"] },
  { icon: ClipboardList, lines: ["신입 기준으로", "시작 가능"] },
]

export const loadingSteps = [
  { title: "GitHub 레포지토리 정보 수집", description: "GitHub API를 통해 레포지토리 기본 정보를 가져오는 중입니다." },
  { title: "README 및 파일 구조 분석", description: "README 내용과 프로젝트 파일 구조를 분석하고 있습니다." },
  { title: "커밋 및 활동 분석", description: "커밋 히스토리와 개발 활동 패턴을 분석하고 있습니다." },
  { title: "포트폴리오 진단 생성", description: "수집된 데이터를 종합하여 포트폴리오를 진단하고 있습니다." },
  { title: "FAISS 기반 직무 매칭", description: "유사한 채용공고를 검색하여 직무를 매칭하고 있습니다." },
  { title: "시장 연봉 밴드 계산", description: "매칭된 직무의 시장 연봉 데이터를 분석하고 있습니다." },
]

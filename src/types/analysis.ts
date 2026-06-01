export type Tone = "blue" | "green" | "orange" | "red" | "gray" | "purple"

export type ReadmeLlmScores = {
  purpose: number
  tech: number
  setup: number
  visual: number
  overall: number
}

export type LanguageBreakdownEntry = {
  name: string
  percent: number
  tier: "main" | "sub" | "trivial"
}

export type JobMatch = {
  rank: number
  company: string
  title: string
  score: string
  exp: string
  domain: string
  domainBoosted?: boolean
  similarity?: string
  category?: string
  postingText?: string
}

export type DomainJobPickUI = {
  company: string
  position: string
  category: string
  similarity: string
  postingText: string
  expLabel: string
}

export type MultiDomainPicksUI = {
  domains: string[]
  picksByDomain: Record<string, DomainJobPickUI[]>
}

export type EvaluationStatus =
  | "양호"
  | "보통"
  | "개선 필요"
  | "필수 미흡"
  | "없음"
  | "성장 신호"
  | "확인 필요"
  | "불규칙"

export type EvaluationItem = {
  title: string
  desc: string
  status: EvaluationStatus
  tone: "ok" | "warn" | "bad" | "info"
  action?: string | null
  llmScores?: ReadmeLlmScores
  llmSuggestions?: string[]
  llmUsed?: boolean
}

export type RepoScore = {
  total: number
  activity: number
  management: number
  consistency: number
}

export type ScoreDetailItemUI = {
  key: string
  label: string
  score: number
  maxScore: number
  potentialGain?: number
  explanation?: string
  improvementHint?: string
}

export type ScoreAxisUI = {
  key: string
  label: string
  score: number
  maxScore: number
  potentialGain?: number
  mode?: "team" | "personal"
  items: ScoreDetailItemUI[]
}

export type ScoreDetailUI = {
  totalScore: number
  maxScore: number
  potentialGainTotal?: number
  scoreModel?: string
  axes: ScoreAxisUI[]
}

export type RepoAnalysis = {
  name: string
  type: string
  repoKind: "personal" | "team"
  displayTypeLabel?: string
  people: string
  period?: string
  techStack: string[]
  isFork: boolean
  commitsTotal: number
  commitsUser: string
  contributionRatioPercent?: number
  contributionRatioLabel?: string
  contributionRole?: string | null
  hasTeamExperience?: boolean
  isDominanceOverride?: boolean
  locUser?: string
  activeWeeks: string
  repoActiveWeeks?: string
  weeklyCommits?: string
  projectSummary: string
  detectedDomains?: string[]
  languageBreakdown?: LanguageBreakdownEntry[]
  evaluations: EvaluationItem[]
  teamChecks: EvaluationItem[]
  collaborationSignals?: string[]
  overallOpinion?: string
  score?: RepoScore
  qualityMode?: "team" | "personal"
  scoreDetail?: ScoreDetailUI
}

export type AnalysisRequest = {
  github_username: string
  repos: string[]
  applicant_years: number
}

export type AnalysisResult = {
  applicant: {
    githubId: string
    career: string
    repoCount: number
    techStack: string[]
    domain: string
    repoType: string
  }
  score: RepoScore
  scoreDetail?: ScoreDetailUI
  repos: RepoAnalysis[]
  jobs: JobMatch[]
  jobSummary: {
    totalPostings: string
    recommendedPostings: string
    averageScore: string
    domainMatchRatio: string
  }
  techMatchNotes: Array<{
    label: string
    type: string
    note: string
  }>
  techLearningSuggestions?: string[]
  salary: {
    role: string
    careerRange: string
    source: string
    median: string
    low: string
    high: string
    note?: string
    rangeDescription?: string
    platforms: Array<{
      name: string
      logo: string
      median: string
      range: string
      count: string
    }>
    relatedJobs: Array<[string, string, string, string]>
  }
  level: {
    grade: string
    description: string
  }
  summary: {
    positioning: string
    strengths: string[]
    quickWins: string[]
  }
  summaryText?: string
  detectedDomains?: string[]
  isMultiDomain?: boolean
  multiDomainPicks?: MultiDomainPicksUI
  companyTypes?: string[]
  jumpitCategory?: string
  meta?: {
    version: string
    llmAvailable: boolean
    analysisTimeSeconds: number
    reposAnalyzed: number
  }
  scoreMeta?: {
    method: string
    breakdownNote: string
  }
  jobMatchingMeta?: {
    rerankNote?: string
  }
  domainConsistent?: boolean
  warnings?: {
    domainMismatch?: string
    domainCheck?: string
  }
}

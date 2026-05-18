export type Tone = "blue" | "green" | "orange" | "red" | "gray" | "purple"

export type JobMatch = {
  rank: number
  company: string
  title: string
  score: string
  exp: string
  domain: string
}

export type EvaluationStatus = "양호" | "보통" | "개선 필요" | "필수 미흡"

export type EvaluationItem = {
  title: string
  desc: string
  status: EvaluationStatus
  tone: "ok" | "warn" | "bad" | "info"
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
  score: {
    total: number
    activity: number
    management: number
    consistency: number
  }
  repo: {
    name: string
    type: string
    people: string
    period: string
    techStack: string[]
    isFork: boolean
    commitsTotal: number
    commitsUser: string
    locUser: string
    activeWeeks: string
    weeklyCommits: string
    projectSummary: string
    evaluations: EvaluationItem[]
    teamChecks: EvaluationItem[]
    collaborationSignals: string[]
    overallOpinion: string
  }
  quickWins: Array<{
    title: string
    desc: string
    priority: string
  }>
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
  matchDistribution: Array<{
    label: string
    count: string
  }>
  salary: {
    role: string
    careerRange: string
    source: string
    median: string
    low: string
    high: string
    platforms: Array<{
      name: string
      logo: string
      median: string
      range: string
      count: string
    }>
    relatedJobs: Array<[string, string, string, string]>
    companySizes: Array<[string, string, string, string]>
  }
}

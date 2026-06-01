export type AnalyzeRequest = {
  github_username: string
  repos: string[]
  applicant_years?: number
}

export type ReadmeLlmScores = {
  purpose: number
  tech: number
  setup: number
  visual: number
  overall: number
}

export type DiagnosisItem = {
  status: string
  detail: string
  action: string | null
  llm_used?: boolean
  llm_scores?: ReadmeLlmScores
  llm_suggestions?: string[]
}

export type ScoreBreakdown = {
  contribution: number
  quality: number
  consistency: number
  quality_mode?: "team" | "personal"
}

export type ScoreDetailItem = {
  key: string
  label: string
  score: number
  max_score: number
  raw_value?: Record<string, unknown>
  explanation?: string
  improvement_hint?: string
  potential_gain?: number
}

export type ScoreAxis = {
  key: string
  label: string
  score: number
  max_score: number
  items: ScoreDetailItem[]
  potential_gain?: number
  mode?: "team" | "personal"
}

export type ScoreDetail = {
  total_score: number
  max_score: number
  axes: ScoreAxis[]
  potential_gain_total?: number
  score_model?: string
}

export type LanguageCategory = {
  main: Array<[string, number]>
  sub: Array<[string, number]>
  trivial: Array<[string, number]>
}

export type PerRepo = {
  repo_name: string
  repo_type: "personal" | "team"
  has_team_experience?: boolean
  distinct_author_count: number
  repo_author_names: string[]
  is_fork: boolean
  fork_penalty: number | null
  dominance_ratio: number | null
  is_dominance_override: boolean
  repo_total_score: number
  score_breakdown: ScoreBreakdown
  score_detail: ScoreDetail
  target_commit_count: number
  total_repo_commits: number
  target_commit_ratio: number
  target_commit_ratio_census?: number | null
  contribution_role?: string | null
  active_weeks: number
  repo_active_weeks: number
  detected_domains: string[]
  frameworks: string[]
  language_category: LanguageCategory
  diagnosis: {
    core_items: Record<string, DiagnosisItem>
    extra_items: Record<string, DiagnosisItem>
  }
}

export type EligibleMatch = {
  rank: number
  position: string
  company_name: string
  category: string
  similarity: number
  effective_score: number
  domain_boosted: boolean
  similarity_label: string
  experience_warning: string | null
}

export type JobPostingMeta = {
  id: number
  job_id: string | number
  company_name: string
  position: string
  category: string
  text: string
}

export type ExperienceRequirement = {
  min_years: number
  is_junior_friendly: boolean
  raw_label: string | null
  requirement_type: string
}

export type DomainJobPick = {
  meta: JobPostingMeta
  similarity: number
  category: string
  experience_requirement: ExperienceRequirement
}

export type MultiDomainPicks = {
  is_multi_domain: boolean
  domain_picks: Record<string, DomainJobPick[]>
  raw_top5: DomainJobPick[]
}

export type JobMatching = {
  primary_domain: string
  detected_domains: string[]
  rerank_note?: string | null
  is_multi_domain: boolean
  eligible_matches: EligibleMatch[]
  domain_mismatch?: {
    type: string
    message: string
  } | null
  domain_check?: {
    consistent: boolean
    warning: string | null
    suggested_category?: string | null
  }
  multi_domain_picks?: MultiDomainPicks | null
  jumpit_category?: string
  company_types?: string[]
}

export type SalaryBand = {
  matched_category: string
  experience_level: string
  salary_range: {
    jumpit_median: number
    wanted_median: number
    combined_range: string
  }
  realistic_range: {
    median: number
    p25_estimate: number
    p75_estimate: number
    description: string
  }
  source?: string
  note?: string
  reference_categories: Array<
    | {
        category: string
        combined_range: string
      }
    | string
  >
  alt_category_band?: {
    category: string
    realistic_range: {
      median: number
      p25_estimate: number
      p75_estimate: number
      description: string
    }
  }
}

export type TechAnalysis = {
  matched_techs: string[]
  missing_techs: string[]
  applicant_techs?: string[]
  learning_suggestions: string[]
  company_types: string[]
}

export type AnalyzeResponse = {
  status: "success" | "error"
  error: string | null
  github_score?: {
    total: number
    method: string
    breakdown: ScoreBreakdown
    breakdown_note: string
    axes: ScoreAxis[]
    score_detail: ScoreDetail
  }
  per_repo?: PerRepo[]
  level?: {
    grade: string
    description: string
    tier_label?: string
    tier_context?: string
    primary_domain_tier?: {
      domain: string
      grade: string
      label: string
    }
    caveat?: string
  }
  summary?: {
    text: string
    positioning?: string
    highlights?: string[]
    strengths: string[]
    quick_wins: string[]
  }
  job_matching?: JobMatching
  salary_band?: SalaryBand
  tech_analysis?: TechAnalysis
  meta?: {
    version: string
    llm_available: boolean
    analysis_time_seconds: number
    repos_analyzed: number
    applicant_years: number
  }
}

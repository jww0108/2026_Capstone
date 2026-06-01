import type {
  AnalyzeResponse,
  DiagnosisItem,
  DomainJobPick,
  PerRepo,
  ScoreAxis,
  ScoreBreakdown,
  ScoreDetail,
  ScoreDetailItem,
} from "@/types/api"
import type {
  AnalysisResult,
  DomainJobPickUI,
  EvaluationItem,
  EvaluationStatus,
  JobMatch,
  LanguageBreakdownEntry,
  MultiDomainPicksUI,
  RepoAnalysis,
  RepoScore,
  ScoreAxisUI,
  ScoreDetailItemUI,
  ScoreDetailUI,
} from "@/types/analysis"
import { formatMoneyRangeWon, formatMoneyWon } from "@/lib/utils"

const CORE_ITEM_LABELS: Record<string, string> = {
  readme_quality: "README 품질",
  project_structure: "프로젝트 구조",
  commit_quality: "커밋 메시지",
}

const EXTRA_ITEM_LABELS: Record<string, string> = {
  test_coverage: "테스트",
  cicd: "CI/CD",
  deployment: "배포",
  commit_pattern: "커밋 리듬",
  growth_signal: "성장 신호",
}

function resolvePrimaryDomain(response: AnalyzeResponse): string | undefined {
  return response.job_matching?.primary_domain ?? undefined
}

function resolveDetectedDomains(response: AnalyzeResponse): string[] {
  return response.job_matching?.detected_domains ?? []
}

function resolveDomainMismatchMessage(response: AnalyzeResponse): string | undefined {
  return response.job_matching?.domain_mismatch?.message ?? undefined
}

function resolveMultiDomainPicks(response: AnalyzeResponse) {
  return response.job_matching?.multi_domain_picks ?? undefined
}

function mapScoreBreakdown(breakdown: ScoreBreakdown, total?: number): RepoScore {
  return {
    total: total ?? breakdown.contribution + breakdown.quality + breakdown.consistency,
    activity: breakdown.contribution,
    management: breakdown.quality,
    consistency: breakdown.consistency,
  }
}

type DiagnosisItemContext = {
  repoType: PerRepo["repo_type"]
  itemKind: "core" | "extra"
}

function mapDiagnosisStatus(
  status: string,
  context?: DiagnosisItemContext
): { uiStatus: EvaluationStatus; tone: EvaluationItem["tone"] } {
  if (status === "양호" || status === "규칙적") {
    return { uiStatus: "양호", tone: "ok" }
  }
  if (status === "보통") {
    return { uiStatus: "보통", tone: "info" }
  }
  if (status === "성장 신호") {
    return { uiStatus: "성장 신호", tone: "ok" }
  }
  if (status === "확인 필요") {
    return { uiStatus: "확인 필요", tone: "warn" }
  }
  if (status === "불규칙") {
    return { uiStatus: "불규칙", tone: "warn" }
  }
  if (status === "개선 필요" || status === "미흡") {
    return { uiStatus: "개선 필요", tone: "warn" }
  }
  if (status === "없음") {
    return { uiStatus: "없음", tone: "info" }
  }
  if (status === "필수 미흡") {
    return { uiStatus: "필수 미흡", tone: "bad" }
  }

  if (context?.repoType === "personal" && context.itemKind === "extra") {
    return { uiStatus: "없음", tone: "info" }
  }

  return { uiStatus: "보통", tone: "info" }
}

function mapDiagnosisItem(
  title: string,
  item: DiagnosisItem,
  context?: DiagnosisItemContext
): EvaluationItem {
  const { uiStatus, tone } = mapDiagnosisStatus(item.status, context)
  return {
    title,
    desc: item.detail,
    status: uiStatus,
    tone,
    action: item.action,
    llmScores: item.llm_scores,
    llmSuggestions: item.llm_suggestions,
    llmUsed: item.llm_used,
  }
}

function mapRepoType(repoType: string): string {
  if (repoType === "personal") return "개인 레포지토리"
  if (repoType === "team") return "팀 레포지토리"
  return repoType
}

function mapScoreDetailItem(item: ScoreDetailItem): ScoreDetailItemUI {
  return {
    key: item.key,
    label: item.label,
    score: item.score,
    maxScore: item.max_score,
    potentialGain: item.potential_gain,
    explanation: item.explanation,
    improvementHint: item.improvement_hint,
  }
}

function mapScoreAxis(axis: ScoreAxis): ScoreAxisUI {
  return {
    key: axis.key,
    label: axis.label,
    score: axis.score,
    maxScore: axis.max_score,
    potentialGain: axis.potential_gain,
    mode: axis.mode,
    items: axis.items.map(mapScoreDetailItem),
  }
}

function mapScoreDetail(detail?: ScoreDetail): ScoreDetailUI | undefined {
  if (!detail) return undefined
  return {
    totalScore: detail.total_score,
    maxScore: detail.max_score,
    potentialGainTotal: detail.potential_gain_total,
    scoreModel: detail.score_model,
    axes: detail.axes.map(mapScoreAxis),
  }
}

function buildLanguageBreakdown(repo: PerRepo): LanguageBreakdownEntry[] {
  const entries: LanguageBreakdownEntry[] = []

  for (const [name, percent] of repo.language_category.main) {
    entries.push({ name, percent, tier: "main" })
  }
  for (const [name, percent] of repo.language_category.sub) {
    if (percent > 0) entries.push({ name, percent, tier: "sub" })
  }
  for (const [name, percent] of repo.language_category.trivial) {
    if (percent > 0) entries.push({ name, percent, tier: "trivial" })
  }

  return entries
}

function extractLanguages(repo: PerRepo): string[] {
  const langNames = buildLanguageBreakdown(repo).map((entry) => entry.name)
  return Array.from(new Set([...repo.frameworks, ...langNames]))
}

function parseWeeklyCommits(extraItems: PerRepo["diagnosis"]["extra_items"]): string | undefined {
  const detail = extraItems.commit_pattern?.detail
  if (!detail) return undefined
  const match = detail.match(/약\s*([\d.]+)회/)
  return match ? `${match[1]}회` : undefined
}

function buildCollaborationSignals(repo: PerRepo): string[] {
  const signals: string[] = []

  if (repo.repo_author_names.length > 0) {
    signals.push(`참여 작성자: ${repo.repo_author_names.join(", ")}`)
  }

  if (repo.dominance_ratio != null) {
    const pct = repo.dominance_ratio * 100
    signals.push(`기여 커밋 비율 약 ${pct.toFixed(1)}%`)
  }

  if (repo.is_dominance_override) {
    signals.push("팀 내 상위 기여자로 감지되었습니다.")
  }

  if (repo.repo_type === "personal" && repo.distinct_author_count === 1) {
    signals.push("개인 프로젝트로 전체 구현 범위가 명확합니다.")
  }

  return signals
}

function buildProjectSummary(repo: PerRepo): string {
  const typeLabel = repo.repo_type === "personal" ? "개인" : "팀"
  const stack = extractLanguages(repo).slice(0, 3).join(", ") || "기술 스택 미확인"
  const domain = repo.detected_domains[0] ?? "도메인 미확인"
  return `${typeLabel} 레포 · ${domain} · ${stack}`
}

function resolveTeamExperience(repo: PerRepo): boolean {
  return repo.has_team_experience ?? repo.distinct_author_count >= 2
}

function resolveContributionRatio(repo: PerRepo): number | null {
  return repo.target_commit_ratio_census ?? repo.target_commit_ratio ?? null
}

function inferContributionRole(repo: PerRepo, ratio: number | null): string | null {
  if (repo.contribution_role) return repo.contribution_role
  if (ratio == null) return null
  if (ratio >= 0.5) return "주도 기여"
  const threshold = repo.distinct_author_count > 0 ? 1 / repo.distinct_author_count : 1
  if (ratio >= threshold) return "적극 기여"
  return "협업"
}

function buildRepoDisplayTypeLabel(
  repo: PerRepo,
  hasTeamExperience: boolean,
  contributionRole: string | null,
  ratio: number | null
): string {
  const ratioLabel = ratio != null ? `${(ratio * 100).toFixed(1)}%` : "데이터 없음"
  const roleLabel = contributionRole ?? "협업"

  if (repo.is_dominance_override && hasTeamExperience) {
    return `팀 레포로 감지되었지만 지배적 기여로 개인 기준 재판정 · ${repo.distinct_author_count}명 중 ${roleLabel} (${ratioLabel})`
  }

  if (repo.repo_type === "team") {
    return `팀 레포 · ${repo.distinct_author_count}명 중 ${roleLabel} (${ratioLabel})`
  }

  return "개인 레포"
}

function mapPerRepo(repo: PerRepo): RepoAnalysis {
  const coreItems = repo.diagnosis.core_items
  const extraItems = repo.diagnosis.extra_items
  const repoKind = repo.repo_type === "team" ? "team" : "personal"

  const evaluations = Object.entries(coreItems).map(([key, item]) =>
    mapDiagnosisItem(CORE_ITEM_LABELS[key] ?? key, item, {
      repoType: repo.repo_type,
      itemKind: "core",
    })
  )

  const teamChecks = Object.entries(extraItems).map(([key, item]) =>
    mapDiagnosisItem(EXTRA_ITEM_LABELS[key] ?? key, item, {
      repoType: repo.repo_type,
      itemKind: "extra",
    })
  )

  const collaborationSignals = buildCollaborationSignals(repo)
  const languageBreakdown = buildLanguageBreakdown(repo)
  const scoreDetail = mapScoreDetail(repo.score_detail)
  const qualityAxisMode = scoreDetail?.axes.find((axis) => axis.key === "quality")?.mode
  const qualityMode = repo.score_breakdown.quality_mode ?? qualityAxisMode
  const hasTeamExperience = resolveTeamExperience(repo)
  const contributionRatio = resolveContributionRatio(repo)
  const shouldResolveRole = repo.repo_type === "team" || (repo.is_dominance_override && hasTeamExperience)
  const contributionRole = shouldResolveRole
    ? inferContributionRole(repo, contributionRatio)
    : (repo.contribution_role ?? null)
  const displayTypeLabel = buildRepoDisplayTypeLabel(
    repo,
    hasTeamExperience,
    contributionRole,
    contributionRatio
  )

  return {
    name: repo.repo_name,
    type: mapRepoType(repo.repo_type),
    repoKind,
    displayTypeLabel,
    people: `${repo.distinct_author_count}명`,
    techStack: extractLanguages(repo),
    isFork: repo.is_fork,
    commitsTotal: repo.total_repo_commits,
    commitsUser: `${repo.target_commit_count}개 (${(repo.target_commit_ratio * 100).toFixed(1)}%)`,
    contributionRatioPercent: contributionRatio != null ? contributionRatio * 100 : undefined,
    contributionRatioLabel:
      contributionRatio != null ? `${(contributionRatio * 100).toFixed(1)}%` : undefined,
    contributionRole,
    hasTeamExperience,
    isDominanceOverride: repo.is_dominance_override,
    activeWeeks: `${repo.active_weeks}주`,
    repoActiveWeeks: `${repo.repo_active_weeks}주`,
    weeklyCommits: parseWeeklyCommits(extraItems),
    projectSummary: buildProjectSummary(repo),
    detectedDomains: repo.detected_domains.length > 0 ? repo.detected_domains : undefined,
    languageBreakdown: languageBreakdown.length > 0 ? languageBreakdown : undefined,
    evaluations,
    teamChecks,
    collaborationSignals: collaborationSignals.length > 0 ? collaborationSignals : undefined,
    score: mapScoreBreakdown(repo.score_breakdown, repo.repo_total_score),
    qualityMode,
    scoreDetail,
  }
}

function buildPostingTextLookup(response: AnalyzeResponse): Map<string, string> {
  const lookup = new Map<string, string>()
  const rawPicks = resolveMultiDomainPicks(response)
  const rawTop5 = rawPicks?.raw_top5 ?? []

  for (const pick of rawTop5) {
    const key = `${pick.meta.company_name}::${pick.meta.position}`
    if (pick.meta.text) lookup.set(key, pick.meta.text)
  }

  for (const picks of Object.values(rawPicks?.domain_picks ?? {})) {
    for (const pick of picks) {
      const key = `${pick.meta.company_name}::${pick.meta.position}`
      if (pick.meta.text) lookup.set(key, pick.meta.text)
    }
  }

  return lookup
}

function mapDomainJobPick(pick: DomainJobPick): DomainJobPickUI {
  const exp = pick.experience_requirement
  let expLabel = "경력 미기재"
  if (exp.raw_label) {
    expLabel = exp.raw_label
  } else if (exp.is_junior_friendly) {
    expLabel = exp.min_years === 0 ? "신입 가능" : `경력 ${exp.min_years}년~`
  }

  return {
    company: pick.meta.company_name,
    position: pick.meta.position,
    category: pick.category || pick.meta.category || "—",
    similarity: pick.similarity.toFixed(4),
    postingText: pick.meta.text,
    expLabel,
  }
}

function mapMultiDomainPicks(response: AnalyzeResponse): MultiDomainPicksUI | undefined {
  const picks = resolveMultiDomainPicks(response)
  if (!picks?.domain_picks || Object.keys(picks.domain_picks).length === 0) {
    return undefined
  }

  const domains = Object.keys(picks.domain_picks)
  const picksByDomain: Record<string, DomainJobPickUI[]> = {}

  for (const domain of domains) {
    picksByDomain[domain] = (picks.domain_picks[domain] ?? []).map(mapDomainJobPick)
  }

  return { domains, picksByDomain }
}

function mapJobs(response: AnalyzeResponse): JobMatch[] {
  const matches = response.job_matching?.eligible_matches ?? []
  const postingLookup = buildPostingTextLookup(response)

  return matches.slice(0, 5).map((job) => {
    const key = `${job.company_name}::${job.position}`
    return {
      rank: job.rank,
      company: job.company_name,
      title: job.position,
      score: job.effective_score.toFixed(4),
      exp: job.experience_warning ?? "경력 미기재",
      domain: job.similarity_label || job.category || "—",
      domainBoosted: job.domain_boosted,
      similarity: job.similarity.toFixed(4),
      category: job.category || "—",
      postingText: postingLookup.get(key),
    }
  })
}

function mapJobSummary(response: AnalyzeResponse): AnalysisResult["jobSummary"] {
  const matches = response.job_matching?.eligible_matches ?? []
  const avg =
    matches.length > 0
      ? (matches.reduce((sum, job) => sum + job.effective_score, 0) / matches.length).toFixed(2)
      : "—"

  const domainMatchRatio =
    response.job_matching?.domain_check?.consistent === true
      ? "일치"
      : response.job_matching?.domain_check?.consistent === false
        ? "검토 필요"
        : "—"

  return {
    totalPostings: "3,400건",
    recommendedPostings: matches.length > 0 ? `${matches.length}건` : "—",
    averageScore: avg,
    domainMatchRatio,
  }
}

function mapTechMatchNotes(response: AnalyzeResponse): AnalysisResult["techMatchNotes"] {
  const notes: AnalysisResult["techMatchNotes"] = []
  const tech = response.tech_analysis
  const primary = resolvePrimaryDomain(response)
  const detectedDomains = resolveDetectedDomains(response)
  const matchedTechs = tech?.matched_techs ?? []
  const missingTechs = tech?.missing_techs ?? []

  if (primary) {
    notes.push({ label: primary, type: "주요 도메인", note: "프로젝트 도메인과 연결" })
  }

  for (const domain of detectedDomains) {
    if (domain !== primary) {
      notes.push({ label: domain, type: "감지 도메인", note: "프로젝트에서 추가로 감지됨" })
    }
  }

  for (const matched of matchedTechs) {
    notes.push({ label: matched, type: "보유 기술", note: "채용공고 요구 기술과 겹침" })
  }

  for (const missing of missingTechs) {
    notes.push({ label: missing, type: "보완 권장", note: "공고에서 자주 요구하는 기술" })
  }

  for (const strength of response.summary?.strengths ?? []) {
    notes.push({ label: strength, type: "강점", note: "포트폴리오 분석에서 확인" })
  }

  for (const suggestion of tech?.learning_suggestions ?? []) {
    notes.push({ label: suggestion, type: "학습 제안", note: "기술 분석에서 제안" })
  }

  return notes
}

function mapSalary(response: AnalyzeResponse): AnalysisResult["salary"] {
  const band = response.salary_band
  const primaryDomain = resolvePrimaryDomain(response)

  if (!band) {
    return {
      role: primaryDomain ?? "—",
      careerRange: "—",
      source: "—",
      median: "—",
      low: "—",
      high: "—",
      platforms: [],
      relatedJobs: [],
    }
  }

  const role =
    band.matched_category ||
    primaryDomain ||
    "—"

  const medianRaw = band.realistic_range.median
  const lowRaw = band.realistic_range.p25_estimate
  const highRaw = band.realistic_range.p75_estimate

  const median = formatMoneyWon(medianRaw ?? NaN)
  const low = formatMoneyWon(lowRaw ?? NaN)
  const high = formatMoneyWon(highRaw ?? NaN)

  const platforms = []
  const jumpitMedian = band.salary_range.jumpit_median
  const wantedMedian = band.salary_range.wanted_median
  const combinedRange =
    band.salary_range.combined_range ||
    formatMoneyRangeWon(lowRaw, highRaw)

  if (jumpitMedian) {
    platforms.push({
      name: "점핏",
      logo: "jumpit",
      median: formatMoneyWon(jumpitMedian),
      range: combinedRange,
      count: "—",
    })
  }
  if (wantedMedian) {
    platforms.push({
      name: "원티드",
      logo: "wanted",
      median: formatMoneyWon(wantedMedian),
      range: combinedRange,
      count: "—",
    })
  }

  const mainMedian = medianRaw ?? 0
  const relatedJobs: Array<[string, string, string, string]> = []

  for (const ref of band.reference_categories ?? []) {
    if (typeof ref === "string") {
      relatedJobs.push([ref, "—", "—", "—"])
      continue
    }
    const rangeParts = ref.combined_range.match(/([\d,]+)만\s*~\s*([\d,]+)만/)
    if (!rangeParts) {
      relatedJobs.push([ref.category, "—", ref.combined_range, "—"])
      continue
    }
    const refMedian =
      (parseInt(rangeParts[1].replace(/,/g, ""), 10) + parseInt(rangeParts[2].replace(/,/g, ""), 10)) /
      2 *
      10_000
    const diffLabel =
      mainMedian > 0
        ? (() => {
            const diffPct = ((refMedian - mainMedian) / mainMedian) * 100
            return diffPct >= 0 ? `+${diffPct.toFixed(1)}% ↑` : `${diffPct.toFixed(1)}% ↓`
          })()
        : "—"
    relatedJobs.push([
      ref.category,
      formatMoneyWon(refMedian),
      ref.combined_range,
      diffLabel,
    ])
  }

  if (band.alt_category_band) {
    const alt = band.alt_category_band
    const diffLabel =
      mainMedian > 0
        ? (() => {
            const diffPct =
              ((alt.realistic_range.median - mainMedian) / mainMedian) * 100
            return diffPct >= 0 ? `+${diffPct.toFixed(1)}% ↑` : `${diffPct.toFixed(1)}% ↓`
          })()
        : "—"
    relatedJobs.push([
      alt.category,
      formatMoneyWon(alt.realistic_range.median),
      formatMoneyRangeWon(alt.realistic_range.p25_estimate, alt.realistic_range.p75_estimate),
      diffLabel,
    ])
  }

  return {
    role,
    careerRange: band.experience_level,
    source: band.source || "—",
    median,
    low,
    high,
    note: band.note,
    rangeDescription: band.realistic_range.description,
    platforms,
    relatedJobs,
  }
}

function buildApplicantMeta(
  response: AnalyzeResponse,
  githubId: string
): AnalysisResult["applicant"] {
  const repos = response.per_repo ?? []
  const personalCount = repos.filter((r) => r.repo_type === "personal").length
  const teamCount = repos.filter((r) => r.repo_type === "team").length
  const years = response.meta?.applicant_years ?? 0

  const techStack = Array.from(
    new Set(repos.flatMap((repo) => extractLanguages(repo)))
  ).slice(0, 8)

  let repoType = "복수 레포 분석"
  if (personalCount > 0 && teamCount === 0) repoType = `개인 ${personalCount}개`
  else if (teamCount > 0 && personalCount === 0) repoType = `팀 ${teamCount}개`
  else if (personalCount > 0 && teamCount > 0) {
    repoType = `개인 ${personalCount}개 · 팀 ${teamCount}개`
  }

  return {
    githubId,
    career: years === 0 ? "신입 0년차" : `${years}년차`,
    repoCount: response.meta?.repos_analyzed ?? repos.length,
    techStack,
    domain: resolvePrimaryDomain(response) ?? "—",
    repoType,
  }
}

export function mapAnalyzeResponse(
  response: AnalyzeResponse,
  context: { githubId: string }
): AnalysisResult {
  const githubScore = response.github_score
  const breakdown = githubScore?.breakdown ?? {
    contribution: 0,
    quality: 0,
    consistency: 0,
  }

  const scoreMeta =
    githubScore?.method && githubScore?.breakdown_note
      ? { method: githubScore.method, breakdownNote: githubScore.breakdown_note }
      : undefined
  const scoreDetail = mapScoreDetail(githubScore?.score_detail)

  const rerankNote = response.job_matching?.rerank_note
  const jobMatchingMeta = rerankNote ? { rerankNote } : undefined

  const domainCheck = response.job_matching?.domain_check
  const domainConsistent =
    domainCheck?.consistent !== undefined ? domainCheck.consistent : undefined

  const meta = response.meta
    ? {
        version: response.meta.version,
        llmAvailable: response.meta.llm_available,
        analysisTimeSeconds: response.meta.analysis_time_seconds,
        reposAnalyzed: response.meta.repos_analyzed,
      }
    : undefined

  return {
    applicant: buildApplicantMeta(response, context.githubId),
    score: mapScoreBreakdown(breakdown, githubScore?.total),
    scoreDetail,
    scoreMeta,
    repos: (response.per_repo ?? []).slice(0, 3).map(mapPerRepo),
    jobs: mapJobs(response),
    jobSummary: mapJobSummary(response),
    jobMatchingMeta,
    techMatchNotes: mapTechMatchNotes(response),
    techLearningSuggestions: response.tech_analysis?.learning_suggestions,
    salary: mapSalary(response),
    domainConsistent,
    summaryText: response.summary?.text,
    detectedDomains: resolveDetectedDomains(response),
    isMultiDomain: response.job_matching?.is_multi_domain,
    multiDomainPicks: mapMultiDomainPicks(response),
    companyTypes: response.job_matching?.company_types ?? response.tech_analysis?.company_types,
    jumpitCategory: response.job_matching?.jumpit_category ?? undefined,
    meta,
    level: {
      grade: response.level?.grade ?? "—",
      description: response.level?.description ?? "",
    },
    summary: {
      positioning: response.summary?.positioning ?? "",
      strengths: response.summary?.strengths ?? [],
      quickWins: response.summary?.quick_wins ?? [],
    },
    warnings: {
      domainMismatch: resolveDomainMismatchMessage(response),
      domainCheck: response.job_matching?.domain_check?.warning ?? undefined,
    },
  }
}

import Image from "next/image"
import Link from "next/link"
import { CheckCircle2, FileText, Users } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Bar, Chip, FooterActions, StatRow } from "@/components/Common"
import { Button } from "@/components/ui/button"
import { ScoreRing } from "@/components/ScoreRing"
import type {
  EvaluationItem,
  LanguageBreakdownEntry,
  ReadmeLlmScores,
  RepoAnalysis,
  RepoScore,
  Tone,
} from "@/types/analysis"

export function RepoAnalysisPanel({
  repo,
  index,
  total,
  fallbackScore,
}: {
  repo: RepoAnalysis
  index: number
  total: number
  fallbackScore: RepoScore
}) {
  const score = repo.score ?? fallbackScore
  const repoTypeValue =
    repo.isDominanceOverride && repo.hasTeamExperience && repo.repoKind === "personal"
      ? `${repo.type} (팀 레포에서 개인 기준으로 재판정)`
      : repo.type

  return (
    <>
      <Card className="min-h-[205px] p-5">
        <div className="grid grid-cols-[1.08fr_230px_1fr] items-center gap-6">
          <div className="flex items-center gap-5">
            <Image
              src="/images/fileImg.png"
              alt="repository"
              width={72}
              height={62}
              className="h-[66px] w-[78px] shrink-0 object-contain"
            />
            <div className="min-w-0">
              <Chip>포트폴리오 {index + 1} / {total}</Chip>
              <h2 className="mt-3 text-[32px] font-black leading-tight tracking-[-0.045em] text-slate-950">
                {repo.name}
              </h2>
              <p className="mt-2 text-lg font-extrabold text-slate-700">
                {repo.projectSummary}
              </p>
              {repo.displayTypeLabel && (
                <p className="mt-2 text-[14px] font-black text-slate-600">
                  {repo.displayTypeLabel}
                </p>
              )}
              <div className="mt-2 flex flex-wrap gap-2">
                {repo.hasTeamExperience && (
                  <Chip tone="green">팀 경험 있음</Chip>
                )}
                {repo.isDominanceOverride && (
                  <Chip tone="purple">지배적 기여</Chip>
                )}
                {repo.contributionRole && (
                  <Chip tone="blue">{repo.contributionRole}</Chip>
                )}
                {repo.contributionRatioLabel && (
                  <Chip tone="gray">{repo.contributionRatioLabel}</Chip>
                )}
              </div>
              {repo.detectedDomains && repo.detectedDomains.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {repo.detectedDomains.map((domain) => (
                    <Chip key={domain} tone="blue">
                      {domain}
                    </Chip>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="border-x px-7 text-center">
            <ScoreRing value={score.total} size={150} />
          </div>

          <div className="grid grid-cols-2 gap-x-8 gap-y-5">
            <Meta label="레포 유형" value={repoTypeValue} image="/images/person.png" />
            <Meta label="작성자 수" value={repo.people} image="/images/person.png" />
            <Meta label="포크 여부" value={repo.isFork ? "포크" : "포크 아님"} image="/images/fork.png" />
            <div>
              <p className="text-sm font-black text-slate-500">주요 기술 스택</p>
              <div className="mt-2 flex content-start flex-wrap gap-2">
                {repo.techStack.map((t) => (
                  <Chip key={t} tone="gray">
                    {t}
                  </Chip>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div className="mt-4 grid grid-cols-[1fr_540px] items-start gap-5">
        <div className="flex flex-col gap-4">
          <Card className="p-5">
            <h2 className="mb-3 flex items-center gap-2 text-xl font-black text-slate-950">
              <CheckCircle2 className="h-6 w-6 text-blue-600" />핵심 진단 항목
            </h2>
            {repo.evaluations.map((item) => (
              <Eval key={item.title} item={item} />
            ))}
          </Card>

          <Card className="p-5">
            <h2 className="mb-1 flex items-center gap-2 text-xl font-black text-slate-950">
              <FileText className="h-6 w-6 text-blue-600" />
              {repo.qualityMode === "team" ? "팀 기준 필수 점검 항목" : "추가 점검 항목"}
            </h2>
            <p className="mb-3 text-[14px] font-bold leading-6 text-slate-600">
              {repo.qualityMode === "team"
                ? "테스트·CI/CD·배포는 팀 기준 점수에 직접 반영됩니다."
                : "테스트·CI/CD·배포는 없어도 불이익 없이, 있으면 가산 요소로 반영됩니다."}
            </p>
            {repo.teamChecks.map((item) => (
              <Eval key={item.title} item={item} />
            ))}
          </Card>

          {repo.scoreDetail && (
            <Card className="p-5">
              <h2 className="mb-2 text-xl font-black text-slate-950">레포 점수 상세 해석</h2>
              {repo.qualityMode && (
                <p className="mb-2 text-[13px] font-bold text-slate-600">
                  운영도 배점 기준: {repo.qualityMode === "team" ? "팀 기준" : "개인 기준"}
                </p>
              )}
              <div className="space-y-2">
                {repo.scoreDetail.axes.map((axis) => (
                  <details key={axis.key} className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2">
                    <summary className="cursor-pointer text-[14px] font-black text-slate-900">
                      {axis.label} · {axis.score.toFixed(1)} / {axis.maxScore}
                    </summary>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-[13px] font-bold text-slate-600">
                      {axis.items.map((item) => (
                        <li key={item.key}>
                          {item.label}: {item.score.toFixed(1)} / {item.maxScore}
                          {item.potentialGain != null ? ` · +${item.potentialGain.toFixed(1)} 가능` : ""}
                        </li>
                      ))}
                    </ul>
                  </details>
                ))}
              </div>
            </Card>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <Card className="p-5">
            <h2 className="mb-3 text-xl font-black text-slate-950">개발 활동 요약</h2>
            <StatRow label="전체 커밋 수" value={`${repo.commitsTotal}개`} />
            <StatRow label="지원자 커밋 수" value={repo.commitsUser} />
            {repo.locUser && <StatRow label="지원자 유효 LOC" value={repo.locUser} />}
            <StatRow label="활성 기간 (지원자)" value={repo.activeWeeks} />
            {repo.repoActiveWeeks && (
              <StatRow label="레포 전체 활성 기간" value={repo.repoActiveWeeks} />
            )}
            {repo.weeklyCommits && (
              <StatRow label="활성 주당 평균 커밋" value={repo.weeklyCommits} />
            )}
          </Card>

          {repo.languageBreakdown && repo.languageBreakdown.length > 0 && (
            <Card className="p-5">
              <h2 className="mb-3 text-xl font-black text-slate-950">언어 구성</h2>
              <LanguageBreakdownTable entries={repo.languageBreakdown} />
            </Card>
          )}

          {repo.collaborationSignals && repo.collaborationSignals.length > 0 && (
            <Card className="border-blue-100 bg-blue-50/60 p-5">
              <h2 className="flex items-center gap-2 text-xl font-black text-blue-700">
                <Users className="h-6 w-6" />협업 신호
              </h2>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-[15px] font-bold leading-6 text-slate-700">
                {repo.collaborationSignals.map((signal) => (
                  <li key={signal}>{signal}</li>
                ))}
              </ul>
            </Card>
          )}

          {repo.overallOpinion && (
            <Card className="border-purple-100 bg-purple-50/50 p-5">
              <h2 className="text-xl font-black text-purple-700">종합 의견</h2>
              <p className="mt-3 text-[15px] font-bold leading-7 text-slate-700">
                {repo.overallOpinion}
              </p>
            </Card>
          )}
        </div>
      </div>

      <FooterActions
        center={
          <Link href="/result">
            <Button variant="secondary" className="w-72 font-black">결과 요약으로 돌아가기</Button>
          </Link>
        }
        right={
          <Link href="/jobs">
            <Button className="w-80 font-black">직무 매칭 보기 →</Button>
          </Link>
        }
      />
    </>
  )
}

function Meta({ label, value, image }: { label: string; value: string; image: string }) {
  return (
    <div className="flex items-start gap-3">
      <Image src={image} alt="" width={45} height={45} className="h-10 w-10 object-contain" />
      <div>
        <p className="text-sm font-black text-slate-500">{label}</p>
        <b className="mt-1 block text-lg font-black text-slate-950">{value}</b>
      </div>
    </div>
  )
}

const TIER_LABELS: Record<LanguageBreakdownEntry["tier"], string> = {
  main: "주요",
  sub: "보조",
  trivial: "기타",
}

function LanguageBreakdownTable({ entries }: { entries: LanguageBreakdownEntry[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <table className="w-full text-[14px] font-bold">
        <thead className="bg-slate-50 text-left text-[13px] font-black text-slate-500">
          <tr className="border-b border-slate-200">
            <th className="px-3 py-2">구분</th>
            <th className="px-3 py-2">언어</th>
            <th className="px-3 py-2 text-right">비율</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={`${entry.tier}-${entry.name}`} className="border-b border-slate-100 last:border-b-0">
              <td className="px-3 py-2 text-slate-500">{TIER_LABELS[entry.tier]}</td>
              <td className="px-3 py-2 font-black text-slate-900">{entry.name}</td>
              <td className="px-3 py-2 text-right text-slate-700">{entry.percent.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Eval({ item }: { item: EvaluationItem }) {
  const toneMap: Record<EvaluationItem["tone"], Tone> = {
    ok: "green",
    warn: "orange",
    bad: "red",
    info: "blue",
  }

  const chipTone: Tone =
    item.status === "없음" ? "gray" : toneMap[item.tone]

  const iconTone = {
    ok: "bg-emerald-500",
    warn: "bg-orange-500",
    bad: "bg-red-500",
    info: "bg-blue-600",
  }[item.tone]

  const marker = item.tone === "ok" ? "✓" : item.tone === "info" ? "i" : "!"
  const hasAction = item.action != null && item.action.trim().length > 0
  const actionText = hasAction ? item.action!.trim() : ""
  const extraSuggestions = (item.llmSuggestions ?? []).filter(
    (s) => s.trim().length > 0 && s.trim() !== actionText
  )

  return (
    <div className="flex items-start gap-4 border-t py-3 first:border-t-0">
      <div className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-black text-white ${iconTone}`}>
        {marker}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <b className="text-lg font-black text-slate-950">{item.title}</b>
          {item.llmUsed && <Chip tone="purple">LLM 보조 분석</Chip>}
        </div>
        <p className="mt-0.5 text-[15px] font-bold leading-6 text-slate-600">{item.desc}</p>
        {hasAction && (
          <p className="mt-1.5 text-[14px] font-bold leading-6 text-slate-500">
            <span className="font-black text-slate-600">개선 제안:</span> {item.action}
          </p>
        )}
        {extraSuggestions.length > 0 && (
          <div className="mt-2">
            <p className="text-[13px] font-black text-slate-600">추가 제안</p>
            <ol className="mt-1 list-decimal space-y-1 pl-5 text-[14px] font-bold leading-6 text-slate-500">
              {extraSuggestions.map((suggestion) => (
                <li key={suggestion}>{suggestion}</li>
              ))}
            </ol>
          </div>
        )}
        {item.llmScores && <ReadmeScoreBars scores={item.llmScores} />}
      </div>
      <Chip tone={chipTone}>{item.status}</Chip>
    </div>
  )
}

const README_SCORE_LABELS: Array<{ key: keyof ReadmeLlmScores; label: string }> = [
  { key: "purpose", label: "목적" },
  { key: "tech", label: "기술" },
  { key: "setup", label: "설치·실행" },
  { key: "visual", label: "시각 자료" },
  { key: "overall", label: "종합" },
]

function ReadmeScoreBars({ scores }: { scores: ReadmeLlmScores }) {
  return (
    <div className="mt-3 space-y-2 rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2.5">
      <p className="text-[13px] font-black text-slate-500">README 세부 점수</p>
      {README_SCORE_LABELS.map(({ key, label }) => (
        <div key={key} className="grid grid-cols-[72px_1fr_36px] items-center gap-2">
          <span className="text-[13px] font-bold text-slate-600">{label}</span>
          <Bar value={(scores[key] / 5) * 100} />
          <span className="text-right text-[13px] font-black text-slate-700">{scores[key]}/5</span>
        </div>
      ))}
    </div>
  )
}

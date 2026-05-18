import type { AnalysisResult } from "@/types/analysis"

// 현재는 시연용 mock 데이터입니다.
// 백엔드 연동 시에는 이 객체 형태와 동일한 응답을 받거나,
// src/lib/analysisResult.ts의 mapper에서 API 응답을 이 형태로 변환하면 됩니다.
export const report: AnalysisResult = {
  applicant: {
    githubId: "tekyung",
    career: "신입 0년차",
    repoCount: 1,
    techStack: ["C#"],
    domain: "게임 개발",
    repoType: "팀 레포 (6명 협업)",
  },
  score: {
    total: 70.8,
    activity: 52.3,
    management: 10.0,
    consistency: 8.5,
  },
  repo: {
    name: "Ttakji_lab-mobile_development_dep",
    type: "팀 레포지토리",
    people: "6명",
    period: "2023.08 ~ 2023.11",
    techStack: ["C#", "Unity", "Firebase", "Git", "GitHub"],
    isFork: false,
    commitsTotal: 199,
    commitsUser: "43개 (21.6%)",
    locUser: "3,842줄",
    activeWeeks: "9주",
    weeklyCommits: "4.8회",
    projectSummary: "팀 레포 · 6명 협업 · Unity · 2023.08 ~ 2023.11",
    evaluations: [
      {
        title: "프로젝트 구조",
        desc: "디렉터리 구성이 .gitignore, 설정 파일들이 적절하게 관리되어 있습니다.",
        status: "양호",
        tone: "ok",
      },
      {
        title: "커밋 메시지",
        desc: "의미 있는 커밋 메시지가 작성되어 프로젝트 흐름을 파악하기 쉽습니다.",
        status: "양호",
        tone: "ok",
      },
      {
        title: "README 품질",
        desc: "프로젝트 목적, 기술스택, 결과물 시각화가 부족합니다.",
        status: "개선 필요",
        tone: "warn",
      },
    ],
    teamChecks: [
      {
        title: "테스트",
        desc: "테스트 코드가 없거나 매우 부족합니다.",
        status: "필수 미흡",
        tone: "bad",
      },
      {
        title: "CI/CD",
        desc: "지속적 통합 및 배포(CI/CD) 설정이 확인되지 않습니다.",
        status: "필수 미흡",
        tone: "bad",
      },
      {
        title: "배포",
        desc: "배포 결과물 또는 실행 가능한 링크가 확인되지 않습니다.",
        status: "필수 미흡",
        tone: "bad",
      },
      {
        title: "커밋 리듬",
        desc: "활성 주당 평균 4.8회로 보통 수준의 꾸준한 커밋이 있습니다.",
        status: "보통",
        tone: "info",
      },
    ],
    collaborationSignals: [
      "전체 6명 중 2번째로 많은 커밋 활동",
      "커밋 비율이 팀 평균보다 높습니다.",
      "주요 기능 단위 커밋이 포함되어 있습니다.",
    ],
    overallOpinion:
      "전반적으로 프로젝트 구조와 커밋 관리는 잘 되어 있지만, 필수 체크 항목 일부(테스트, CI/CD, 배포)의 보강이 필요합니다.",
  },
  quickWins: [
    {
      title: "README 보강",
      desc: "프로젝트 목적, 기술 스택, 스크린샷, 결과물 링크를 추가하면 좋아요.",
      priority: "우선순위 높음",
    },
    {
      title: "테스트 추가",
      desc: "Unity Test Framework로 핵심 기능 테스트를 작성해보세요.",
      priority: "우선순위 중간",
    },
    {
      title: "배포/실행 결과 명시",
      desc: "빌드 파일, itch.io 링크 등 실행 가능한 결과를 보여주세요.",
      priority: "우선순위 보통",
    },
  ],
  jobs: [
    { rank: 1, company: "베이글코드", title: "게임 클라이언트 개발자", score: "0.6539", exp: "경력 미기재", domain: "도메인 일치" },
    { rank: 2, company: "매카로", title: "금융 SW 개발 모집", score: "0.6062", exp: "경력 미기재", domain: "보통" },
    { rank: 3, company: "BC카드", title: "백엔드 개발자 (Node.js)", score: "0.5921", exp: "신입", domain: "부분 일치" },
    { rank: 4, company: "현대카드", title: "소프트웨어 엔지니어 (Java)", score: "0.5734", exp: "경력 미기재", domain: "부분 일치" },
    { rank: 5, company: "뱅크샐러드", title: "프론트엔드 개발자", score: "0.5513", exp: "경력 무관", domain: "낮음" },
  ],
  jobSummary: {
    totalPostings: "1,142건",
    recommendedPostings: "276건",
    averageScore: "0.41",
    domainMatchRatio: "32%",
  },
  techMatchNotes: [
    { label: "C# / Unity", type: "핵심 기술", note: "보유 기술 스택과 직접 연결" },
    { label: "게임 개발", type: "주요 도메인", note: "프로젝트 도메인과 일치" },
    { label: "클라이언트 개발", type: "직무 방향", note: "1순위 추천 직무와 관련" },
    { label: "협업 (Git)", type: "협업 신호", note: "팀 레포와 커밋 활동 기반" },
    { label: "데이터 처리", type: "보조 키워드", note: "일부 공고에서 참고 신호로 활용" },
  ],
  matchDistribution: [
    { label: "높음 (0.70~1.00)", count: "0건 (0%)" },
    { label: "보통 (0.50~0.70)", count: "56건 (20%)" },
    { label: "낮음 (0.30~0.50)", count: "163건 (59%)" },
    { label: "매우 낮음 (0.00~0.30)", count: "57건 (21%)" },
  ],
  salary: {
    role: "게임 클라이언트 개발자",
    careerRange: "신입 ~ 3년",
    source: "점핏, 원티드 채용공고 (2025.05 기준)",
    median: "3,554만원",
    low: "3,021만원",
    high: "4,265만원",
    platforms: [
      { name: "점핏", logo: "jumpit", median: "3,560만원", range: "3,012만 ~ 4,280만원", count: "152건" },
      { name: "원티드", logo: "wanted", median: "3,548만원", range: "3,030만 ~ 4,250만원", count: "124건" },
    ],
    relatedJobs: [
      ["프론트엔드 개발자", "3,357만원", "3,357만 ~ 3,480만원", "-5.5% ↓"],
      ["SW/솔루션 개발자", "3,677만원", "3,677만 ~ 3,724만원", "+3.5% ↑"],
      ["서버/백엔드 개발자", "3,649만원", "3,649만 ~ 3,687만원", "+2.7% ↑"],
      ["게임 서버 개발자", "3,239만원", "3,239만 ~ 3,803만원", "-8.9% ↓"],
      ["데이터 엔지니어", "3,466만원", "3,466만 ~ 3,592만원", "-2.5% ↓"],
    ],
    companySizes: [
      ["스타트업", "1~50명", "3,000만원", "~ 3,600만원"],
      ["중소기업", "50~300명", "3,200만원", "~ 3,900만원"],
      ["중견기업", "300~1000명", "3,500만원", "~ 4,200만원"],
      ["대기업", "1000명 이상", "3,800만원", "~ 4,800만원"],
    ],
  },
}

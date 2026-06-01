import type { AnalysisResult, RepoAnalysis } from "@/types/analysis"

// 현재는 시연용 mock 데이터입니다.
// 백엔드 연동 시에는 이 객체 형태와 동일한 응답을 받거나,
// src/lib/analysisResult.ts의 mapper에서 API 응답을 이 형태로 변환하면 됩니다.

const primaryRepo: RepoAnalysis = {
  name: "Ttakji_lab-mobile_development_dep",
  type: "팀 레포지토리",
  repoKind: "team",
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
  score: {
    total: 70.8,
    activity: 52.3,
    management: 10.0,
    consistency: 8.5,
  },
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
      action: "README에 프로젝트 목적, 기술 스택, 스크린샷을 추가하세요.",
      llmScores: { purpose: 3, tech: 4, setup: 2, visual: 1, overall: 3 },
      llmUsed: true,
      llmSuggestions: [
        "Include screenshots or a demo video of the gameplay.",
        "Add a step-by-step setup guide for Unity and Firebase.",
      ],
    },
  ],
  detectedDomains: ["게임 개발"],
  languageBreakdown: [
    { name: "C#", percent: 82.5, tier: "main" },
    { name: "ShaderLab", percent: 12.0, tier: "sub" },
  ],
  repoActiveWeeks: "10주",
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
}

const secondaryRepo: RepoAnalysis = {
  name: "JuicyMatch-card-game",
  type: "개인 레포지토리",
  repoKind: "personal",
  people: "1명",
  period: "2023.10 ~ 2024.01",
  techStack: ["Java", "Swing", "MySQL", "Git"],
  isFork: false,
  commitsTotal: 84,
  commitsUser: "84개 (100%)",
  locUser: "5,126줄",
  activeWeeks: "7주",
  weeklyCommits: "12.0회",
  projectSummary: "개인 레포 · Java Swing · 카드 매칭 게임 · MySQL 기록 저장",
  score: {
    total: 74.2,
    activity: 55.1,
    management: 11.8,
    consistency: 7.3,
  },
  evaluations: [
    {
      title: "프로젝트 구조",
      desc: "화면, 게임 로직, 데이터 접근 계층이 비교적 명확하게 분리되어 있습니다.",
      status: "양호",
      tone: "ok",
    },
    {
      title: "커밋 메시지",
      desc: "기능 단위 커밋이 확인되지만 일부 메시지는 더 구체화할 여지가 있습니다.",
      status: "보통",
      tone: "info",
    },
    {
      title: "README 품질",
      desc: "게임 목적과 실행 방법은 있으나 주요 화면 흐름과 기술적 개선 설명을 보강하면 좋습니다.",
      status: "개선 필요",
      tone: "warn",
    },
  ],
  teamChecks: [
    {
      title: "테스트",
      desc: "테스트 파일이 감지되지 않았습니다.",
      status: "없음",
      tone: "info",
      action: "핵심 비즈니스 로직부터 단위 테스트를 추가하면 차별화 요소가 됩니다.",
    },
    {
      title: "CI/CD",
      desc: "GitHub Actions 또는 실질적인 Dockerfile 기반 CI/CD가 감지되지 않았습니다.",
      status: "없음",
      tone: "info",
      action: "간단한 lint/test 워크플로우라도 추가해 보세요.",
    },
    {
      title: "배포",
      desc: "배포 관련 설정(docker-compose, Vercel 등)이 감지되지 않았습니다.",
      status: "없음",
      tone: "info",
      action: "Vercel, Netlify, Railway 등 간단한 배포부터 시도해 보세요.",
    },
    {
      title: "커밋 리듬",
      desc: "활성 주당 평균 12.0회로 집중적인 개발 활동이 확인됩니다.",
      status: "양호",
      tone: "ok",
    },
  ],
  collaborationSignals: [
    "개인 프로젝트로 전체 구현 범위가 명확합니다.",
    "게임 로직과 UI 개선 이력이 함께 확인됩니다.",
    "DB 연동 및 설정 파일 분리 경험을 보여줄 수 있습니다.",
  ],
  overallOpinion:
    "개인 프로젝트로서 구현 범위와 개선 방향이 명확합니다. README에 기술적 의사결정과 실행 결과를 더 정리하면 포트폴리오 설득력이 높아집니다.",
}

const thirdRepo: RepoAnalysis = {
  name: "SafePin-disaster-map",
  type: "팀 레포지토리",
  repoKind: "team",
  people: "4명",
  period: "2025.04 ~ 2025.06",
  techStack: ["React", "Spring Boot", "WebSocket", "MySQL", "Kakao Map"],
  isFork: false,
  commitsTotal: 152,
  commitsUser: "38개 (25.0%)",
  locUser: "4,018줄",
  activeWeeks: "6주",
  weeklyCommits: "6.3회",
  projectSummary: "팀 레포 · 실시간 재난 제보 지도 · React/Spring Boot/WebSocket",
  score: {
    total: 72.6,
    activity: 50.9,
    management: 13.2,
    consistency: 8.5,
  },
  evaluations: [
    {
      title: "프로젝트 구조",
      desc: "프론트엔드와 백엔드 역할이 분리되어 있고 주요 도메인별 패키지 구성이 확인됩니다.",
      status: "양호",
      tone: "ok",
    },
    {
      title: "커밋 메시지",
      desc: "기능 브랜치와 PR 단위 작업 흐름을 파악하기 쉽습니다.",
      status: "양호",
      tone: "ok",
    },
    {
      title: "README 품질",
      desc: "서비스 목적과 실행 방법은 있으나 API 흐름과 실시간 처리 구조 설명을 보강하면 좋습니다.",
      status: "개선 필요",
      tone: "warn",
    },
  ],
  teamChecks: [
    {
      title: "테스트",
      desc: "백엔드 서비스 계층과 프론트 주요 컴포넌트 테스트가 부족합니다.",
      status: "필수 미흡",
      tone: "bad",
    },
    {
      title: "CI/CD",
      desc: "GitHub Actions 또는 실질적인 Dockerfile 기반 CI/CD가 감지되지 않았습니다.",
      status: "필수 미흡",
      tone: "bad",
      action: "간단한 lint/test 워크플로우라도 추가해 보세요.",
    },
    {
      title: "배포",
      desc: "배포 관련 설정(docker-compose, Vercel 등)이 감지되지 않았습니다.",
      status: "필수 미흡",
      tone: "bad",
      action: "실행 가능한 배포 링크 또는 데모 환경을 README에 명시하세요.",
    },
    {
      title: "커밋 리듬",
      desc: "활성 주당 평균 6.3회로 팀 프로젝트 기준 안정적인 커밋 흐름이 있습니다.",
      status: "양호",
      tone: "ok",
    },
  ],
  collaborationSignals: [
    "팀 프로젝트에서 기능 단위 브랜치 작업 흐름이 확인됩니다.",
    "지도, 제보, 실시간 알림 등 역할 분담 근거가 있습니다.",
    "API와 WebSocket 연동 경험을 직무 매칭 신호로 활용할 수 있습니다.",
  ],
  overallOpinion:
    "서비스 목적과 기술 스택의 연결성이 좋은 팀 프로젝트입니다. 배포 링크, API 명세, 실시간 처리 흐름을 보강하면 백엔드/풀스택 직무에도 활용도가 높아집니다.",
}

const repos = [primaryRepo, secondaryRepo, thirdRepo]

export const report: AnalysisResult = {
  applicant: {
    githubId: "tekyung",
    career: "신입 0년차",
    repoCount: repos.length,
    techStack: ["C#", "Unity", "Java", "React", "Spring Boot"],
    domain: "게임 개발",
    repoType: "복수 레포 분석",
  },
  score: {
    total: 70.8,
    activity: 52.3,
    management: 10.0,
    consistency: 8.5,
  },
  scoreMeta: {
    method: "대표 프로젝트(최고점) 70% + 전체 평균 30%",
    breakdownNote: "최고 레포 기준",
  },
  repos,
  jobs: [
    { rank: 1, company: "베이글코드", title: "게임 클라이언트 개발자", score: "0.6539", exp: "경력 미기재", domain: "도메인 일치", domainBoosted: true },
    { rank: 2, company: "매카로", title: "금융 SW 개발 모집", score: "0.6062", exp: "경력 미기재", domain: "보통" },
    { rank: 3, company: "BC카드", title: "백엔드 개발자 (Node.js)", score: "0.5921", exp: "신입", domain: "부분 일치" },
    { rank: 4, company: "현대카드", title: "소프트웨어 엔지니어 (Java)", score: "0.5734", exp: "경력 미기재", domain: "부분 일치" },
    { rank: 5, company: "뱅크샐러드", title: "프론트엔드 개발자", score: "0.5513", exp: "경력 무관", domain: "낮음" },
  ],
  jobSummary: {
    totalPostings: "3,400건",
    recommendedPostings: "276건",
    averageScore: "0.41",
    domainMatchRatio: "32%",
  },
  jobMatchingMeta: {
    rerankNote: "도메인 감지: '게임 개발' → 기대 직무와 일치하는 공고에 +0.05 가산 후 유효 점수로 재정렬했습니다.",
  },
  domainConsistent: true,
  techMatchNotes: [
    { label: "C# / Unity", type: "핵심 기술", note: "보유 기술 스택과 직접 연결" },
    { label: "게임 개발", type: "주요 도메인", note: "프로젝트 도메인과 일치" },
    { label: "클라이언트 개발", type: "직무 방향", note: "상위 유사 공고와 관련" },
    { label: "협업 (Git)", type: "협업 신호", note: "팀 레포와 커밋 활동 기반" },
    { label: "데이터 처리", type: "보조 키워드", note: "일부 공고에서 참고 신호로 활용" },
    { label: "문서화", type: "문서 신호", note: "README와 프로젝트 설명 기반" },
  ],
  salary: {
    role: "게임 클라이언트 개발자",
    careerRange: "신입 ~ 3년",
    source: "점핏, 원티드 채용공고 (2025.05 기준)",
    median: "3,554만원",
    low: "3,021만원",
    high: "4,265만원",
    note: "동일 직무 내에서 회사 규모, 지역, 협상력에 따라 차이가 있을 수 있습니다.",
    rangeDescription: "시장 중앙값 기준 ±15%/+20% 추정 분포",
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
  },
  level: {
    grade: "Entry",
    description:
      "포트폴리오 기본 구성은 확인되며, 프로젝트 완성도와 결과물 보강이 필요합니다.",
  },
  summary: {
    positioning: "게임 개발 Entry 포트폴리오 구성 수준 — 프로젝트 완성도와 결과물 보강이 필요해요.",
    strengths: ["커밋 메시지", "팀 협업"],
    quickWins: [
      "README에 프로젝트 목적 + 기술 스택 + 스크린샷 추가",
      "테스트 및 CI/CD 파이프라인 도입 검토",
    ],
  },
  summaryText: "[종합 분석]\nGitHub 포트폴리오 분석 점수: 70.8점 / 100점\n포지셔닝: 게임 개발 Entry 포트폴리오 구성 수준",
  meta: {
    version: "v7.0-mock",
    llmAvailable: true,
    analysisTimeSeconds: 8.2,
    reposAnalyzed: 3,
  },
}

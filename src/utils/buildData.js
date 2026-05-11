import T from '../constants/theme';

export function buildData(u) {
  const seed = u.split("").reduce((a, c) => a + c.charCodeAt(0), 42);
  const rng  = (mn, mx) => mn + ((seed * 6271 + 31337) % 99991) / 99991 * (mx - mn);
  const score        = parseFloat((58 + rng(6, 34)).toFixed(1));
  const contribution = parseFloat((score * 0.75).toFixed(1));
  const quality      = parseFloat((score * 0.135).toFixed(1));
  const consistency  = parseFloat((score * 0.115).toFixed(1));
  const commits      = Math.round(18 + rng(5, 78));
  const loc          = Math.round(7000 + rng(4000, 38000));
  const repos        = Math.round(1 + rng(0, 5));
  const matches = [
    { company:"이스트나인",     title:"웹 인터랙티브 이벤트 엔진 개발 리드", tag:"프론트엔드", sim: parseFloat((0.73 + rng(0, 0.07)).toFixed(4)) },
    { company:"메타익스체인지", title:"프론트 개발 3-5년차",                tag:"프론트엔드", sim: parseFloat((0.70 + rng(0, 0.06)).toFixed(4)) },
    { company:"버스에잇코리아", title:"Mobile Client Engineer",              tag:"모바일",    sim: parseFloat((0.68 + rng(0, 0.06)).toFixed(4)) },
    { company:"뷰리드",         title:"프론트엔드 개발자 (SSR+AJAX)",        tag:"프론트엔드", sim: parseFloat((0.66 + rng(0, 0.06)).toFixed(4)) },
    { company:"팀스파르타",     title:"Software Engineer - Fullstack",       tag:"풀스택",    sim: parseFloat((0.64 + rng(0, 0.06)).toFixed(4)) },
  ].sort((a, b) => b.sim - a.sim);
  const csharpPct = Math.round(70 + rng(0, 28));
  return {
    score, contribution, quality, consistency, commits, loc, repos,
    stacks: [
      { lang: "C#",         pct: csharpPct,        color: T.ink },
      { lang: "TypeScript", pct: Math.round((100 - csharpPct) * 0.6), color: T.teal },
      { lang: "기타",       pct: 100 - csharpPct - Math.round((100 - csharpPct) * 0.6), color: T.slate },
    ],
    stackNote: csharpPct > 90 ? "단일 언어 집중 — TS/React 프로젝트 추가 권장" : null,
    matches,
    salary: { min:33570000, max:34810000, jumpfit:34805488, wanted:33572409 },
    aiComment: `${u}님의 GitHub 활동 분석 결과, C# 기반 이벤트 주도 아키텍처 설계 경험이 확인됩니다. ${commits}개의 커밋과 ${(loc/1000).toFixed(1)}k LOC는 신입 기준 준수한 볼륨입니다. 다만 CI/CD와 테스트 커버리지 부재가 현재 포트폴리오의 핵심 약점으로, 채용 담당자 관점에서 "프로덕션 준비 미완"으로 읽힐 수 있습니다. GitHub Actions 기반 워크플로우 1개와 xUnit 테스트 10개 이상을 추가하면 체감 등급이 즉각 상승할 것으로 예측됩니다.`,
  };
}

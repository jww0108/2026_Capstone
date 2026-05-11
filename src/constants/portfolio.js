export const PORTFOLIO = [
  { label: "README 품질",    status: "양호",   detail: "평균 1,500자 이상, 구성 적절",           rec: null },
  { label: "프로젝트 구조",  status: "양호",   detail: "디렉터리 구성, .gitignore 존재",          rec: null },
  { label: "테스트 커버리지",status: "미흡",   detail: "테스트 파일이 감지되지 않음",              rec: "xUnit 기반 테스트 최소 10개 추가" },
  { label: "CI/CD",          status: "미경험", detail: "GitHub Actions 또는 Dockerfile 없음",   rec: "lint/test 워크플로우 1개 이상 추가" },
  { label: "커밋 메시지",    status: "양호",   detail: "메시지가 비교적 구체적이고 서술적",        rec: null },
  { label: "커밋 리듬",      status: "보통",   detail: "활성 주 평균 약 4.8회",                  rec: "작은 단위로 더 자주 커밋 권장" },
  { label: "배포 경험",      status: "미경험", detail: "docker-compose, Vercel 등 없음",         rec: "배포 링크 1개 이상 포함 권장" },
  { label: "협업 패턴",      status: "보통",   detail: "단일 작성자 위주",                       rec: "PR 리뷰, 이슈 트래킹 이력 추가" },
  { label: "성장 궤적",      status: "양호",   detail: "최근 커밋 메시지 평균 1.43배 길어지는 추세", rec: null },
];

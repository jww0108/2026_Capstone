# Git2Value Frontend

GitHub 포트폴리오 진단, 직무 매칭, 시장 연봉 밴드 분석 UI (Next.js App Router + Tailwind CSS).

## Run

```bash
npm install
cp .env.example .env.local   # Windows: copy .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Backend API

프론트엔드는 FastAPI 게이트웨이의 `POST /v1/analyze`를 호출합니다.

| 환경 변수 | 설명 |
|-----------|------|
| `NEXT_PUBLIC_API_BASE_URL` | 백엔드 base URL (예: `http://localhost:8080`) |
| `NEXT_PUBLIC_USE_MOCK` | `true`이면 API 없이 mock 데이터 사용 |

요청 형식:

```json
{
  "github_username": "user",
  "repos": ["user/repo", "user/repo2/tree/branch"],
  "applicant_years": 0
}
```

### CORS

백엔드 `CORS_ORIGINS`에 프론트 origin을 등록해야 합니다.

- 로컬: `http://localhost:3000`
- 배포: Vercel 등 실제 프론트 URL

백엔드 실행 예:

```bash
# basic/ 디렉터리
python main.py
```

## Pages

- `/` 입력 화면
- `/loading` 분석 진행 (E2E API 호출)
- `/result` 결과 요약
- `/portfolio` 포트폴리오 진단
- `/jobs` 직무 매칭
- `/salary` 시장 연봉 밴드
- `/help` 문제해결 가이드

## Assets

Reference-based assets are placed in `public/images/`.

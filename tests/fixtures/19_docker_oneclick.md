# DevBoard — 개발팀 경량 칸반 보드

소규모 개발팀을 위한 경량 칸반 보드입니다.
Jira처럼 복잡하지 않고, 이슈 트래킹과 스프린트 관리에 집중합니다.

## 스크린샷

![보드 메인](./screenshots/board.png)
![이슈 상세](./screenshots/issue-detail.png)

## 기술 스택

- **Backend**: FastAPI + PostgreSQL + SQLAlchemy
- **Frontend**: React + TypeScript + Tailwind CSS
- **Infra**: Docker Compose + Nginx (리버스 프록시)

## 실행 방법

### Docker로 바로 실행 (권장)

Docker와 Docker Compose가 설치되어 있으면 됩니다:

```bash
git clone https://github.com/user/devboard
cd devboard
cp .env.example .env   # 필요 시 포트/DB 비밀번호 수정
docker compose up -d
```

→ http://localhost:3000 에서 바로 사용 가능합니다.

### 개발 환경 (Docker 없이)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (별도 터미널)
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## 주요 기능

- 칸반 보드 (드래그&드롭으로 상태 변경)
- 이슈 생성 / 수정 / 삭제
- 마감일 및 담당자 지정
- 스프린트 단위 관리
- 팀원 초대 (이메일)

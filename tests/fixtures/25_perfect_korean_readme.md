# TeamSync — 팀 협업 올인원 플랫폼

> "Slack + Notion + Jira를 하나로" — 중소 개발팀을 위한 협업 도구

실시간 채팅, 문서 공유, 칸반 보드를 하나의 플랫폼에서 제공합니다.
**도구가 많아 오히려 비효율적이라는 팀 내 문제를 해결하기 위해** 6개월간 직접 기획하고 개발했습니다.

## 주요 기능 시연

![실시간 채팅](./docs/demo-chat.gif)
![칸반 보드 드래그앤드롭](./docs/demo-kanban.gif)

## 시스템 아키텍처

![아키텍처 다이어그램](./docs/architecture.png)

```
[React + TypeScript]
        ↕ WebSocket / REST
[Spring Boot API Server]
        ↓              ↓
[Redis Pub/Sub]   [PostgreSQL]
        ↓
[WebSocket Broadcast → 모든 클라이언트]
        ↓
[AWS S3 — 파일 첨부]
```

## 기술 스택 및 선택 이유

| 기술 | 선택 이유 |
|------|----------|
| Spring Boot + WebSocket (STOMP) | 실시간 양방향 통신, 팀 친숙도 |
| Redis Pub/Sub | 다중 서버 인스턴스에서 메시지 브로드캐스트 |
| PostgreSQL | 문서·칸반 데이터의 복잡한 쿼리 지원 |
| AWS S3 + Presigned URL | 대용량 파일 클라이언트 직접 업로드 |

## 빠른 시작

```bash
git clone https://github.com/team/teamsync
cd teamsync
cp .env.example .env   # AWS 키, DB 설정 입력
docker compose up -d
```

→ http://localhost:3000 에서 바로 접속 가능합니다.

### 개발 환경 (Docker 없이)

```bash
# Backend
./gradlew bootRun

# Frontend (별도 터미널)
cd frontend && npm install && npm run dev
```

## 성과 및 트러블슈팅

- **WebSocket 연결 끊김** → Heartbeat + 재연결 로직으로 해결
- **파일 업로드 속도** → Presigned URL 방식으로 클라이언트가 S3에 직접 업로드
- 팀 3명, 개발 4개월, 실 사용자 12명 베타 테스트 완료

## 기여 방법

[CONTRIBUTING.md](./CONTRIBUTING.md)를 참고하세요.

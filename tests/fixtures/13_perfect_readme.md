# TaskFlow — 팀 프로젝트 관리 도구

실시간 칸반 보드와 타임라인을 결합한 팀 프로젝트 관리 웹 애플리케이션입니다.
Trello의 직관성과 Jira의 일정 관리 기능을 소규모 팀에 맞게 재설계했습니다.

[![CI](https://github.com/username/taskflow/actions/workflows/ci.yml/badge.svg)](https://github.com/username/taskflow/actions)
[![Coverage](https://codecov.io/gh/username/taskflow/branch/main/graph/badge.svg)](https://codecov.io/gh/username/taskflow)

## 문제 정의

5~10인 규모 팀은 Jira처럼 복잡한 도구 대신 Trello를 사용하지만, 타임라인·마감일 관리 기능이 부족합니다.
TaskFlow는 칸반 + 간트 차트를 단일 화면에서 전환할 수 있어 이 문제를 해결합니다.

## 데모

![칸반 보드 데모](docs/demo/kanban.gif)
![타임라인 뷰](docs/demo/timeline.gif)
![실시간 협업](docs/demo/realtime.gif)

## 아키텍처

![시스템 아키텍처](docs/architecture.png)

## 기술 스택

| 영역 | 기술 | 선택 이유 |
|------|------|-----------|
| 프론트엔드 | React 18 + TypeScript | 타입 안전성, 컴포넌트 재사용 |
| 상태 관리 | Zustand | Redux 대비 낮은 보일러플레이트 |
| 실시간 | WebSocket (SockJS/STOMP) | 낮은 지연시간 양방향 통신 |
| 백엔드 | Spring Boot 3.2 | 팀 기술 역량, 성숙한 생태계 |
| DB | PostgreSQL + Redis | 관계형 데이터 + 세션/캐시 |
| 배포 | AWS ECS + RDS | 컨테이너 오케스트레이션 |
| CI/CD | GitHub Actions | 자동 테스트·배포 파이프라인 |

## 빠른 시작 (Docker)

```bash
# 저장소 클론
git clone https://github.com/username/taskflow.git
cd taskflow

# 환경 변수 설정
cp .env.example .env

# 전체 스택 실행 (DB, Redis, 백엔드, 프론트엔드 포함)
docker-compose up -d

# 브라우저에서 접속
open http://localhost:3000
# API: http://localhost:8080/api
# Swagger: http://localhost:8080/swagger-ui.html
```

## 개발 환경 실행

```bash
# 백엔드
cd backend
./gradlew bootRun -Dspring.profiles.active=local

# 프론트엔드
cd frontend
npm install
npm run dev
```

## 테스트

```bash
# 백엔드 전체 테스트 (단위 + 통합)
cd backend && ./gradlew test

# 커버리지 리포트 (목표: 80% 이상)
./gradlew jacocoTestReport
# → build/reports/jacoco/test/html/index.html

# 프론트엔드 테스트
cd frontend && npm test -- --coverage
```

## 주요 기능

- **실시간 칸반 보드**: 드래그&드롭으로 태스크 이동, 변경사항 즉시 동기화
- **타임라인/간트 차트**: 마감일 시각화, 의존성 표현
- **멤버 관리**: 초대 링크, 역할(관리자/편집자/뷰어) 권한 설정
- **알림**: 태스크 할당·마감 임박 시 이메일/인앱 알림

## API 문서

Swagger UI: [http://localhost:8080/swagger-ui.html](http://localhost:8080/swagger-ui.html)

주요 엔드포인트:
- `POST /api/auth/login` — 로그인
- `GET/POST /api/projects` — 프로젝트 목록/생성
- `GET/POST /api/projects/{id}/tasks` — 태스크 조회/생성
- `WS /ws/board/{projectId}` — 실시간 보드 동기화

## 팀 구성 및 기여

| 이름 | 역할 | 주요 기여 |
|------|------|-----------|
| 김OO | 백엔드 리드 | WebSocket 실시간 동기화, AWS 배포 |
| 이OO | 프론트엔드 리드 | 칸반 DnD, 타임라인 컴포넌트 |
| 박OO | 풀스택 | 인증/권한, CI/CD 파이프라인 |
| 최OO | 백엔드 | 알림 시스템, API 설계 |

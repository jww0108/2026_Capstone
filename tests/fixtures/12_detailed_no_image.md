# 도서관 좌석 예약 시스템

## 프로젝트 소개

대학 도서관 좌석을 웹에서 실시간으로 예약하고 확인하는 시스템입니다.
좌석 QR 코드 체크인, 잔여 좌석 실시간 표시, 노쇼 방지 자동 취소 기능을 구현했습니다.

## 개발 동기

코로나 이후 도서관 좌석 예약이 필수화됐지만, 기존 시스템은 새로고침 없이는 잔여 좌석 현황을 확인할 수 없어 불편했습니다.
WebSocket 기반 실시간 업데이트로 이 문제를 해결했습니다.

## 기술 스택

### 백엔드

- Spring Boot 3.1 — RESTful API + WebSocket 서버
- Spring Security + JWT — 학생증 번호 기반 인증
- JPA + Hibernate — 도메인 모델 영속화
- MariaDB — 좌석·예약 데이터 저장
- Redis — 세션 관리, 실시간 좌석 상태 캐싱

### 프론트엔드

- React 18 + TypeScript — 컴포넌트 기반 UI
- Zustand — 전역 상태 관리 (좌석 맵)
- SockJS + STOMP — 실시간 좌석 현황 수신

### 인프라

- AWS EC2 (t3.small) — 애플리케이션 서버
- AWS RDS (MariaDB) — 관리형 데이터베이스
- Nginx — 리버스 프록시
- GitHub Actions — CI/CD 파이프라인

## 주요 기능 설명

### 실시간 좌석 맵

WebSocket을 통해 다른 사용자가 예약하거나 취소하는 순간 좌석 색상이 즉시 변경됩니다.
좌석 상태는 Redis에 캐싱하여 DB 부하를 최소화했습니다.

### QR 코드 체크인

예약 후 도서관 입장 시 QR 코드를 스캔하면 자동으로 체크인됩니다.
체크인 없이 15분이 지나면 자동으로 예약이 취소됩니다.

## 실행 방법

```bash
# 백엔드
cd backend
./gradlew bootRun

# 프론트엔드
cd frontend
npm install && npm start
```

환경변수는 `backend/src/main/resources/application-local.yml` 참고.

## 테스트

```bash
# 백엔드 단위 테스트
./gradlew test

# 테스트 커버리지
./gradlew jacocoTestReport
```

## 아키텍처

(다이어그램 추가 예정)

## 팀원

| 이름 | 역할 |
|------|------|
| 이OO | 백엔드, AWS 인프라 |
| 최OO | 프론트엔드 |
| 강OO | 백엔드, 인증 모듈 |

# Dungeon Crawler 2D

2D 탑다운 던전 탐험 게임입니다. Unity 2022 LTS로 개발되었으며, 무작위 던전 생성과 전투 시스템을 구현했습니다.

## About

플레이어는 무작위로 생성되는 던전을 탐험하며 몬스터를 처치하고 아이템을 수집합니다.
클리어 시간 단축을 목표로 하는 스피드런 모드도 포함되어 있습니다.

## 개발 환경

- Unity 2022.3 LTS
- C#
- Universal Render Pipeline (URP)

## 주요 구현 내용

- **절차적 던전 생성**: BSP 알고리즘 기반 무작위 맵 생성
- **전투 시스템**: 근접·원거리 공격, 회피 메커니즘
- **아이템 시스템**: 랜덤 드롭, 인벤토리 관리
- **스피드런 모드**: 레코드 저장 및 리플레이 기능

## 플레이 방법

1. [Releases](https://github.com/username/dungeon-crawler/releases) 페이지에서 최신 빌드 다운로드
2. `DungeonCrawler.exe` 실행 (Windows) 또는 `DungeonCrawler.app` (macOS)

또는 Unity 에디터에서 직접 실행:
1. Unity Hub에서 Unity 2022.3 LTS 설치
2. 프로젝트 열기 → `Assets/Scenes/MainMenu.unity` 실행

## 스크린샷

![게임 플레이](Screenshots/gameplay.gif)
![던전 예시](Screenshots/dungeon_example.png)
![전투 시스템](Screenshots/combat.png)

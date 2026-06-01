# JobCrawler — 채용공고 자동 수집기

잡코리아, 사람인, 원티드에서 채용공고를 자동으로 수집해 Excel 또는 Notion으로 정리해주는 크롤러입니다.
취업 준비 중 공고를 일일이 확인하는 번거로움을 없애기 위해 만들었습니다.

## 지원 플랫폼

| 플랫폼 | 수집 항목 | 갱신 주기 |
|--------|----------|----------|
| 잡코리아 | 직무, 회사명, 마감일, 연봉 | 1시간 |
| 사람인 | 직무, 회사명, 마감일 | 1시간 |
| 원티드 | 직무, 회사명, 포지션, 스택 | 30분 |

## 설치 및 실행

```bash
git clone https://github.com/user/job-crawler
cd job-crawler
pip install -r requirements.txt
cp config.example.yaml config.yaml   # Notion 토큰 등 설정
python crawler.py --all
```

### 키워드 필터 설정

`config.yaml`에서 직무 키워드, 지역, 경력 조건을 설정합니다:

```yaml
keywords:
  - "백엔드"
  - "Python"
location: "서울"
experience: "신입"
output: "notion"   # 또는 "excel"
```

## 출력 예시

수집된 데이터는 `output/jobs_YYYYMMDD.xlsx`로 저장되거나 Notion 데이터베이스에 자동 추가됩니다.

## 기술 스택

- Python 3.10
- Selenium + BeautifulSoup
- Notion API (notion-client)
- APScheduler (주기 실행)

# 서울 부동산 가격 예측 분석

공공데이터포털의 아파트 실거래가 데이터(2020-2024)를 활용해 서울 지역 부동산 가격 변동 패턴을 분석하고,
머신러닝 모델로 지역별 평균 가격을 예측합니다.

## 데이터셋

- **출처**: 국토교통부 아파트 실거래가 API
- **기간**: 2020.01 ~ 2024.12 (5년)
- **레코드 수**: 약 380만 건
- **주요 컬럼**: 지역구, 면적, 층수, 건축연도, 거래금액

## 모델 성능 비교

| 모델 | RMSE (만원) | MAE (만원) | R² |
|------|------------|-----------|-----|
| Linear Regression | 12,450 | 8,230 | 0.72 |
| Random Forest | 6,820 | 4,510 | 0.91 |
| XGBoost | **6,340** | **4,100** | **0.93** |

## 주요 인사이트

- 강남3구(강남/서초/송파) 가격 변동성이 일반구 대비 **2.3배** 높음
- 역세권(도보 10분 이내) 프리미엄: 평균 **+18%**
- 건축연도보다 리모델링 여부가 가격에 더 큰 영향 (feature importance 기준)

## 시각화

![구별 평균 가격 히트맵](./plots/district_heatmap.png)
![연도별 가격 추이](./plots/yearly_trend.png)
![Feature Importance](./plots/feature_importance.png)

## 실행 방법

```bash
git clone https://github.com/user/seoul-realestate
cd seoul-realestate
pip install -r requirements.txt

# 데이터 수집 (API 키 필요)
python collect_data.py --years 2020 2024

# 분석 실행
jupyter notebook analysis.ipynb
```

## 파일 구조

```
├── collect_data.py   # 공공 API 수집
├── preprocess.py     # 전처리
├── analysis.ipynb    # 메인 분석 노트북
├── models/           # 학습된 모델 저장
└── plots/            # 시각화 결과
```

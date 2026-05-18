# 한국어 감성 분석 모델

BERT 기반 한국어 리뷰 감성 분석(긍정/부정/중립) 모델입니다. 네이버 쇼핑 리뷰 50만 건으로 학습했습니다.

## 문제 정의

한국어 리뷰 데이터에서 감성을 자동으로 분류하는 기존 모델들은 쇼핑 도메인 특화 어휘(상품명, 브랜드 약어 등)에 취약했습니다.
도메인 특화 파인튜닝으로 이 문제를 개선했습니다.

## 기술 스택

- **모델**: klue/bert-base (허깅페이스 사전학습)
- **학습 프레임워크**: PyTorch + Transformers
- **데이터 처리**: pandas, KoNLPy
- **실험 추적**: MLflow
- **서빙**: FastAPI + uvicorn

## 모델 성능

| 지표 | 학습 전 (zero-shot) | 파인튜닝 후 |
|------|-------------------|------------|
| Accuracy | 61.3% | **88.7%** |
| F1 (macro) | 58.9% | **87.2%** |
| Precision | 60.1% | 88.4% |
| Recall | 59.4% | 87.0% |

![학습 곡선](results/training_curve.png)
![혼동 행렬](results/confusion_matrix.png)

## 실행 방법

```bash
# 환경 설정
pip install -r requirements.txt

# 데이터 전처리
python preprocess.py --input data/raw/reviews.csv --output data/processed/

# 모델 학습
python train.py --model klue/bert-base --epochs 5 --batch_size 32

# 추론 서버 실행
uvicorn serve:app --host 0.0.0.0 --port 8000
```

## 데이터셋

- 출처: 네이버 쇼핑 리뷰 (공개 데이터)
- 총 50만 건 (학습 40만 / 검증 5만 / 테스트 5만)
- 라벨 분포: 긍정 60%, 부정 25%, 중립 15%

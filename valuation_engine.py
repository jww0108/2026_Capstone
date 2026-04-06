import json
import os
import importlib.util
from typing import Any, Dict, List, Optional

# 점핏 route_job_category 키 → 원티드 salary JSON (신입~3년차 교차검증용)
JUMPIT_TO_WANTED_FILE: Dict[str, str] = {
    "블록체인": "salary_data_1027_블록체인_플랫폼_엔지니어.json",
    "인공지능/머신러닝": "salary_data_1634_머신러닝_엔지니어.json",
    "VR/AR/3D": "salary_data_10112_VR_엔지니어.json",
    "빅데이터 엔지니어": "salary_data_1025_빅데이터_엔지니어.json",
    "HW/임베디드": "salary_data_658_임베디드_개발자.json",
    "SW/솔루션": "salary_data_10110_소프트웨어_엔지니어.json",
    "개발 PM": "salary_data_877_개발_매니저.json",
    "devops/시스템 엔지니어": "salary_data_674_DevOps_&_시스템 관리자.json",
    "기술지원": "salary_data_1026_기술지원.json",
    "서버/백엔드": "salary_data_872_서버_개발자.json",
    "크로스플랫폼 앱": "salary_data_10111_크로스플랫폼_앱_개발자.json",
    "안드로이드": "salary_data_677_안드로이드_개발자.json",
    "DBA": "salary_data_10231_DBA.json",
    "iOS": "salary_data_678_iOS_개발자.json",
    "웹 풀스택": "salary_data_873_웹_개발자.json",
    "프론트엔드": "salary_data_669_프론트엔드_개발자.json",
    "QA 엔지니어": "salary_data_676_QA,테스트_엔지니어.json",
    "웹퍼블리셔": "salary_data_939_웹_퍼블리셔.json",
}


def _format_manwon_range(low_won: int, high_won: int) -> str:
    return f"{low_won // 10000:,}만 ~ {high_won // 10000:,}만원"


class Git2ValueEngine:
    def __init__(self):
        self.jumpit_data = self._load_jumpit_data()
        self._salary_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data",
            "wanted_data",
            "salary_data",
        )

    def _load_jumpit_data(self):
        """점핏 시장 연봉 룩업 테이블을 메모리에 로드합니다."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "data", "jumpit_data", "korean_it_salary_lookup_2025.py")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"데이터 파일이 없습니다: {file_path}")

        spec = importlib.util.spec_from_file_location("jumpit_lookup", file_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(module)  # type: ignore

        for attr in dir(module):
            if not attr.startswith("__") and isinstance(getattr(module, attr), dict):
                return getattr(module, attr)
        return {}

    def get_market_base(self, job_category: str, years_of_experience: int) -> int:
        """연차를 기반으로 정확한 시장 중앙값(P50)을 추출합니다."""
        exp_data = self.jumpit_data.get("experience_level", {})

        if years_of_experience <= 3:
            bucket = exp_data.get("junior_1_to_3_years", {})
        elif years_of_experience <= 9:
            bucket = exp_data.get("middle_4_to_10_years", {})
        else:
            bucket = exp_data.get("senior_over_10_years", {})

        base_salary = bucket.get(job_category)

        if not base_salary:
            raise ValueError(f"'{job_category}'에 대한 연봉 데이터가 존재하지 않습니다.")

        return base_salary

    def _wanted_junior_blend(self, job_category: str) -> Optional[int]:
        fname = JUMPIT_TO_WANTED_FILE.get(job_category)
        if not fname:
            return None
        path = os.path.join(self._salary_dir, fname)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
        salaries = data.get("salaries_by_year") or {}
        keys = ["신입", "1년차", "2년차", "3년차"]
        vals = [int(salaries[k]) for k in keys if salaries.get(k) is not None]
        if not vals:
            return None
        return int(sum(vals) / len(vals))

    def get_market_band(
        self,
        job_category: str,
        years_max: int = 3,
    ) -> Dict[str, Any]:
        """
        v4.0: GitHub 점수와 독립된 시장 연봉 밴드(신입~3년차 구간).
        years_max: 3이면 junior_1_to_3_years 버킷(점핏) 기준.
        """
        if years_max > 3:
            years_lookup = years_max
        else:
            years_lookup = 1

        jumpit_median = self.get_market_base(job_category, years_lookup)
        wanted_median = self._wanted_junior_blend(job_category)

        if wanted_median is not None:
            low_won = min(jumpit_median, wanted_median)
            high_won = max(jumpit_median, wanted_median)
        else:
            low_won = int(jumpit_median * 0.92)
            high_won = int(jumpit_median * 1.08)

        combined_range = _format_manwon_range(low_won, high_won)

        exp_data = self.jumpit_data.get("experience_level", {})
        junior = exp_data.get("junior_1_to_3_years", {})
        comparison: List[Dict[str, str]] = []
        for cat, med in sorted(junior.items(), key=lambda x: x[1], reverse=True)[:12]:
            w = self._wanted_junior_blend(cat)
            if w is not None:
                lo, hi = min(med, w), max(med, w)
            else:
                lo, hi = int(med * 0.92), int(med * 1.08)
            comparison.append(
                {
                    "category": cat,
                    "junior_range": _format_manwon_range(lo, hi),
                }
            )

        return {
            "market_salary_band": {
                "matched_category": job_category,
                "experience_level": "신입 (0~3년)",
                "salary_range": {
                    "jumpit_median": jumpit_median,
                    "wanted_median": wanted_median,
                    "combined_range": combined_range,
                },
                "source": "점핏·원티드 2025 채용공고 기반",
                "note": "동일 직무 내에서 회사 규모, 지역, 협상력에 따라 차이가 있을 수 있습니다.",
            },
            "category_comparison": comparison,
        }


if __name__ == "__main__":
    engine = Git2ValueEngine()
    band = engine.get_market_band("서버/백엔드")
    msb = band["market_salary_band"]
    sr = msb["salary_range"]
    print("\n[Git2Value v4.0] 시장 연봉 밴드 (GitHub 점수와 독립)")
    print("=" * 50)
    print(f"직무: {msb['matched_category']} / {msb['experience_level']}")
    print(f"점핏 중앙값: {sr['jumpit_median']:,}원")
    wm = sr.get("wanted_median")
    print(f"원티드(신입~3년 평균): {wm if wm is not None else '해당 직무 매핑 없음'}")
    print(f"참고 구간: {sr['combined_range']}")
    print(f"출처: {msb['source']}")
    print("=" * 50)

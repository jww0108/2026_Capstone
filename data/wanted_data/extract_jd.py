import requests
import json
import os
import time
import random

def fetch_jd_data(job_id: int):
    """
    [Core Logic] 단일 Job ID의 상세 API를 호출하여 정제된 딕셔너리를 반환합니다.
    디스크 I/O(저장)의 책임은 이 함수에서 분리되었습니다.
    """
    api_url = f"https://www.wanted.co.kr/api/v4/jobs/{job_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        
        # 공고가 마감되었거나 삭제된 경우 (404 등) 조용히 None 반환
        if response.status_code != 200:
            return None
            
        data = response.json()
        job_info = data.get("job", {})
        detail = job_info.get("detail", {})
        company_info = job_info.get("company", {})
        
        company_name = company_info.get("name", "회사명 비공개")
        position = job_info.get("position", "포지션명 없음")
        
        requirements = detail.get("requirements", "")
        preferred = detail.get("preferred_points", "")
        main_tasks = detail.get("main_tasks", "")
        
        corpus_text = f"Job Title: {position}\n\n"
        corpus_text += f"[Main Tasks - 주요 업무]\n{main_tasks}\n\n"
        corpus_text += f"[Requirements - 자격 요건]\n{requirements}\n\n"
        corpus_text += f"[Preferred - 우대 사항]\n{preferred}"
        
        return {
            "job_id": job_id,
            "company_name": company_name,
            "position": position,
            "ai_corpus_text": corpus_text.strip()
        }

    except requests.exceptions.RequestException:
        # 타임아웃 등 네트워크 단절 시
        return None
    except Exception as e:
        print(f"❌ {job_id} 파싱 에러: {e}")
        return None


def process_bulk_jds():
    """
    [Pipeline Orchestrator] ID 리스트를 읽어 JSONL 형태의 대규모 코퍼스로 병합합니다.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, "wanted_job_ids.json")
    output_file = os.path.join(current_dir, "unified_jd_corpus.jsonl")
    
    # 1. ID 리스트 로드
    if not os.path.exists(input_file):
        print(f"❌ 에러: '{input_file}' 파일이 없습니다. Phase 1 스크립트를 먼저 실행하세요.")
        return
        
    with open(input_file, "r", encoding="utf-8") as f:
        job_ids = json.load(f)
        
    total_ids = len(job_ids)
    print(f"🚀 총 {total_ids}개의 Job ID 추출 파이프라인을 가동합니다.")
    print(f"📂 결과물은 '{output_file}'에 JSONL 형태로 실시간 누적 저장됩니다.\n")
    
    success_count = 0
    fail_count = 0
    
    # 2. 'a' (Append) 모드로 파일 열기: 중간에 스크립트를 꺼도 기존 데이터 보존
    with open(output_file, "a", encoding="utf-8", newline="\n") as out_f:
        for index, job_id in enumerate(job_ids, start=1):
            print(f"⏳ [{index}/{total_ids}] ID {job_id} 처리 중...", end="\r") # \r로 진행률 덮어쓰기 출력
            
            data = fetch_jd_data(job_id)
            
            if data:
                # 3. JSON Lines 규격에 맞게 한 줄(문자열)로 덤프 후 줄바꿈 기호 삽입
                out_f.write(json.dumps(data, ensure_ascii=False) + "\n")
                # 버퍼를 강제로 비워 즉시 디스크에 쓰기 (Crash Safe)
                out_f.flush() 
                success_count += 1
            else:
                fail_count += 1
                
            # 4. [보안 로직] IP 차단 방지를 위한 랜덤 슬립 (0.5초 ~ 1.5초)
            # 서버 부하를 고려하여 너무 짧게 주지 마십시오.
            time.sleep(random.uniform(0.5, 1.5))
            
    print(f"\n\n🎉 대규모 코퍼스 구축 완료!")
    print(f"✅ 성공: {success_count}건 | ❌ 실패/마감: {fail_count}건")
    print(f"📂 통합 데이터 경로: {output_file}")


# --- 실행부 ---
if __name__ == "__main__":
    process_bulk_jds()
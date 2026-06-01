import os
import json
from bs4 import BeautifulSoup

def process_wanted_salary_html(html_filename: str):
    """
    [의도] 원티드 HTML 파일 하나를 통째로 씹어먹고, 
    원하는 연봉 데이터만 추출하여 특정 폴더에 정제된 JSON으로 저장하는 단일 파이프라인.
    """
    # 1. 경로 동적 할당 (터미널 실행 위치와 무관하게 작동하도록 보장)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_file_path = os.path.join(current_dir, html_filename)
    
    # [방어 로직] 타겟 폴더인 'wanted_data'가 없으면 에러를 뿜지 않고 조용히 생성함 (exist_ok=True)
    output_dir = os.path.join(current_dir, "wanted_data")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"⏳ 데이터 추출 시작: {html_filename} ...")
    
    try:
        # --- 1단계: Extract (HTML 읽기 및 보물상자 찾기) ---
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
            
        soup = BeautifulSoup(html_content, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        
        if not script_tag or not script_tag.string:
            raise ValueError("HTML 내에 '__NEXT_DATA__' 태그가 존재하지 않습니다.")

        # --- 2단계: Transform (거대 JSON 파싱 및 타겟 노드 정제) ---
        raw_data = json.loads(script_tag.string)
        
        # [핵심] 수만 줄의 데이터 중 우리가 필요한 심장부로 다이렉트 접근
        salary_data = raw_data["props"]["pageProps"]["salaryData"]
        
        job_title = salary_data["tag"]["title"]
        job_id = salary_data["tag"]["id"]
        
        clean_salary_table = {
            "source": "wanted",
            "job_title": job_title,
            "job_id": job_id,
            "salaries_by_year": {}
        }
        
        for item in salary_data["hits"]:
            year = item["annual"]
            salary = item["job_final_salary"]
            year_key = "신입" if year == 0 else f"{year}년차"
            clean_salary_table["salaries_by_year"][year_key] = salary

        # --- 3단계: Load (정제된 데이터를 wanted_data 폴더에 저장) ---
        output_filename = f"salary_data_{job_id}_{job_title.replace(' ', '_')}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, "w", encoding="utf-8") as out_file:
            json.dump(clean_salary_table, out_file, ensure_ascii=False, indent=4)
            
        print(f"✅ 파이프라인 성공! 추출된 직무: {job_title}")
        print(f"📂 저장 완료: {output_path}")

    # [에러 핸들링] 시스템이 죽지 않고 원인을 명확히 뱉어내도록 다중 예외 처리
    except FileNotFoundError:
        print(f"❌ 에러: '{html_filename}' 파일을 찾을 수 없습니다. 경로를 확인하세요.")
    except KeyError as e:
        print(f"❌ 에러: 원티드 웹사이트의 데이터 구조가 변경되었습니다. 못 찾은 키: {e}")
    except Exception as e:
        print(f"❌ 알 수 없는 치명적 에러 발생: {e}")

# --- 실행부 ---
if __name__ == "__main__":
    # 타겟 파일명 지정
    TARGET_HTML = "직군·연차별 연봉 _ 원티드.html"
    
    # 단 한 줄의 함수 호출로 모든 과정을 자동화
    process_wanted_salary_html(TARGET_HTML)
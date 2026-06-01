import json
import os

# 1. 아까 저장해둔 보물상자(wanted_parsed_data.json) 파일의 경로를 잡습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "wanted_parsed_data.json")

# 2. JSON 파일을 읽어옵니다.
with open(file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

try:
    # 3. 질문자님이 찾아주신 경로를 따라 데이터의 핵심(Core)으로 곧장 들어갑니다.
    # 구조: props -> pageProps -> salaryTagsData -> salaryData
    salary_data = data["props"]["pageProps"]["salaryData"]
    
    # 4. 직무 이름과 ID를 추출합니다.
    job_title = salary_data["tag"]["title"]
    job_id = salary_data["tag"]["id"]
    
    # 5. 연차별 연봉 데이터를 예쁜 딕셔너리로 재조립합니다.
    clean_salary_table = {
        "job_title": job_title,
        "job_id": job_id,
        "salaries_by_year": {}
    }
    
    for item in salary_data["hits"]:
        year = item["annual"]
        salary = item["job_final_salary"]
        
        # 보기 편하게 "0년차", "1년차" 형식의 키(Key)를 만듭니다.
        year_key = "신입" if year == 0 else f"{year}년차"
        clean_salary_table["salaries_by_year"][year_key] = salary

    # 6. 결과를 화면에 예쁘게 출력합니다.
    print(f"✅ 직무 추출 완료: {clean_salary_table['job_title']} (ID: {clean_salary_table['job_id']})")
    print("-" * 40)
    for year_key, salary in clean_salary_table["salaries_by_year"].items():
        print(f"{year_key.ljust(5)} : {salary:,}원")
        
    # 7. (선택) 이 깔끔해진 데이터를 AI 파이프라인에서 쓸 수 있게 새로 저장합니다.
    output_path = os.path.join(current_dir, f"clean_salary_{job_id}.json")
    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(clean_salary_table, out_file, ensure_ascii=False, indent=4)
        
except KeyError as e:
    print(f"❌ JSON 구조가 예상과 다릅니다. 찾을 수 없는 키(Key): {e}")
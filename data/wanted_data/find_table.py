import json
from bs4 import BeautifulSoup
import os

# 1. 질문자님이 다운로드하신 HTML 파일을 파이썬으로 엽니다.
# (파이썬 파일과 HTML 파일이 같은 폴더에 있어야 합니다)
current_dir = os.path.dirname(os.path.abspath(__file__))
file_name = "직군·연차별 연봉 _ 원티드.html"
file_path = os.path.join(current_dir, file_name)

with open(file_path, "r", encoding="utf-8") as file:
    html_content = file.read()

# 2. BeautifulSoup을 사용해 HTML 문서를 분석할 준비를 합니다.
soup = BeautifulSoup(html_content, "html.parser")

# 3. 빈 액자 뒷면을 뒤져서 'id가 __NEXT_DATA__인 script 태그'를 찾습니다.
# 이것이 바로 연봉 데이터가 숨겨진 보물상자입니다.
secret_box = soup.find("script", id="__NEXT_DATA__")

if secret_box:
    data = json.loads(secret_box.string) # type: ignore
    print("🎉 보물상자를 성공적으로 열었습니다!")
    
    # --- [여기가 추가된 부분입니다] ---
    # 메모리에만 있는 데이터를 우리가 눈으로 볼 수 있게 새로운 JSON 파일로 저장합니다.
    output_path = os.path.join(current_dir, "wanted_parsed_data.json")
    
    with open(output_path, "w", encoding="utf-8") as out_file:
        # indent=4를 주면 줄바꿈과 들여쓰기가 예쁘게 적용되어 사람이 읽기 편해집니다.
        json.dump(data, out_file, ensure_ascii=False, indent=4)
        
    print(f"📂 데이터를 보기 좋게 정리하여 다음 파일로 저장했습니다: {output_path}")
    print("Cursor 에디터에서 이 파일을 열고 'Ctrl+F'를 눌러 숫자를 검색해 보세요!")
    # ---------------------------------
else:
    print("보물상자를 찾지 못했습니다.")
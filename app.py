import os
from flask import Flask, render_template, request, jsonify
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def search_in_excel_files(keyword):
    results = []
    if not keyword:
        return results
    
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.xls', '.xlsx'))]
    
    for filename in files:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            # 엑셀 파일 내의 모든 시트 읽기
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name).fillna('')
                
                # 키워드가 포함된 행 검색
                for idx, row in df.iterrows():
                    row_str = " ".join([str(val) for val in row.values])
                    if keyword.lower() in row_str.lower():
                        # 검색 결과에 출처 파일, 시트, 내용 담기
                        results.append({
                            'filename': filename,
                            'sheet': sheet_name,
                            'data': [str(val) for val in row.values[:6]] # 주요 6개 컬럼 표시
                        })
                        if len(results) >= 50: # 검색 결과 최대 50개 제한
                            return results
        except Exception as e:
            continue
            
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    search_keyword = request.args.get('keyword', '')
    search_results = []
    
    if request.method == 'POST':
        uploaded_files = request.files.getlist('files')
        saved_names = []
        for file in uploaded_files:
            if file and file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                saved_names.append(file.filename)
        if saved_names:
            message = f"총 {len(saved_names)}개 파일이 새로 등록되었습니다."

    if search_keyword:
        search_results = search_in_excel_files(search_keyword)

    current_files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', message=message, current_files=current_files, search_results=search_results, keyword=search_keyword)

if __name__ == '__main__':
    app.run(debug=True)

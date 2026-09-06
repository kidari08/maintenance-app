import os
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd

app = Flask(__name__)

# 업로드 파일 저장 폴더 설정
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    
    if request.method == 'POST':
        # 여러 파일 한 번에 받기
        uploaded_files = request.files.getlist('files')
        saved_names = []
        
        for file in uploaded_files:
            if file and file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                saved_names.append(file.filename)
        
        if saved_names:
            message = f"총 {len(saved_names)}개 파일 ({', '.join(saved_names)})이 성공적으로 업로드되었습니다."

    # 현재 서버에 업로드되어 있는 파일 목록 불러오기
    current_files = os.listdir(app.config['UPLOAD_FOLDER'])
    
    return render_template('index.html', message=message, current_files=current_files)

if __name__ == '__main__':
    app.run(debug=True)

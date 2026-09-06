import os
import pandas as pd
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 업로드 및 산출 데이터 보관 폴더 설정
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '업로드할 파일이 없습니다.'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '선택된 파일이 없습니다.'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    return jsonify({
        'message': f'[{file.filename}] 단가 데이터가 성공적으로 서버에 등록되었습니다.',
        'filename': file.filename
    })

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    item_name = data.get('item_name', '')
    quantity = float(data.get('quantity', 0))
    unit_price = float(data.get('unit_price', 0))
    
    total_price = quantity * unit_price
    
    return jsonify({
        'item_name': item_name,
        'quantity': quantity,
        'unit_price': unit_price,
        'total_price': total_price
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
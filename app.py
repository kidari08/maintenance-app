import os
import shutil
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

calculation_items = []

def search_in_excel_files(keyword):
    results = []
    if not keyword:
        return results
    
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.xls', '.xlsx'))]
    
    for filename in files:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 1. 일반적인 방식으로 시도 (.xlsx 및 일반 .xls)
        sheets_data = []
        try:
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name).fillna('')
                sheets_data.append(df)
        except Exception:
            # 2. 구형 .xls 포맷 대응 (xlrd 엔진 강제 사용)
            try:
                excel_file = pd.ExcelFile(file_path, engine='xlrd')
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd').fillna('')
                    sheets_data.append(df)
            except Exception:
                continue

        # 검색어 매칭 로직
        for df in sheets_data:
            for idx, row in df.iterrows():
                row_str = " ".join([str(val) for val in row.values])
                if keyword.lower() in row_str.lower():
                    vals = [str(v).strip() for v in row.values if str(v).strip() != '']
                    if len(vals) >= 2:
                        results.append({
                            'filename': filename,
                            'item_name': vals[0] if len(vals) > 0 else '품목',
                            'spec': vals[1] if len(vals) > 1 else '-',
                            'unit': vals[2] if len(vals) > 2 else '식',
                            'price': vals[3] if len(vals) > 3 else '0',
                            'raw_data': " | ".join(vals[:6])
                        })
                    if len(results) >= 50:
                        return results
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    global calculation_items
    message = None
    search_keyword = request.args.get('keyword', '')
    search_results = []
    
    if request.method == 'POST' and 'files' in request.files:
        uploaded_files = request.files.getlist('files')
        saved_names = []
        for file in uploaded_files:
            if file and file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                saved_names.append(file.filename)
        if saved_names:
            message = f"총 {len(saved_names)}개 파일이 서버에 등록되었습니다."

    if search_keyword:
        search_results = search_in_excel_files(search_keyword)

    total_amount = sum(item['total'] for item in calculation_items)
    current_files = os.listdir(app.config['UPLOAD_FOLDER'])
    
    return render_template('index.html', 
                           message=message, 
                           current_files=current_files, 
                           search_results=search_results, 
                           keyword=search_keyword,
                           calc_items=calculation_items,
                           total_amount=total_amount)

@app.route('/add_item', methods=['POST'])
def add_item():
    global calculation_items
    name = request.form.get('name', '품목명')
    spec = request.form.get('spec', '-')
    unit = request.form.get('unit', '식')
    try:
        price_str = request.form.get('price', '0').replace(',', '')
        price = float(price_str)
        qty = float(request.form.get('qty', 1))
    except ValueError:
        price = 0
        qty = 1
    
    total = price * qty
    calculation_items.append({
        'id': len(calculation_items) + 1,
        'name': name,
        'spec': spec,
        'unit': unit,
        'price': price,
        'qty': qty,
        'total': total
    })
    return redirect(url_for('index'))

@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    global calculation_items
    calculation_items = [item for item in calculation_items if item['id'] != item_id]
    return redirect(url_for('index'))

@app.route('/clear_files', methods=['POST'])
def clear_files():
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception:
            pass
    return redirect(url_for('index'))

@app.route('/delete_file/<filename>')
def delete_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

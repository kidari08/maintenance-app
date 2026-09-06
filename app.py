import os
import shutil
import re
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

calculation_items = []

def extract_smart_data(row_values):
    cleaned_vals = [str(v).strip() for v in row_values if str(v).strip() != '' and str(v).strip() != 'nan']
    if not cleaned_vals:
        return None

    item_name = cleaned_vals[0]
    spec = '-'
    unit = '식'
    price = 0

    numbers = []
    texts = []
    for val in cleaned_vals:
        num_str = re.sub(r'[^0-9.]', '', val)
        if num_str and val.replace(',', '').replace('.', '').isdigit():
            try:
                numbers.append(float(num_str))
            except ValueError:
                pass
        else:
            texts.append(val)

    if len(texts) > 0: item_name = texts[0]
    if len(texts) > 1: spec = texts[1]
    if len(texts) > 2: unit = texts[2]
    if numbers: price = numbers[-1]

    return {
        'item_name': item_name,
        'spec': spec,
        'unit': unit,
        'price': price,
        'raw_data': " | ".join(cleaned_vals)
    }

def read_file_safely(file_path):
    """표준 .xlsx 및 CSV, 텍스트 파일 읽기"""
    dfs = []
    # 1. .xlsx 파일 읽기
    try:
        excel_file = pd.ExcelFile(file_path)
        for sheet in excel_file.sheet_names:
            dfs.append(pd.read_excel(file_path, sheet_name=sheet).fillna(''))
        return dfs
    except Exception:
        pass

    # 2. CSV / 텍스트 기반 파일 읽기
    for enc in ['cp949', 'utf-8', 'euc-kr']:
        try:
            df = pd.read_csv(file_path, encoding=enc, on_bad_lines='skip', sep=None, engine='python').fillna('')
            dfs.append(df)
            return dfs
        except Exception:
            pass

    return dfs

def search_in_excel_files(keyword):
    results = []
    if not keyword:
        return results

    clean_keyword = re.sub(r'\s+', '', keyword).lower()
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.xls', '.xlsx', '.csv'))]

    for filename in files:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            dfs = read_file_safely(file_path)
            for df in dfs:
                for idx, row in df.iterrows():
                    row_str = "".join([str(val) for val in row.values])
                    clean_row_str = re.sub(r'\s+', '', row_str).lower()

                    if clean_keyword in clean_row_str:
                        parsed = extract_smart_data(row.values)
                        if parsed:
                            parsed['filename'] = filename
                            results.append(parsed)
                        if len(results) >= 100:
                            return results
        except Exception:
            continue
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

import os
import shutil
import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
DB_FILE = 'data.db'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

calculation_items = []

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            raw_data TEXT,
            item_name TEXT,
            spec TEXT,
            unit TEXT,
            price REAL,
            search_text TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def extract_smart_data(row_values):
    try:
        cleaned_vals = [str(v).strip() for v in row_values if str(v).strip() not in ['', 'nan', 'None']]
        if not cleaned_vals:
            return None

        item_name = cleaned_vals[0]
        spec = '-'
        unit = '식'
        price = 0.0

        numbers = []
        texts = []
        for val in cleaned_vals:
            num_str = re.sub(r'[^0-9.]', '', val)
            if num_str and val.replace(',', '').replace('.', '').strip().isdigit():
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

        raw_str = " | ".join(cleaned_vals[:6])
        search_str = re.sub(r'\s+', '', raw_str).lower()

        return {
            'item_name': item_name,
            'spec': spec,
            'unit': unit,
            'price': price,
            'raw_data': raw_str,
            'search_text': search_str
        }
    except Exception:
        return None

def process_and_save_to_db(filename, file_path):
    """모든 엔진 및 HTML 표 형태까지 완전 방어형 다중 파싱"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    dfs = []
    
    # 1. openpyxl (.xlsx)
    try:
        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
        for sheet in excel_file.sheet_names[:2]:
            df = pd.read_excel(file_path, sheet_name=sheet, engine='openpyxl', nrows=1000).fillna('')
            dfs.append(df)
    except Exception:
        pass

    # 2. xlrd (.xls 구형)
    if not dfs:
        try:
            excel_file = pd.ExcelFile(file_path, engine='xlrd')
            for sheet in excel_file.sheet_names[:2]:
                df = pd.read_excel(file_path, sheet_name=sheet, engine='xlrd', nrows=1000).fillna('')
                dfs.append(df)
        except Exception:
            pass

    # 3. HTML 표 형태 (.xlsx로 위장한 HTML)
    if not dfs:
        try:
            tables = pd.read_html(file_path)
            for df in tables[:2]:
                dfs.append(df.iloc[:1000].fillna(''))
        except Exception:
            pass

    # 4. CSV / 텍스트
    if not dfs:
        for enc in ['cp949', 'euc-kr', 'utf-8']:
            try:
                df = pd.read_csv(file_path, encoding=enc, on_bad_lines='skip', nrows=1000, engine='python').fillna('')
                dfs.append(df)
                if dfs: break
            except Exception:
                pass

    db_rows = []
    for df in dfs:
        for idx, row in df.iterrows():
            parsed = extract_smart_data(row.values)
            if parsed:
                db_rows.append((
                    filename,
                    parsed['raw_data'],
                    parsed['item_name'],
                    parsed['spec'],
                    parsed['unit'],
                    parsed['price'],
                    parsed['search_text']
                ))

    if db_rows:
        cursor.executemany('''
            INSERT INTO items (filename, raw_data, item_name, spec, unit, price, search_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', db_rows)

    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    global calculation_items
    message = None
    search_keyword = request.args.get('keyword', '').strip()
    search_results = []

    if request.method == 'POST' and 'files' in request.files:
        uploaded_files = request.files.getlist('files')
        saved_names = []
        for file in uploaded_files:
            if file and file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                try:
                    process_and_save_to_db(file.filename, file_path)
                except Exception:
                    pass
                saved_names.append(file.filename)
        if saved_names:
            message = f"총 {len(saved_names)}개 파일이 등록 및 DB화되었습니다."

    if search_keyword:
        clean_key = re.sub(r'\s+', '', search_keyword).lower()
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT filename, raw_data, item_name, spec, unit, price 
                FROM items 
                WHERE search_text LIKE ? 
                LIMIT 100
            ''', (f'%{clean_key}%',))
            
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                search_results.append({
                    'filename': r[0],
                    'raw_data': r[1],
                    'item_name': r[2],
                    'spec': r[3],
                    'unit': r[4],
                    'price': r[5]
                })
        except Exception:
            pass

    total_amount = sum(item['total'] for item in calculation_items)

    try:
        current_files = os.listdir(app.config['UPLOAD_FOLDER'])
    except Exception:
        current_files = []

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
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception:
            pass

    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception:
            pass
    init_db()

    return redirect(url_for('index'))

@app.route('/delete_file/<filename>')
def delete_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM items WHERE filename = ?', (filename,))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

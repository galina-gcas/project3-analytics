#!/usr/bin/env python3
"""
Веб-приложение для анализа Excel/CSV/PDF файлов
Позволяет загружать, просматривать и анализировать данные из различных форматов файлов
"""

import os
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile
import io
from datetime import datetime
import numpy as np
import pdfplumber
from dotenv import load_dotenv
from yandex_gpt_module import create_yandex_analyzer
from gigachat_module import create_gigachat_analyzer
from pdf_generator import create_pdf_report

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создание Flask приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size
app.config['MAX_CONTENT_PATH'] = 200 * 1024 * 1024  # 200MB max content path

# CORS настройки для GitHub Pages
from flask_cors import CORS
CORS(app, origins=['https://yourusername.github.io', 'http://localhost:5000'])

# Папка для загруженных файлов
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf'}

# Создаем папку для загрузок
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    """Проверяет, разрешен ли тип файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_dataframe_to_json_safe(df):
    """Преобразует DataFrame в JSON-безопасный формат"""
    df_clean = df.copy()
    
    for column in df_clean.columns:
        try:
            # Преобразуем numpy типы в Python типы
            if df_clean[column].dtype == 'int64':
                df_clean[column] = df_clean[column].astype('int')
            elif df_clean[column].dtype == 'float64':
                df_clean[column] = df_clean[column].astype('float')
            elif df_clean[column].dtype == 'bool':
                df_clean[column] = df_clean[column].astype('bool')
            elif 'datetime' in str(df_clean[column].dtype):
                df_clean[column] = df_clean[column].astype('str')
            elif df_clean[column].dtype == 'object':
                # Для object типов проверяем содержимое
                sample_values = df_clean[column].dropna().head(5)
                if len(sample_values) > 0:
                    # Пробуем преобразовать в числа
                    try:
                        pd.to_numeric(sample_values.iloc[0])
                        df_clean[column] = pd.to_numeric(df_clean[column], errors='coerce').astype('float')
                    except:
                        # Если не число, оставляем как строку
                        df_clean[column] = df_clean[column].astype('str')
                else:
                    df_clean[column] = df_clean[column].astype('str')
        except Exception as e:
            logger.warning(f"Ошибка преобразования столбца {column}: {e}")
            # В случае ошибки преобразуем в строки
            try:
                df_clean[column] = df_clean[column].astype('str')
            except:
                # Если и это не работает, заменяем на пустые строки
                df_clean[column] = ''
    
    # Заменяем NaN на None
    df_clean = df_clean.where(pd.notnull(df_clean), None)
    
    # Дополнительная проверка - заменяем все numpy типы и Timestamp на Python типы
    for column in df_clean.columns:
        try:
            # Используем .loc для избежания chained assignment
            for i in range(len(df_clean[column])):
                value = df_clean[column].iloc[i]
                if hasattr(value, 'item'):  # numpy scalar
                    df_clean.loc[df_clean.index[i], column] = value.item()
                elif isinstance(value, (np.integer, np.floating)):
                    df_clean.loc[df_clean.index[i], column] = value.item()
                elif hasattr(value, 'strftime'):  # Timestamp или datetime объект
                    df_clean.loc[df_clean.index[i], column] = str(value)
                elif isinstance(value, pd.Timestamp):  # pandas Timestamp
                    df_clean.loc[df_clean.index[i], column] = str(value)
        except Exception as e:
            logger.warning(f"Ошибка преобразования элементов столбца {column}: {e}")
    
    return df_clean

def detect_data_types(df):
    """Автоматически определяет типы данных в DataFrame"""
    data_types = {}
    
    for column in df.columns:
        # Пробуем определить тип данных
        if df[column].dtype in ['int64', 'float64']:
            data_types[column] = 'numeric'
        elif df[column].dtype == 'object':
            # Проверяем, является ли это датой
            try:
                # Берем несколько значений для проверки
                sample_values = df[column].dropna().head(3)
                if len(sample_values) > 0:
                    # Пробуем преобразовать в дату
                    pd.to_datetime(sample_values.iloc[0])
                    data_types[column] = 'datetime'
                else:
                    data_types[column] = 'text'
            except:
                # Проверяем, можно ли преобразовать в число
                try:
                    sample_values = df[column].dropna().head(3)
                    if len(sample_values) > 0:
                        pd.to_numeric(sample_values.iloc[0])
                        data_types[column] = 'numeric'
                    else:
                        data_types[column] = 'text'
                except:
                    data_types[column] = 'text'
        else:
            data_types[column] = 'text'
    
    return data_types

def get_basic_analytics(df):
    """Получает базовую аналитику по DataFrame"""
    analytics = {
        'total_rows': int(len(df)),
        'total_columns': int(len(df.columns)),
        'columns_info': {},
        'summary_stats': {}
    }
    
    # Общая статистика
    numeric_columns = [col for col in df.columns if df[col].dtype in ['int64', 'float64']]
    text_columns = [col for col in df.columns if df[col].dtype == 'object']
    
    analytics['summary_stats'] = {
        'numeric_columns': len(numeric_columns),
        'text_columns': len(text_columns),
        'total_missing_values': int(df.isnull().sum().sum()),
        'completeness_percentage': round((1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100, 2)
    }
    
    for column in df.columns:
        col_info = {
            'dtype': str(df[column].dtype),
            'non_null_count': int(df[column].count()),
            'null_count': int(df[column].isnull().sum()),
            'unique_count': int(df[column].nunique()),
            'completeness': round((df[column].count() / len(df)) * 100, 2)
        }
        
        # Для числовых столбцов добавляем статистику
        if df[column].dtype in ['int64', 'float64']:
            try:
                col_info.update({
                    'sum': float(df[column].sum()) if not df[column].isnull().all() else 0.0,
                    'mean': float(df[column].mean()) if not df[column].isnull().all() else 0.0,
                    'min': float(df[column].min()) if not df[column].isnull().all() else 0.0,
                    'max': float(df[column].max()) if not df[column].isnull().all() else 0.0,
                    'median': float(df[column].median()) if not df[column].isnull().all() else 0.0,
                    'std': float(df[column].std()) if not df[column].isnull().all() else 0.0
                })
            except Exception as e:
                logger.warning(f"Ошибка вычисления статистики для столбца {column}: {e}")
                col_info.update({
                    'sum': 0.0,
                    'mean': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'median': 0.0,
                    'std': 0.0
                })
        
        # Для текстовых столбцов добавляем информацию о самых частых значениях
        elif df[column].dtype == 'object':
            try:
                top_values = df[column].value_counts().head(5)
                col_info['top_values'] = {
                    str(k): int(v) for k, v in top_values.items()
                }
                # Добавляем информацию о количестве уникальных значений
                col_info['unique_values_count'] = int(df[column].nunique())
            except Exception as e:
                logger.warning(f"Ошибка анализа текстового столбца {column}: {e}")
                col_info['top_values'] = {}
                col_info['unique_values_count'] = 0
        
        analytics['columns_info'][column] = col_info
    
    return analytics

def create_charts(df, data_types):
    """Создает диаграммы на основе типов данных"""
    charts = []
    
    # Ищем числовые столбцы для bar chart
    numeric_columns = [col for col, dtype in data_types.items() if dtype == 'numeric']
    text_columns = [col for col, dtype in data_types.items() if dtype == 'text']
    datetime_columns = [col for col, dtype in data_types.items() if dtype == 'datetime']
    
    # 1. Bar chart: Топ марок автомобилей по количеству продаж
    if 'make' in text_columns and len(numeric_columns) > 0:
        try:
            # Группируем по маркам и считаем количество
            grouped_data = df.groupby('make').size().head(10)  # Топ 10 марок
            
            if len(grouped_data) > 0:
                x_values = [str(x) for x in grouped_data.index]
                y_values = [int(y) for y in grouped_data.values]
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=x_values,
                        y=y_values,
                        marker_color='#1e3a8a',
                        text=y_values,
                        textposition='auto'
                    )
                ])
                
                fig.update_layout(
                    title='Топ 10 марок автомобилей по количеству продаж',
                    xaxis_title='Марка автомобиля',
                    yaxis_title='Количество продаж',
                    font=dict(family="Georgia, serif"),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    height=400
                )
                
                charts.append({
                    'type': 'bar',
                    'title': 'Топ 10 марок автомобилей по количеству продаж',
                    'data': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                })
        except Exception as e:
            logger.warning(f"Ошибка создания bar chart марок: {e}")
    
    # 2. Line chart: Продажи по годам
    if 'year' in numeric_columns and 'sellingprice' in numeric_columns:
        try:
            # Группируем по годам и считаем сумму продаж
            grouped_data = df.groupby('year')['sellingprice'].sum().sort_index()
            
            if len(grouped_data) > 1:
                x_values = [str(x) for x in grouped_data.index]
                y_values = [float(y) for y in grouped_data.values]
                
                fig = go.Figure(data=[
                    go.Scatter(
                        x=x_values,
                        y=y_values,
                        mode='lines+markers',
                        line=dict(color='#1e3a8a', width=3),
                        marker=dict(size=8, color='#3b82f6'),
                        fill='tonexty'
                    )
                ])
                
                fig.update_layout(
                    title='Общая сумма продаж по годам',
                    xaxis_title='Год',
                    yaxis_title='Сумма продаж ($)',
                    font=dict(family="Georgia, serif"),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    height=400
                )
                
                charts.append({
                    'type': 'line',
                    'title': 'Общая сумма продаж по годам',
                    'data': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                })
        except Exception as e:
            logger.warning(f"Ошибка создания line chart по годам: {e}")
    
    return charts

def get_available_categories(df, data_types):
    """Возвращает доступные категории для создания диаграмм"""
    categories = {
        'text_columns': [col for col, dtype in data_types.items() if dtype == 'text'],
        'numeric_columns': [col for col, dtype in data_types.items() if dtype == 'numeric'],
        'datetime_columns': [col for col, dtype in data_types.items() if dtype == 'datetime']
    }
    
    # Добавляем информацию о количестве уникальных значений для каждой категории
    for col in categories['text_columns']:
        try:
            unique_count = df[col].nunique()
            # Преобразуем значения в строки для JSON-сериализации
            sample_values = df[col].value_counts().head(5)
            sample_dict = {}
            for key, value in sample_values.items():
                # Преобразуем ключ в строку, если это не базовый тип
                if hasattr(key, 'strftime'):  # Timestamp или datetime
                    sample_dict[str(key)] = int(value)
                elif isinstance(key, pd.Timestamp):  # pandas Timestamp
                    sample_dict[str(key)] = int(value)
                else:
                    sample_dict[str(key)] = int(value)
            
            categories[col] = {
                'type': 'text',
                'unique_count': int(unique_count),
                'sample_values': sample_dict
            }
        except Exception as e:
            logger.warning(f"Ошибка анализа категории {col}: {e}")
            categories[col] = {'type': 'text', 'unique_count': 0, 'sample_values': {}}
    
    return categories

def extract_table_from_pdf(filepath):
    """Извлекает первую таблицу из PDF файла"""
    try:
        with pdfplumber.open(filepath) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError("PDF файл не содержит страниц")
            
            # Ищем таблицы на первой странице
            first_page = pdf.pages[0]
            tables = first_page.extract_tables()
            
            if not tables:
                raise ValueError("На первой странице PDF не найдено таблиц")
            
            # Берем первую найденную таблицу
            table = tables[0]
            
            if not table or len(table) == 0:
                raise ValueError("Первая таблица в PDF пуста")
            
            # Преобразуем таблицу в DataFrame
            # Первая строка - заголовки
            if len(table) < 2:
                raise ValueError("Таблица должна содержать как минимум заголовки и одну строку данных")
            
            headers = table[0]
            data_rows = table[1:]
            
            # Создаем DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Очищаем данные
            df = df.dropna(how='all')  # Удаляем полностью пустые строки
            df = df.dropna(axis=1, how='all')  # Удаляем полностью пустые столбцы
            
            # Заменяем пустые значения на None
            df = df.where(pd.notnull(df), None)
            
            # Автоматически определяем типы данных для каждого столбца
            for column in df.columns:
                try:
                    # Пытаемся преобразовать в числовой тип
                    df[column] = pd.to_numeric(df[column], errors='coerce')
                except:
                    pass
                
                # Пытаемся преобразовать в дату для всех столбцов
                try:
                    # Пытаемся преобразовать в дату
                    df[column] = pd.to_datetime(df[column], errors='coerce')
                except:
                    pass
            
            logger.info(f"Извлечена таблица из PDF: {df.shape[0]} строк, {df.shape[1]} столбцов")
            logger.info(f"Столбцы: {list(df.columns)}")
            
            return df
            
    except Exception as e:
        logger.error(f"Ошибка извлечения таблицы из PDF: {e}")
        raise e

# Маршруты Flask
@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Загрузка и обработка Excel/CSV/PDF файла"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не выбран'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Неподдерживаемый тип файла. Разрешены: xlsx, xls, csv, pdf'}), 400
        
        # Сохраняем файл
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Читаем файл с оптимизацией для больших файлов
        try:
            if filename.endswith('.pdf'):
                # Для PDF файлов извлекаем таблицу
                df = extract_table_from_pdf(filepath)
            elif filename.endswith('.csv'):
                # Для CSV файлов используем chunking для больших файлов
                file_size = os.path.getsize(filepath)
                if file_size > 10 * 1024 * 1024:  # Если файл больше 10MB
                    # Читаем только первые 10000 строк для предварительного анализа
                    df = pd.read_csv(filepath, encoding='utf-8', nrows=10000)
                    logger.info(f"Файл большой ({file_size / 1024 / 1024:.1f}MB), читаем первые 10000 строк")
                else:
                    df = pd.read_csv(filepath, encoding='utf-8')
            else:
                # Для Excel файлов
                file_size = os.path.getsize(filepath)
                if file_size > 10 * 1024 * 1024:  # Если файл больше 10MB
                    # Читаем только первые 10000 строк
                    df = pd.read_excel(filepath, nrows=10000)
                    logger.info(f"Файл большой ({file_size / 1024 / 1024:.1f}MB), читаем первые 10000 строк")
                else:
                    df = pd.read_excel(filepath)
        except Exception as e:
            # Пробуем другие кодировки для CSV
            if filename.endswith('.csv'):
                try:
                    file_size = os.path.getsize(filepath)
                    if file_size > 10 * 1024 * 1024:
                        df = pd.read_csv(filepath, encoding='cp1251', nrows=10000)
                    else:
                        df = pd.read_csv(filepath, encoding='cp1251')
                except:
                    try:
                        file_size = os.path.getsize(filepath)
                        if file_size > 10 * 1024 * 1024:
                            df = pd.read_csv(filepath, encoding='latin-1', nrows=10000)
                        else:
                            df = pd.read_csv(filepath, encoding='latin-1')
                    except:
                        raise e
            else:
                raise e
        
        # Очищаем данные
        df = df.dropna(how='all')  # Удаляем полностью пустые строки
        df = df.dropna(axis=1, how='all')  # Удаляем полностью пустые столбцы
        
        # Заменяем NaN значения на None для корректной JSON сериализации
        df = df.where(pd.notnull(df), None)
        
        # Дополнительная обработка пустых значений
        df = df.replace(['', ' ', '  ', '   '], None)  # Заменяем пустые строки на None
        df = df.replace(['nan', 'NaN', 'NAN'], None)  # Заменяем строковые 'nan' на None
        
        # Логируем информацию о типах данных для отладки
        logger.info(f"Типы данных в DataFrame: {dict(df.dtypes)}")
        logger.info(f"Размер DataFrame: {df.shape}")
        
        # Определяем типы данных
        data_types = detect_data_types(df)
        
        # Получаем базовую аналитику
        analytics = get_basic_analytics(df)
        
        # Создаем диаграммы
        charts = create_charts(df, data_types)
        
        # Получаем доступные категории для диаграмм
        categories = get_available_categories(df, data_types)
        
        # Подготавливаем первые 100 строк для отображения
        df_display = df.head(100)
        
        # Конвертируем DataFrame в JSON-безопасный формат
        df_display_clean = convert_dataframe_to_json_safe(df_display)
        data_json = df_display_clean.to_json(orient='records', date_format='iso')
        
        # Получаем размер файла
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'data': json.loads(data_json),
            'columns': list(df.columns),
            'total_rows': len(df),
            'data_types': data_types,
            'analytics': analytics,
            'charts': charts,
            'categories': categories,
            'has_more_data': len(df) > 100,
            'file_size_mb': round(file_size_mb, 2),
            'is_large_file': file_size > 10 * 1024 * 1024
        })
        
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 500

@app.route('/load_more', methods=['POST'])
def load_more_data():
    """Загружает дополнительные строки данных"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        start_row = data.get('start_row', 0)
        rows_count = data.get('rows_count', 100)
        
        if not filename:
            return jsonify({'error': 'Имя файла не указано'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Файл не найден'}), 404
        
        # Читаем файл
        if filename.endswith('.pdf'):
            df = extract_table_from_pdf(filepath)
        elif filename.endswith('.csv'):
            df = pd.read_csv(filepath, encoding='utf-8')
        else:
            df = pd.read_excel(filepath)
        
        # Очищаем данные
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        
        # Заменяем NaN значения на None для корректной JSON сериализации
        df = df.where(pd.notnull(df), None)
        
        # Логируем информацию о типах данных для отладки
        logger.info(f"Типы данных в load_more: {dict(df.dtypes)}")
        
        # Получаем нужный диапазон строк
        end_row = min(start_row + rows_count, len(df))
        df_slice = df.iloc[start_row:end_row]
        
        # Конвертируем в JSON-безопасный формат
        df_slice_clean = convert_dataframe_to_json_safe(df_slice)
        data_json = df_slice_clean.to_json(orient='records', date_format='iso')
        
        return jsonify({
            'success': True,
            'data': json.loads(data_json),
            'start_row': start_row,
            'end_row': end_row,
            'has_more_data': end_row < len(df)
        })
        
    except Exception as e:
        logger.error(f"Ошибка загрузки дополнительных данных: {e}")
        return jsonify({'error': f'Ошибка загрузки данных: {str(e)}'}), 500

@app.route('/create_chart', methods=['POST'])
def create_custom_chart():
    """Создает диаграмму по выбранной категории"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        category = data.get('category')
        chart_type = data.get('chart_type', 'bar')
        
        if not filename or not category:
            return jsonify({'error': 'Не указаны обязательные параметры'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Файл не найден'}), 404
        
        # Читаем файл
        if filename.endswith('.pdf'):
            df = extract_table_from_pdf(filepath)
        elif filename.endswith('.csv'):
            df = pd.read_csv(filepath, encoding='utf-8')
        else:
            df = pd.read_excel(filepath)
        
        # Очищаем данные
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        df = df.where(pd.notnull(df), None)
        
        # Определяем типы данных
        data_types = detect_data_types(df)
        
        # Создаем диаграмму
        if chart_type == 'bar':
            # Bar chart: количество по категории
            try:
                grouped_data = df.groupby(category).size().head(15)  # Топ 15
                
                if len(grouped_data) > 0:
                    x_values = [str(x) for x in grouped_data.index]
                    y_values = [int(y) for y in grouped_data.values]
                    
                    fig = go.Figure(data=[
                        go.Bar(
                            x=x_values,
                            y=y_values,
                            marker_color='#1e3a8a',
                            text=y_values,
                            textposition='auto'
                        )
                    ])
                    
                    fig.update_layout(
                        title=f'Распределение по {category}',
                        xaxis_title=category,
                        yaxis_title='Количество',
                        font=dict(family="Georgia, serif"),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        height=400
                    )
                    
                    chart_data = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                    
                    return jsonify({
                        'success': True,
                        'chart': {
                            'type': 'bar',
                            'title': f'Распределение по {category}',
                            'data': chart_data
                        }
                    })
                else:
                    return jsonify({'error': 'Недостаточно данных для создания диаграммы'}), 400
                    
            except Exception as e:
                logger.warning(f"Ошибка создания bar chart: {e}")
                return jsonify({'error': f'Ошибка создания диаграммы: {str(e)}'}), 500
        
        elif chart_type == 'line':
            # Line chart: временной ряд (если есть числовые столбцы)
            numeric_columns = [col for col, dtype in data_types.items() if dtype == 'numeric']
            if len(numeric_columns) > 0:
                try:
                    value_col = numeric_columns[0]  # Берем первый числовой столбец
                    grouped_data = df.groupby(category)[value_col].sum().sort_index()
                    
                    if len(grouped_data) > 1:
                        x_values = [str(x) for x in grouped_data.index]
                        y_values = [float(y) for y in grouped_data.values]
                        
                        fig = go.Figure(data=[
                            go.Scatter(
                                x=x_values,
                                y=y_values,
                                mode='lines+markers',
                                line=dict(color='#1e3a8a', width=3),
                                marker=dict(size=8, color='#3b82f6')
                            )
                        ])
                        
                        fig.update_layout(
                            title=f'{value_col} по {category}',
                            xaxis_title=category,
                            yaxis_title=value_col,
                            font=dict(family="Georgia, serif"),
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            height=400
                        )
                        
                        chart_data = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                        
                        return jsonify({
                            'success': True,
                            'chart': {
                                'type': 'line',
                                'title': f'{value_col} по {category}',
                                'data': chart_data
                            }
                        })
                    else:
                        return jsonify({'error': 'Недостаточно данных для создания линейной диаграммы'}), 400
                        
                except Exception as e:
                    logger.warning(f"Ошибка создания line chart: {e}")
                    return jsonify({'error': f'Ошибка создания диаграммы: {str(e)}'}), 500
            else:
                return jsonify({'error': 'Нет числовых столбцов для линейной диаграммы'}), 400
        
        else:
            return jsonify({'error': 'Неподдерживаемый тип диаграммы'}), 400
            
    except Exception as e:
        logger.error(f"Ошибка создания диаграммы: {e}")
        return jsonify({'error': f'Ошибка создания диаграммы: {str(e)}'}), 500

@app.route('/yandex_analysis', methods=['POST'])
def yandex_analysis():
    """Анализ данных с помощью Яндекс.GPT"""
    try:
        print("🤖 [YANDEX] Начало анализа через Яндекс.GPT")
        data = request.get_json()
        filename = data.get('filename')
        
        print(f"📄 [YANDEX] Запрошен файл для анализа: {filename}")
        
        if not filename:
            print("❌ [YANDEX] Ошибка: не указано имя файла")
            return jsonify({'error': 'Имя файла не указано'}), 400
        
        # Проверяем, что файл существует
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            print(f"❌ [YANDEX] Ошибка: файл не найден - {filepath}")
            return jsonify({'error': 'Файл не найден'}), 404
        
        print(f"✅ [YANDEX] Файл найден: {filepath}")
        
        # Читаем файл для получения первых 15 строк
        try:
            if filename.endswith('.pdf'):
                print("📊 [YANDEX] Читаем PDF файл...")
                df = extract_table_from_pdf(filepath)
            elif filename.endswith('.csv'):
                print("📊 [YANDEX] Читаем CSV файл...")
                df = pd.read_csv(filepath, encoding='utf-8')
            else:
                print("📊 [YANDEX] Читаем Excel файл...")
                df = pd.read_excel(filepath)
        except Exception as e:
            print(f"⚠️ [YANDEX] Ошибка чтения с UTF-8, пробуем другие кодировки...")
            # Пробуем другие кодировки для CSV
            if filename.endswith('.csv'):
                try:
                    print("📊 [YANDEX] Пробуем кодировку cp1251...")
                    df = pd.read_csv(filepath, encoding='cp1251')
                except:
                    try:
                        print("📊 [YANDEX] Пробуем кодировку latin-1...")
                        df = pd.read_csv(filepath, encoding='latin-1')
                    except:
                        print(f"❌ [YANDEX] Критическая ошибка чтения файла: {str(e)}")
                        return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 500
            else:
                print(f"❌ [YANDEX] Критическая ошибка чтения файла: {str(e)}")
                return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 500
        
        print(f"📈 [YANDEX] Данные загружены: {len(df)} строк, {len(df.columns)} столбцов")
        
        # Очищаем данные
        print("🧹 [YANDEX] Очищаем данные...")
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        df = df.where(pd.notnull(df), None)
        
        # Берем первые 15 строк для анализа
        df_sample = df.head(15)
        print(f"📋 [YANDEX] Подготовлено {len(df_sample)} строк для анализа")
        
        # Конвертируем в JSON-безопасный формат
        df_sample_clean = convert_dataframe_to_json_safe(df_sample)
        table_data = df_sample_clean.to_dict('records')
        print(f"🔄 [YANDEX] Данные конвертированы в JSON формат")
        
        # Создаем анализатор Яндекс.GPT
        print("🔧 [YANDEX] Инициализируем анализатор Яндекс.GPT...")
        analyzer = create_yandex_analyzer()
        if not analyzer:
            print("❌ [YANDEX] Ошибка: не удалось инициализировать анализатор")
            return jsonify({
                'error': 'Не удалось инициализировать анализатор Яндекс.GPT. Проверьте настройки в .env файле.'
            }), 500
        
        print("✅ [YANDEX] Анализатор Яндекс.GPT инициализирован")
        
        # Выполняем анализ
        print("🚀 [YANDEX] Запускаем анализ через Яндекс.GPT...")
        logger.info(f"Запускаем анализ файла {filename} через Яндекс.GPT")
        analysis_result = analyzer.analyze_table_data(table_data, filename)
        
        if analysis_result['success']:
            analysis_length = len(analysis_result['analysis'])
            print(f"✅ [YANDEX] Анализ завершён успешно!")
            print(f"📊 [YANDEX] Длина ответа: {analysis_length} символов")
            print(f"🤖 [YANDEX] Модель: {analysis_result['model']}")
            return jsonify({
                'success': True,
                'analysis': {
                    'status': 'completed',
                    'message': 'Анализ завершен успешно',
                    'content': analysis_result['analysis'],
                    'model': analysis_result['model'],
                    'filename': analysis_result['filename']
                }
            })
        else:
            print(f"❌ [YANDEX] Ошибка анализа: {analysis_result['error']}")
            return jsonify({
                'success': False,
                'error': analysis_result['error']
            }), 500
        
    except Exception as e:
        print(f"❌ [YANDEX] Критическая ошибка: {str(e)}")
        import traceback
        print(f"🔍 [YANDEX] Трассировка ошибки:\n{traceback.format_exc()}")
        logger.error(f"Ошибка Yandex анализа: {e}")
        return jsonify({'error': f'Ошибка анализа: {str(e)}'}), 500

@app.route('/gigachat_analysis', methods=['POST'])
def gigachat_analysis():
    """Анализ данных с помощью GigaChat"""
    try:
        print("🤖 [GIGACHAT] Начало анализа через GigaChat")
        data = request.get_json()
        filename = data.get('filename')
        
        print(f"📄 [GIGACHAT] Запрошен файл для анализа: {filename}")
        
        if not filename:
            print("❌ [GIGACHAT] Ошибка: не указано имя файла")
            return jsonify({'error': 'Имя файла не указано'}), 400
        
        # Проверяем, что файл существует
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            print(f"❌ [GIGACHAT] Ошибка: файл не найден - {filepath}")
            return jsonify({'error': 'Файл не найден'}), 404
        
        print(f"✅ [GIGACHAT] Файл найден: {filepath}")
        
        # Читаем файл для получения первых 15 строк
        try:
            if filename.endswith('.pdf'):
                print("📊 [GIGACHAT] Читаем PDF файл...")
                df = extract_table_from_pdf(filepath)
            elif filename.endswith('.csv'):
                print("📊 [GIGACHAT] Читаем CSV файл...")
                df = pd.read_csv(filepath, encoding='utf-8')
            else:
                print("📊 [GIGACHAT] Читаем Excel файл...")
                df = pd.read_excel(filepath)
        except Exception as e:
            print(f"⚠️ [GIGACHAT] Ошибка чтения с UTF-8, пробуем другие кодировки...")
            # Пробуем другие кодировки для CSV
            if filename.endswith('.csv'):
                try:
                    print("📊 [GIGACHAT] Пробуем кодировку cp1251...")
                    df = pd.read_csv(filepath, encoding='cp1251')
                except:
                    try:
                        print("📊 [GIGACHAT] Пробуем кодировку latin-1...")
                        df = pd.read_csv(filepath, encoding='latin-1')
                    except:
                        print(f"❌ [GIGACHAT] Критическая ошибка чтения файла: {str(e)}")
                        return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 500
            else:
                print(f"❌ [GIGACHAT] Критическая ошибка чтения файла: {str(e)}")
                return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 500
        
        print(f"📈 [GIGACHAT] Данные загружены: {len(df)} строк, {len(df.columns)} столбцов")
        
        # Очищаем данные
        print("🧹 [GIGACHAT] Очищаем данные...")
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        df = df.where(pd.notnull(df), None)
        
        # Берем первые 15 строк для анализа
        df_sample = df.head(15)
        print(f"📋 [GIGACHAT] Подготовлено {len(df_sample)} строк для анализа")
        
        # Конвертируем в JSON-безопасный формат
        df_sample_clean = convert_dataframe_to_json_safe(df_sample)
        table_data = df_sample_clean.to_dict('records')
        print(f"🔄 [GIGACHAT] Данные конвертированы в JSON формат")
        
        # Создаем анализатор GigaChat
        print("🔧 [GIGACHAT] Инициализируем анализатор GigaChat...")
        analyzer = create_gigachat_analyzer()
        if not analyzer:
            print("❌ [GIGACHAT] Ошибка: не удалось инициализировать анализатор")
            return jsonify({
                'error': 'Не удалось инициализировать анализатор GigaChat. Проверьте настройки в .env файле.'
            }), 500
        
        print("✅ [GIGACHAT] Анализатор GigaChat инициализирован")
        
        # Выполняем анализ
        print("🚀 [GIGACHAT] Запускаем анализ через GigaChat...")
        logger.info(f"Запускаем анализ файла {filename} через GigaChat")
        analysis_result = analyzer.analyze_table_data(table_data, filename)
        
        if analysis_result['success']:
            analysis_length = len(analysis_result['analysis'])
            print(f"✅ [GIGACHAT] Анализ завершён успешно!")
            print(f"📊 [GIGACHAT] Длина ответа: {analysis_length} символов")
            print(f"🤖 [GIGACHAT] Модель: {analysis_result['model']}")
            return jsonify({
                'success': True,
                'analysis': {
                    'status': 'completed',
                    'message': 'Анализ завершен успешно',
                    'content': analysis_result['analysis'],
                    'model': analysis_result['model'],
                    'filename': analysis_result['filename']
                }
            })
        else:
            print(f"❌ [GIGACHAT] Ошибка анализа: {analysis_result['error']}")
            return jsonify({
                'success': False,
                'error': analysis_result['error']
            }), 500
        
    except Exception as e:
        print(f"❌ [GIGACHAT] Критическая ошибка: {str(e)}")
        import traceback
        print(f"🔍 [GIGACHAT] Трассировка ошибки:\n{traceback.format_exc()}")
        logger.error(f"Ошибка GigaChat анализа: {e}")
        return jsonify({'error': f'Ошибка анализа: {str(e)}'}), 500

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """Генерация PDF отчета на сервере"""
    try:
        print("🔄 [PDF] Начало генерации PDF отчёта")
        data = request.get_json()
        filename = data.get('filename')
        yandex_analysis = data.get('yandex_analysis', '')
        gigachat_analysis = data.get('gigachat_analysis', '')
        
        print(f"📄 [PDF] Запрошен файл: {filename}")
        print(f"🤖 [PDF] Яндекс.GPT анализ получен: {'Да' if yandex_analysis else 'Нет'}")
        print(f"🤖 [PDF] GigaChat анализ получен: {'Да' if gigachat_analysis else 'Нет'}")
        
        if not filename:
            print("❌ [PDF] Ошибка: не указано имя файла")
            return jsonify({'error': 'Имя файла не указано'}), 400
        
        # Проверяем, что файл существует
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            print(f"❌ [PDF] Ошибка: файл не найден - {filepath}")
            return jsonify({'error': 'Файл не найден'}), 404
        
        print(f"✅ [PDF] Файл найден: {filepath}")
        
        # Читаем файл
        try:
            if filename.endswith('.pdf'):
                print("📊 [PDF] Читаем PDF файл...")
                df = extract_table_from_pdf(filepath)
            elif filename.endswith('.csv'):
                print("📊 [PDF] Читаем CSV файл...")
                df = pd.read_csv(filepath, encoding='utf-8')
            else:
                print("📊 [PDF] Читаем Excel файл...")
                df = pd.read_excel(filepath)
        except Exception as e:
            print(f"⚠️ [PDF] Ошибка чтения с UTF-8, пробуем другие кодировки...")
            # Пробуем другие кодировки для CSV
            if filename.endswith('.csv'):
                try:
                    print("📊 [PDF] Пробуем кодировку cp1251...")
                    df = pd.read_csv(filepath, encoding='cp1251')
                except:
                    try:
                        print("📊 [PDF] Пробуем кодировку latin-1...")
                        df = pd.read_csv(filepath, encoding='latin-1')
                    except:
                        print(f"❌ [PDF] Критическая ошибка чтения файла: {str(e)}")
                        return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 500
            else:
                print(f"❌ [PDF] Критическая ошибка чтения файла: {str(e)}")
                return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 500
        
        print(f"📈 [PDF] Данные загружены: {len(df)} строк, {len(df.columns)} столбцов")
        
        # Очищаем данные
        print("🧹 [PDF] Очищаем данные...")
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        df = df.where(pd.notnull(df), None)
        df = df.replace(['', ' ', '  ', '   '], None)  # Заменяем пустые строки на None
        df = df.replace(['nan', 'NaN', 'NAN'], None)  # Заменяем строковые 'nan' на None
        
        print(f"✨ [PDF] Данные очищены: {len(df)} строк, {len(df.columns)} столбцов")
        
        # Получаем аналитику
        print("📊 [PDF] Генерируем аналитику...")
        data_types = detect_data_types(df)
        analytics = get_basic_analytics(df)
        print(f"✅ [PDF] Аналитика готова: {len(analytics)} элементов")
        
        # Подготавливаем данные для PDF
        df_sample = df.head(50)  # Берем больше строк для PDF
        df_sample_clean = convert_dataframe_to_json_safe(df_sample)
        table_data = df_sample_clean.to_dict('records')
        print(f"📋 [PDF] Подготовлено {len(table_data)} строк для таблицы в PDF")
        
        # Получаем AI анализы если есть
        ai_analyses = {}
        if yandex_analysis and yandex_analysis != 'Здесь появится вывод от нейросети':
            ai_analyses['yandex'] = yandex_analysis
            print(f"🤖 [PDF] Яндекс.GPT анализ включён в PDF: {len(yandex_analysis)} символов")
        if gigachat_analysis and gigachat_analysis != 'Здесь появится вывод от нейросети':
            ai_analyses['gigachat'] = gigachat_analysis
            print(f"🤖 [PDF] GigaChat анализ включён в PDF: {len(gigachat_analysis)} символов")
        
        if not ai_analyses:
            print("🤖 [PDF] AI анализы не включены в PDF")
        
        # Подготавливаем данные для PDF генератора
        pdf_data = {
            'filename': filename,
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'table_data': table_data,
            'analytics': analytics,
            'ai_analyses': ai_analyses
        }
        
        # Создаем временный файл для PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"analytics_report_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
        
        print(f"📄 [PDF] Создаём PDF файл: {pdf_filename}")
        print(f"📁 [PDF] Путь сохранения: {pdf_path}")
        
        # Генерируем PDF
        print("🔄 [PDF] Запускаем генерацию PDF...")
        success = create_pdf_report(pdf_data, pdf_path)
        
        if success:
            file_size = os.path.getsize(pdf_path)
            print(f"✅ [PDF] PDF отчёт успешно создан!")
            print(f"📊 [PDF] Размер файла: {file_size} байт")
            print(f"📄 [PDF] Имя файла: {pdf_filename}")
            return jsonify({
                'success': True,
                'pdf_filename': pdf_filename,
                'message': 'PDF отчет успешно создан'
            })
        else:
            print("❌ [PDF] Ошибка создания PDF отчёта")
            return jsonify({
                'success': False,
                'error': 'Ошибка создания PDF отчета'
            }), 500
        
    except Exception as e:
        print(f"❌ [PDF] Критическая ошибка: {str(e)}")
        import traceback
        print(f"🔍 [PDF] Трассировка ошибки:\n{traceback.format_exc()}")
        logger.error(f"Ошибка генерации PDF: {e}")
        return jsonify({'error': f'Ошибка генерации PDF: {str(e)}'}), 500

@app.route('/download_pdf/<filename>')
def download_pdf(filename):
    """Скачивание PDF файла"""
    try:
        print(f"📥 [DOWNLOAD] Запрос на скачивание PDF: {filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"✅ [DOWNLOAD] PDF файл найден: {filepath}")
            print(f"📊 [DOWNLOAD] Размер файла: {file_size} байт")
            print(f"📤 [DOWNLOAD] Отправляем файл клиенту...")
            
            response = send_file(filepath, as_attachment=True, download_name=filename)
            print(f"✅ [DOWNLOAD] Файл успешно отправлен клиенту")
            return response
        else:
            print(f"❌ [DOWNLOAD] PDF файл не найден: {filepath}")
            return jsonify({'error': 'PDF файл не найден'}), 404
    except Exception as e:
        print(f"❌ [DOWNLOAD] Ошибка скачивания PDF: {str(e)}")
        import traceback
        print(f"🔍 [DOWNLOAD] Трассировка ошибки:\n{traceback.format_exc()}")
        logger.error(f"Ошибка скачивания PDF: {e}")
        return jsonify({'error': f'Ошибка скачивания: {str(e)}'}), 500

if __name__ == '__main__':
    # Создаем необходимые папки
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    
    # Определяем порт для Render
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("Запуск веб-приложения для анализа Excel/CSV/PDF файлов...")
    
    # Запуск в зависимости от окружения
    if os.environ.get('RENDER'):
        # Продакшен режим для Render
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Локальная разработка
        app.run(debug=True, host='0.0.0.0', port=port)

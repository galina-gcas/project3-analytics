#!/usr/bin/env python3
"""
Модуль для генерации PDF отчетов с поддержкой русского языка
Использует ReportLab для создания качественных PDF документов
"""

import os
import io
import math
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Используем non-interactive backend

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

logger = logging.getLogger(__name__)

class PDFReportGenerator:
    """Класс для генерации PDF отчетов"""
    
    def __init__(self):
        """Инициализация генератора PDF"""
        self.styles = getSampleStyleSheet()
        self._setup_fonts()
        self._setup_custom_styles()
    
    def _setup_fonts(self):
        """Настройка шрифтов для поддержки русского языка"""
        try:
            # Пытаемся зарегистрировать системные шрифты
            # Для Windows
            if os.name == 'nt':
                font_paths = [
                    'C:/Windows/Fonts/arial.ttf',
                    'C:/Windows/Fonts/calibri.ttf',
                    'C:/Windows/Fonts/times.ttf'
                ]
            # Для Linux
            else:
                font_paths = [
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                    '/System/Library/Fonts/Arial.ttf'  # macOS
                ]
            
            # Регистрируем первый доступный шрифт
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('CustomFont', font_path))
                        self.font_name = 'CustomFont'
                        logger.info(f"Зарегистрирован шрифт: {font_path}")
                        break
                    except Exception as e:
                        logger.warning(f"Не удалось зарегистрировать шрифт {font_path}: {e}")
                        continue
            
            # Если не удалось зарегистрировать кастомный шрифт, используем стандартный
            if not hasattr(self, 'font_name'):
                self.font_name = 'Helvetica'
                logger.warning("Используется стандартный шрифт Helvetica (возможны проблемы с кириллицей)")
                
        except Exception as e:
            logger.error(f"Ошибка настройки шрифтов: {e}")
            self.font_name = 'Helvetica'
    
    def _setup_custom_styles(self):
        """Настройка пользовательских стилей"""
        # Заголовок отчета
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=self.font_name
        ))
        
        # Заголовки разделов
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            fontName=self.font_name,
            textColor=colors.darkblue
        ))
        
        # Обычный текст
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            fontName=self.font_name
        ))
        
        # Подзаголовки разделов
        self.styles.add(ParagraphStyle(
            name='SubsectionTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            fontName=self.font_name,
            textColor=colors.darkgreen
        ))
        
        # Текст AI анализа
        self.styles.add(ParagraphStyle(
            name='AIAnalysis',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=4,
            fontName=self.font_name,
            leftIndent=10,
            rightIndent=10
        ))
    
    def _convert_markdown_to_reportlab(self, text: str) -> List:
        """
        Конвертирует Markdown текст в элементы ReportLab
        
        Args:
            text: Markdown текст
            
        Returns:
            Список элементов ReportLab
        """
        elements = []
        
        if not text or not text.strip():
            return elements
        
        # Разбиваем текст на строки
        lines = text.split('\n')
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            # Обрабатываем заголовки
            if line.startswith('###'):
                # Заголовок 3-го уровня
                if current_paragraph:
                    elements.append(Paragraph(' '.join(current_paragraph), self.styles['AIAnalysis']))
                    elements.append(Spacer(1, 4))
                    current_paragraph = []
                
                header_text = line[3:].strip()
                elements.append(Paragraph(f"<b>{header_text}</b>", self.styles['AIAnalysis']))
                elements.append(Spacer(1, 4))
                
            elif line.startswith('##'):
                # Заголовок 2-го уровня
                if current_paragraph:
                    elements.append(Paragraph(' '.join(current_paragraph), self.styles['AIAnalysis']))
                    elements.append(Spacer(1, 4))
                    current_paragraph = []
                
                header_text = line[2:].strip()
                elements.append(Paragraph(f"<b><font size='12'>{header_text}</font></b>", self.styles['AIAnalysis']))
                elements.append(Spacer(1, 6))
                
            elif line.startswith('#'):
                # Заголовок 1-го уровня
                if current_paragraph:
                    elements.append(Paragraph(' '.join(current_paragraph), self.styles['AIAnalysis']))
                    elements.append(Spacer(1, 4))
                    current_paragraph = []
                
                header_text = line[1:].strip()
                elements.append(Paragraph(f"<b><font size='14'>{header_text}</font></b>", self.styles['AIAnalysis']))
                elements.append(Spacer(1, 8))
                
            elif line.startswith('---') or line.startswith('***'):
                # Горизонтальная линия
                if current_paragraph:
                    elements.append(Paragraph(' '.join(current_paragraph), self.styles['AIAnalysis']))
                    elements.append(Spacer(1, 4))
                    current_paragraph = []
                
                elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey))
                elements.append(Spacer(1, 6))
                
            elif line.startswith('- ') or line.startswith('* '):
                # Список
                if current_paragraph:
                    elements.append(Paragraph(' '.join(current_paragraph), self.styles['AIAnalysis']))
                    elements.append(Spacer(1, 4))
                    current_paragraph = []
                
                list_item = line[2:].strip()
                # Обрабатываем жирный текст в списке
                list_item = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', list_item)
                list_item = re.sub(r'\*(.*?)\*', r'<i>\1</i>', list_item)
                elements.append(Paragraph(f"• {list_item}", self.styles['AIAnalysis']))
                elements.append(Spacer(1, 2))
                
            elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. ') or line.startswith('4. ') or line.startswith('5. '):
                # Нумерованный список
                if current_paragraph:
                    elements.append(Paragraph(' '.join(current_paragraph), self.styles['AIAnalysis']))
                    elements.append(Spacer(1, 4))
                    current_paragraph = []
                
                list_item = line[3:].strip()
                # Обрабатываем жирный текст в списке
                list_item = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', list_item)
                list_item = re.sub(r'\*(.*?)\*', r'<i>\1</i>', list_item)
                elements.append(Paragraph(f"{line[:2]} {list_item}", self.styles['AIAnalysis']))
                elements.append(Spacer(1, 2))
                
            elif line == '':
                # Пустая строка - завершаем текущий абзац
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    # Обрабатываем жирный и курсивный текст
                    paragraph_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', paragraph_text)
                    paragraph_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', paragraph_text)
                    elements.append(Paragraph(paragraph_text, self.styles['AIAnalysis']))
                    elements.append(Spacer(1, 4))
                    current_paragraph = []
                
            else:
                # Обычный текст
                current_paragraph.append(line)
        
        # Обрабатываем последний абзац
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            # Обрабатываем жирный и курсивный текст
            paragraph_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', paragraph_text)
            paragraph_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', paragraph_text)
            elements.append(Paragraph(paragraph_text, self.styles['AIAnalysis']))
            elements.append(Spacer(1, 4))
        
        return elements
    
    def generate_report(self, data: Dict[str, Any], output_path: str) -> bool:
        """
        Генерирует PDF отчет
        
        Args:
            data: Словарь с данными для отчета
            output_path: Путь для сохранения PDF файла
            
        Returns:
            True если отчет создан успешно, False иначе
        """
        try:
            # Создаем PDF документ
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            # Список элементов для добавления в PDF
            story = []
            
            # Заголовок отчета
            story.append(Paragraph("📊 Аналитический отчет", self.styles['ReportTitle']))
            
            # Информация о файле и дате
            file_info = f"<b>Файл:</b> {data.get('filename', 'Не указан')}<br/>"
            file_info += f"<b>Дата создания:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}<br/>"
            file_info += f"<b>Всего строк:</b> {data.get('total_rows', 0):,}<br/>"
            file_info += f"<b>Всего столбцов:</b> {data.get('total_columns', 0)}"
            
            # Добавляем информацию о заполненности данных
            if data.get('analytics', {}).get('summary_stats', {}).get('completeness_percentage'):
                completeness = data['analytics']['summary_stats']['completeness_percentage']
                file_info += f"<br/><b>Заполненность данных:</b> {completeness}%"
            
            story.append(Paragraph(file_info, self.styles['NormalText']))
            story.append(Spacer(1, 15))
            story.append(HRFlowable(width="100%", thickness=2, lineCap='round', color=colors.HexColor('#1e3a8a')))
            story.append(Spacer(1, 15))
            
            # Добавляем таблицу данных
            if data.get('table_data'):
                story.extend(self._add_data_table(data['table_data'], data.get('columns', [])))
            
            # Добавляем аналитику
            if data.get('analytics'):
                story.extend(self._add_analytics_section(data['analytics']))
            
            # Добавляем AI анализы
            if data.get('ai_analyses'):
                story.extend(self._add_ai_analysis_section(data['ai_analyses']))
            
            # Строим PDF
            doc.build(story)
            logger.info(f"PDF отчет успешно создан: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания PDF отчета: {e}")
            return False
    
    def _add_data_table(self, table_data: List[Dict], columns: List[str]) -> List:
        """Добавляет таблицу данных в отчет"""
        elements = []
        
        elements.append(Paragraph("📋 Данные", self.styles['SectionTitle']))
        
        if not table_data or not columns:
            elements.append(Paragraph("Данные отсутствуют", self.styles['NormalText']))
            return elements
        
        # Подготавливаем данные для таблицы (первые 30 строк)
        table_rows = [columns]  # Заголовки
        
        for row in table_data[:30]:  # Увеличиваем количество строк
            table_row = []
            for col in columns:
                value = row.get(col, '')
                
                # Обрабатываем пустые значения и NaN
                if (value is None or value == '' or str(value).strip() == '' or 
                    (isinstance(value, float) and math.isnan(value))):
                    value = '—'  # Используем тире для пустых значений
                else:
                    # Ограничиваем длину значения
                    if isinstance(value, str) and len(value) > 25:
                        value = value[:22] + '...'
                    elif isinstance(value, (int, float)):
                        # Форматируем числа, проверяем на NaN
                        if isinstance(value, float):
                            if math.isnan(value):
                                value = '—'  # Заменяем NaN на тире
                            else:
                                value = f"{value:.2f}" if value != int(value) else str(int(value))
                        else:
                            value = str(value)
                
                table_row.append(str(value))
            table_rows.append(table_row)
        
        # Создаем таблицу с улучшенным форматированием
        table = Table(table_rows, repeatRows=1)
        table.setStyle(TableStyle([
            # Заголовки
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Данные
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fefce8')),  # Светло-желтый фон
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            
            # Границы
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
            
            # Альтернативные строки
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fefce8'), colors.HexColor('#f7fee7')])
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        if len(table_data) > 30:
            elements.append(Paragraph(f"<i>Показаны первые 30 строк из {len(table_data)}</i>", self.styles['NormalText']))
        
        return elements
    
    def _add_analytics_section(self, analytics: Dict) -> List:
        """Добавляет раздел аналитики"""
        elements = []
        
        elements.append(Paragraph("📈 Аналитика", self.styles['SectionTitle']))
        
        # Общая статистика
        summary = analytics.get('summary_stats', {})
        if summary:
            stats_text = f"""
            <b>Общая статистика:</b><br/>
            • Всего строк: {analytics.get('total_rows', 0)}<br/>
            • Всего столбцов: {analytics.get('total_columns', 0)}<br/>
            • Числовые столбцы: {summary.get('numeric_columns', 0)}<br/>
            • Текстовые столбцы: {summary.get('text_columns', 0)}<br/>
            • Заполненность: {summary.get('completeness_percentage', 0)}%
            """
            elements.append(Paragraph(stats_text, self.styles['NormalText']))
            elements.append(Spacer(1, 12))
        
        # Информация по столбцам
        columns_info = analytics.get('columns_info', {})
        if columns_info:
            elements.append(Paragraph("<b>Информация по столбцам:</b>", self.styles['NormalText']))
            
            for col_name, col_info in list(columns_info.items())[:10]:  # Ограничиваем количество
                col_text = f"""
                <b>{col_name}:</b> {col_info.get('dtype', 'unknown')} | 
                Уникальных: {col_info.get('unique_count', 0)} | 
                Заполненность: {col_info.get('completeness', 0)}%
                """
                elements.append(Paragraph(col_text, self.styles['NormalText']))
        
        return elements
    
    def _add_ai_analysis_section(self, ai_analyses: Dict[str, str]) -> List:
        """Добавляет раздел AI анализов"""
        elements = []
        
        elements.append(Paragraph("🤖 Анализ от нейросетей", self.styles['SectionTitle']))
        
        if ai_analyses:
            # Добавляем анализ от Яндекс.GPT если есть
            if 'yandex' in ai_analyses and ai_analyses['yandex'].strip():
                elements.append(Paragraph("🔵 Яндекс.GPT", self.styles['SubsectionTitle']))
                elements.append(Spacer(1, 4))
                
                # Конвертируем Markdown в ReportLab элементы
                markdown_elements = self._convert_markdown_to_reportlab(ai_analyses['yandex'])
                elements.extend(markdown_elements)
                
                elements.append(Spacer(1, 8))
            
            # Добавляем анализ от GigaChat если есть
            if 'gigachat' in ai_analyses and ai_analyses['gigachat'].strip():
                elements.append(Paragraph("🟢 GigaChat", self.styles['SubsectionTitle']))
                elements.append(Spacer(1, 4))
                
                # Конвертируем Markdown в ReportLab элементы
                markdown_elements = self._convert_markdown_to_reportlab(ai_analyses['gigachat'])
                elements.extend(markdown_elements)
                
                elements.append(Spacer(1, 8))
        else:
            elements.append(Paragraph("AI анализы не были выполнены", self.styles['NormalText']))
        
        return elements
    
    def create_chart_image(self, chart_data: Dict, chart_type: str) -> Optional[str]:
        """
        Создает изображение диаграммы
        
        Args:
            chart_data: Данные для диаграммы
            chart_type: Тип диаграммы
            
        Returns:
            Путь к созданному изображению или None
        """
        try:
            # Создаем временный файл для изображения
            temp_path = f"temp_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # Настраиваем matplotlib для русского языка
            plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
            plt.rcParams['axes.unicode_minus'] = False
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if chart_type == 'bar' and 'x' in chart_data and 'y' in chart_data:
                ax.bar(chart_data['x'], chart_data['y'], color='#1e3a8a')
                ax.set_title(chart_data.get('title', 'Диаграмма'), fontsize=14)
                ax.set_xlabel(chart_data.get('xlabel', 'X'), fontsize=12)
                ax.set_ylabel(chart_data.get('ylabel', 'Y'), fontsize=12)
                
            elif chart_type == 'line' and 'x' in chart_data and 'y' in chart_data:
                ax.plot(chart_data['x'], chart_data['y'], marker='o', linewidth=2, color='#1e3a8a')
                ax.set_title(chart_data.get('title', 'Диаграмма'), fontsize=14)
                ax.set_xlabel(chart_data.get('xlabel', 'X'), fontsize=12)
                ax.set_ylabel(chart_data.get('ylabel', 'Y'), fontsize=12)
            
            plt.tight_layout()
            plt.savefig(temp_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Ошибка создания изображения диаграммы: {e}")
            return None


def create_pdf_report(data: Dict[str, Any], output_path: str) -> bool:
    """
    Создает PDF отчет
    
    Args:
        data: Данные для отчета
        output_path: Путь для сохранения
        
    Returns:
        True если успешно, False иначе
    """
    generator = PDFReportGenerator()
    return generator.generate_report(data, output_path)


# Пример использования
if __name__ == "__main__":
    # Тестовые данные
    test_data = {
        'filename': 'test_data.csv',
        'total_rows': 100,
        'total_columns': 5,
        'columns': ['make', 'model', 'year', 'price', 'color'],
        'table_data': [
            {'make': 'Toyota', 'model': 'Camry', 'year': 2020, 'price': 25000, 'color': 'Белый'},
            {'make': 'Honda', 'model': 'Civic', 'year': 2019, 'price': 22000, 'color': 'Черный'},
            {'make': 'Ford', 'model': 'Focus', 'year': 2021, 'price': 18000, 'color': 'Серый'}
        ],
        'analytics': {
            'summary_stats': {
                'numeric_columns': 2,
                'text_columns': 3,
                'completeness_percentage': 95.5
            },
            'columns_info': {
                'make': {'dtype': 'object', 'unique_count': 3, 'completeness': 100},
                'model': {'dtype': 'object', 'unique_count': 3, 'completeness': 100},
                'year': {'dtype': 'int64', 'unique_count': 3, 'completeness': 100}
            }
        },
        'ai_analysis': 'Это тестовый анализ от нейросети. Данные показывают разнообразие автомобилей с разными характеристиками.'
    }
    
    # Создаем тестовый отчет
    success = create_pdf_report(test_data, 'test_report.pdf')
    if success:
        print("✅ Тестовый PDF отчет создан успешно")
    else:
        print("❌ Ошибка создания тестового PDF отчета")

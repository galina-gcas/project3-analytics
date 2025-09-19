#!/usr/bin/env python3
"""
Анализ PDF файла для понимания его структуры
"""

import pdfplumber
import os

def analyze_pdf(pdf_file):
    """Анализирует PDF файл и показывает его структуру"""
    
    if not os.path.exists(pdf_file):
        print(f"❌ Файл {pdf_file} не найден!")
        return False
    
    try:
        print(f"📄 Анализируем PDF файл: {pdf_file}")
        print("=" * 50)
        
        with pdfplumber.open(pdf_file) as pdf:
            print(f"📊 Количество страниц: {len(pdf.pages)}")
            
            if len(pdf.pages) == 0:
                print("❌ PDF файл не содержит страниц")
                return False
            
            # Анализируем каждую страницу
            for page_num, page in enumerate(pdf.pages):
                print(f"\n📄 Страница {page_num + 1}:")
                
                # Извлекаем текст
                text = page.extract_text()
                if text:
                    print(f"📝 Текст (первые 200 символов): {text[:200]}...")
                else:
                    print("📝 Текст не найден")
                
                # Ищем таблицы
                tables = page.extract_tables()
                print(f"📋 Найдено таблиц: {len(tables)}")
                
                if tables:
                    for i, table in enumerate(tables):
                        print(f"   Таблица {i+1}: {len(table)} строк x {len(table[0]) if table else 0} столбцов")
                        if table and len(table) > 0:
                            print(f"   Первая строка: {table[0]}")
                else:
                    print("   Таблицы не найдены")
                
                # Ищем изображения
                images = page.images
                print(f"🖼️ Найдено изображений: {len(images)}")
                
                # Ищем линии
                lines = page.lines
                print(f"📏 Найдено линий: {len(lines)}")
                
                # Ищем прямоугольники
                rects = page.rects
                print(f"⬜ Найдено прямоугольников: {len(rects)}")
        
        print("\n" + "=" * 50)
        print("💡 Рекомендации:")
        print("   - Если это скриншот или изображение, таблицы не будут найдены")
        print("   - Для анализа таблиц нужен PDF с текстовыми таблицами")
        print("   - Попробуйте использовать CSV или Excel файлы для лучших результатов")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка анализа PDF: {e}")
        return False

if __name__ == "__main__":
    pdf_file = "Screenshot 2025-09-18 214023.pdf"
    analyze_pdf(pdf_file)


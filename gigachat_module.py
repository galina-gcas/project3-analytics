#!/usr/bin/env python3
"""
Модуль для анализа табличных данных с помощью GigaChat
"""

import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class GigaChatAnalyzer:
    """Класс для анализа данных с помощью GigaChat"""
    
    def __init__(self):
        """Инициализация анализатора GigaChat"""
        load_dotenv()
        
        self.api_key = os.getenv('GIGACHAT_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Не задана переменная окружения GIGACHAT_API_KEY. "
                "Проверьте файл .env"
            )
        
        # Инициализируем GigaChat
        try:
            from gigachat import GigaChat
            
            # Используем сертификат через ca_bundle_file
            cert_path = os.path.join(os.path.dirname(__file__), "russian_trusted_root_ca.cer")
            
            if os.path.exists(cert_path):
                self.client = GigaChat(
                    credentials=self.api_key,
                    verify_ssl_certs=True,
                    ca_bundle_file=cert_path
                )
            else:
                # Если сертификат не найден, отключаем проверку SSL
                self.client = GigaChat(
                    credentials=self.api_key,
                    verify_ssl_certs=False
                )
            
            logger.info("GigaChat клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации GigaChat: {e}")
            raise
    
    def analyze_table_data(self, table_data: List[Dict], filename: str) -> Dict[str, Any]:
        """
        Анализирует табличные данные с помощью GigaChat
        
        Args:
            table_data: Список словарей с данными таблицы (первые 15 строк)
            filename: Имя файла для контекста
            
        Returns:
            Словарь с результатом анализа
        """
        try:
            # Создаем промпт для анализа
            system_prompt = (
                "Ты - аналитическая система с большим опытом. "
                "Твоя задача - анализировать табличные данные, делать выводы и находить аномалии или интересные тенденции. "
                "Отвечай на русском языке. Будь конкретным и полезным в своих выводах."
            )
            
            # Подготавливаем данные для промпта
            data_text = f"Вот первые 15 строк таблицы из файла {filename}:\n\n"
            
            if table_data:
                # Получаем названия столбцов
                columns = list(table_data[0].keys()) if table_data else []
                data_text += f"Столбцы: {', '.join(columns)}\n\n"
                
                # Добавляем данные
                for i, row in enumerate(table_data, 1):
                    data_text += f"Строка {i}: "
                    row_values = []
                    for col, value in row.items():
                        if value is None or value == '':
                            value = 'пусто'
                        row_values.append(f"{col}={value}")
                    data_text += ", ".join(row_values) + "\n"
            else:
                data_text += "Данные отсутствуют"
            
            # Создаем полный промпт
            full_prompt = f"{system_prompt}\n\n{data_text}"
            
            logger.info(f"Отправляем запрос в GigaChat для анализа файла {filename}")
            
            # Отправляем запрос
            response = self.client.chat(full_prompt)
            
            if response and hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    analysis_text = choice.message.content
                else:
                    analysis_text = str(choice)
                
                logger.info(f"GigaChat анализ завершен успешно для файла {filename}")
                
                return {
                    'success': True,
                    'analysis': analysis_text,
                    'model': 'gigachat',
                    'filename': filename
                }
            else:
                logger.error("GigaChat вернул пустой ответ")
                return {
                    'success': False,
                    'error': 'GigaChat вернул пустой ответ'
                }
                
        except Exception as e:
            logger.error(f"Ошибка анализа данных через GigaChat: {e}")
            return {
                'success': False,
                'error': f'Ошибка анализа данных через GigaChat: {str(e)}'
            }

def create_gigachat_analyzer():
    """
    Создает экземпляр анализатора GigaChat
    
    Returns:
        GigaChatAnalyzer или None в случае ошибки
    """
    try:
        return GigaChatAnalyzer()
    except Exception as e:
        logger.error(f"Не удалось создать анализатор GigaChat: {e}")
        return None

if __name__ == "__main__":
    # Тестирование модуля
    import json
    
    # Тестовые данные
    test_data = [
        {"name": "Иван", "age": 25, "salary": 50000},
        {"name": "Мария", "age": 30, "salary": 60000},
        {"name": "Петр", "age": 35, "salary": 70000}
    ]
    
    try:
        analyzer = create_gigachat_analyzer()
        if analyzer:
            result = analyzer.analyze_table_data(test_data, "test.csv")
            print("Результат анализа GigaChat:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("Не удалось создать анализатор GigaChat")
    except Exception as e:
        print(f"Ошибка тестирования: {e}")
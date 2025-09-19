#!/usr/bin/env python3
"""
Модуль для работы с Яндекс.GPT API
Основан на коде из generate-deferred.py
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from yandex_cloud_ml_sdk import YCloudML

logger = logging.getLogger(__name__)

class YandexGPTAnalyzer:
    """Класс для анализа данных с помощью Яндекс.GPT"""
    
    def __init__(self):
        """Инициализация с параметрами из .env файла"""
        self.folder_id = os.getenv('YANDEX_FOLDER_ID')
        self.auth_token = os.getenv('YANDEX_AUTH_TOKEN')
        
        if not self.folder_id or not self.auth_token:
            raise ValueError(
                "Не заданы переменные окружения YANDEX_FOLDER_ID и YANDEX_AUTH_TOKEN. "
                "Проверьте файл .env"
            )
        
        try:
            self.sdk = YCloudML(
                folder_id=self.folder_id,
                auth=self.auth_token,
            )
            self.model = self.sdk.models.completions("yandexgpt")
            logger.info("Яндекс.GPT SDK успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Яндекс.GPT SDK: {e}")
            raise e
    
    def analyze_table_data(self, table_data: List[Dict[str, Any]], filename: str = "") -> Dict[str, Any]:
        """
        Анализирует табличные данные с помощью Яндекс.GPT
        
        Args:
            table_data: Список словарей с данными таблицы (первые 15 строк)
            filename: Имя файла для контекста
            
        Returns:
            Словарь с результатами анализа
        """
        try:
            # Подготавливаем данные для анализа
            data_text = self._prepare_data_for_analysis(table_data)
            
            # Формируем системный промпт
            system_prompt = """Ты - аналитическая система с большим опытом. Твоя задача - анализировать табличные данные, делать выводы и находить аномалии или интересные тенденции.

Проанализируй предоставленные данные и дай развернутый ответ, включающий:
1. Общую характеристику данных
2. Выявленные паттерны и тренды
3. Аномалии или необычные значения
4. Практические выводы и рекомендации
5. Потенциальные области для дальнейшего исследования

Отвечай на русском языке, структурированно и профессионально."""

            # Формируем пользовательский промпт
            user_prompt = f"""Вот первые 15 строк таблицы из файла "{filename}":

{data_text}

Пожалуйста, проанализируй эти данные и дай развернутый аналитический отчет."""

            # Создаем сообщения для API
            messages = [
                {
                    "role": "system",
                    "text": system_prompt
                },
                {
                    "role": "user", 
                    "text": user_prompt
                }
            ]
            
            logger.info(f"Отправляем запрос в Яндекс.GPT для анализа файла: {filename}")
            
            # Отправляем запрос с использованием deferred метода
            operation = self.model.configure(temperature=0.3).run_deferred(messages)
            
            # Ждем завершения операции
            result = operation.wait()
            
            if result and hasattr(result, 'alternatives') and result.alternatives:
                # Получаем текст из альтернативы
                alternative = result.alternatives[0]
                if hasattr(alternative, 'message') and hasattr(alternative.message, 'text'):
                    analysis_text = alternative.message.text
                elif hasattr(alternative, 'text'):
                    analysis_text = alternative.text
                else:
                    # Пробуем получить текст напрямую из альтернативы
                    analysis_text = str(alternative)
                
                logger.info("Анализ от Яндекс.GPT получен успешно")
                
                return {
                    'success': True,
                    'analysis': analysis_text,
                    'model': 'yandexgpt',
                    'filename': filename
                }
            else:
                logger.error("Получен пустой ответ от Яндекс.GPT")
                return {
                    'success': False,
                    'error': 'Получен пустой ответ от нейросети'
                }
                
        except Exception as e:
            logger.error(f"Ошибка анализа данных через Яндекс.GPT: {e}")
            return {
                'success': False,
                'error': f'Ошибка анализа: {str(e)}'
            }
    
    def _prepare_data_for_analysis(self, table_data: List[Dict[str, Any]]) -> str:
        """
        Подготавливает данные таблицы для отправки в нейросеть
        
        Args:
            table_data: Список словарей с данными
            
        Returns:
            Отформатированная строка с данными
        """
        if not table_data:
            return "Данные отсутствуют"
        
        # Получаем заголовки из первого элемента
        headers = list(table_data[0].keys())
        
        # Формируем заголовки
        header_line = " | ".join(str(header) for header in headers)
        separator = "-" * len(header_line)
        
        # Формируем строки данных
        data_lines = []
        for i, row in enumerate(table_data[:15], 1):  # Берем максимум 15 строк
            row_values = []
            for header in headers:
                value = row.get(header, '')
                # Ограничиваем длину значения для читаемости
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + "..."
                row_values.append(str(value))
            
            data_line = " | ".join(row_values)
            data_lines.append(f"{i:2d}. {data_line}")
        
        # Объединяем все в одну строку
        result = f"Заголовки: {header_line}\n"
        result += f"Разделитель: {separator}\n"
        result += "Данные:\n"
        result += "\n".join(data_lines)
        
        return result
    
    def test_connection(self) -> bool:
        """
        Тестирует подключение к Яндекс.GPT
        
        Returns:
            True если подключение успешно, False иначе
        """
        try:
            test_messages = [
                {
                    "role": "system",
                    "text": "Ты - тестовая система. Отвечай кратко."
                },
                {
                    "role": "user",
                    "text": "Привет! Это тест подключения."
                }
            ]
            
            operation = self.model.configure(temperature=0.1).run_deferred(test_messages)
            result = operation.wait()
            
            if result and hasattr(result, 'alternatives') and result.alternatives:
                logger.info("Тест подключения к Яндекс.GPT прошел успешно")
                return True
            else:
                logger.error("Тест подключения к Яндекс.GPT не прошел")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка тестирования подключения к Яндекс.GPT: {e}")
            return False


def create_yandex_analyzer() -> Optional[YandexGPTAnalyzer]:
    """
    Создает экземпляр анализатора Яндекс.GPT
    
    Returns:
        Экземпляр YandexGPTAnalyzer или None в случае ошибки
    """
    try:
        return YandexGPTAnalyzer()
    except Exception as e:
        logger.error(f"Не удалось создать анализатор Яндекс.GPT: {e}")
        return None


# Пример использования
if __name__ == "__main__":
    # Настройка логирования для тестирования
    logging.basicConfig(level=logging.INFO)
    
    # Тестируем подключение
    analyzer = create_yandex_analyzer()
    if analyzer:
        print("✅ Анализатор Яндекс.GPT создан успешно")
        
        # Тестируем подключение
        if analyzer.test_connection():
            print("✅ Подключение к Яндекс.GPT работает")
        else:
            print("❌ Проблемы с подключением к Яндекс.GPT")
    else:
        print("❌ Не удалось создать анализатор Яндекс.GPT")

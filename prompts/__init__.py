import os

def load_prompt(filename: str) -> str:
    """Загружает промпт из файла"""
    prompt_path = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Файл промпта не найден: {prompt_path}")
        return ""
    except Exception as e:
        print(f"Ошибка загрузки промпта {filename}: {e}")
        return ""

# Загружаем промпты при импорте модуля
GIGACHAT_SYSTEM_PROMPT = load_prompt("gigachat_system_prompt.txt")
QWEN_TELEGRAM_PROMPT = load_prompt("qwen_telegram_prompt.txt")
QWEN_GENERAL_PROMPT = load_prompt("qwen_general_prompt.txt")
GIGACHAT_IMAGE_PROMPT = load_prompt("gigachat_image_prompt.txt")
GIGACHAT_THREADS_PROMPT = load_prompt("gigachat_threads_prompt.txt")

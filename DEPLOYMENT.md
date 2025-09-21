# 🚀 Развертывание проекта на Render + GitHub Pages

Этот документ описывает пошаговое развертывание веб-приложения для анализа данных на бесплатных платформах Render (backend) и GitHub Pages (frontend).

## 📋 Архитектура развертывания

- **Backend (Render)**: Flask API для обработки файлов, AI анализа и генерации PDF
- **Frontend (GitHub Pages)**: Статический интерфейс, взаимодействующий с API
- **CI/CD**: GitHub Actions для автоматического деплоя

## 🔧 Подготовка к развертыванию

### 1. Создание GitHub репозитория

1. Создайте новый репозиторий на GitHub
2. Загрузите код проекта в репозиторий
3. Убедитесь, что все файлы загружены, включая:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
   - `.github/workflows/deploy.yml`
   - `.nojekyll`

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта (НЕ загружайте его в GitHub):

```env
# GigaChat API
GIGACHAT_API_KEY=your_gigachat_api_key_here

# Yandex GPT API
YANDEX_FOLDER_ID=your_yandex_folder_id_here
YANDEX_AUTH=your_yandex_auth_token_here
```

## 🌐 Развертывание Backend на Render

### 1. Создание аккаунта на Render

1. Перейдите на [render.com](https://render.com)
2. Зарегистрируйтесь через GitHub
3. Подтвердите email

### 2. Создание Web Service

1. Нажмите "New +" → "Web Service"
2. Подключите ваш GitHub репозиторий
3. Настройте сервис:

```
Name: analytics-backend (или любое другое имя)
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

### 3. Настройка переменных окружения в Render

В разделе "Environment" добавьте переменные:

```
GIGACHAT_API_KEY=your_gigachat_api_key_here
YANDEX_FOLDER_ID=your_yandex_folder_id_here
YANDEX_AUTH=your_yandex_auth_token_here
RENDER=true
```

### 4. Запуск деплоя

1. Нажмите "Create Web Service"
2. Дождитесь завершения деплоя (5-10 минут)
3. Скопируйте URL вашего сервиса (например: `https://analytics-backend.onrender.com`)

## 📄 Развертывание Frontend на GitHub Pages

### 1. Обновление API URL

В файле `templates/index.html` замените URL в строке 593:

```javascript
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:5000' 
    : 'https://your-render-app-name.onrender.com'; // Замените на ваш URL Render
```

### 2. Включение GitHub Pages

1. Перейдите в Settings вашего репозитория
2. Найдите раздел "Pages"
3. В "Source" выберите "GitHub Actions"
4. Сохраните настройки

### 3. Автоматический деплой

GitHub Actions автоматически развернет frontend при каждом push в ветку `master`:

1. Сделайте commit и push изменений в ветку `master`
2. Перейдите в раздел "Actions" репозитория
3. Дождитесь завершения workflow
4. Ваш сайт будет доступен по адресу: `https://yourusername.github.io/repository-name`

## 🔄 Обновление приложения

### Backend (Render)
- Изменения в коде автоматически деплоятся при push в GitHub
- Render автоматически перезапускает сервис

### Frontend (GitHub Pages)
- GitHub Actions автоматически обновляет сайт при push в `master`
- Изменения появляются через 1-2 минуты

## 🛠️ Локальная разработка

### Запуск backend локально:

```bash
# Установка зависимостей
pip install -r requirements.txt

# Создание .env файла
cp env.example .env
# Отредактируйте .env файл

# Запуск приложения
python app.py
```

### Тестирование frontend:

1. Откройте `templates/index.html` в браузере
2. Или используйте локальный сервер:
```bash
python -m http.server 8000
```

## 🔍 Отладка

### Проверка логов Render:
1. Перейдите в ваш сервис на Render
2. Откройте раздел "Logs"
3. Проверьте ошибки деплоя или выполнения

### Проверка GitHub Actions:
1. Перейдите в "Actions" репозитория
2. Откройте последний workflow
3. Проверьте логи выполнения

### Проверка CORS:
Если возникают ошибки CORS, убедитесь что:
1. В `app.py` правильно настроен CORS
2. URL в `API_BASE_URL` соответствует вашему Render сервису

## 📊 Мониторинг

### Render:
- Бесплатный план: 750 часов в месяц
- Автоматическое "засыпание" после 15 минут неактивности
- Пробуждение занимает 30-60 секунд

### GitHub Pages:
- Бесплатно для публичных репозиториев
- Ограничение: 1GB трафика в месяц
- Автоматическое обновление при push

## 🚨 Ограничения бесплатных планов

### Render:
- ✅ 750 часов в месяц
- ✅ Автоматическое засыпание
- ❌ Нет постоянного хранения файлов
- ❌ Ограниченная производительность

### GitHub Pages:
- ✅ Бесплатный хостинг
- ✅ Автоматический HTTPS
- ❌ Только статические файлы
- ❌ Нет серверной логики

## 🔧 Дополнительные настройки

### Оптимизация для продакшена:

1. **Кэширование**: Добавьте заголовки кэширования
2. **Сжатие**: Включите gzip сжатие
3. **CDN**: Используйте Cloudflare для ускорения
4. **Мониторинг**: Настройте уведомления об ошибках

### Безопасность:

1. **HTTPS**: Всегда используйте HTTPS
2. **CORS**: Ограничьте домены в CORS
3. **API ключи**: Никогда не коммитьте API ключи
4. **Валидация**: Проверяйте все входящие данные

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи в Render и GitHub Actions
2. Убедитесь в правильности переменных окружения
3. Проверьте CORS настройки
4. Убедитесь что API ключи действительны

## 🎉 Готово!

После выполнения всех шагов у вас будет:
- ✅ Backend API на Render
- ✅ Frontend на GitHub Pages  
- ✅ Автоматический CI/CD
- ✅ Бесплатное развертывание

Ваше приложение будет доступно по адресу GitHub Pages и будет автоматически обновляться при каждом изменении кода!

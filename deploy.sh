#!/bin/bash

# Скрипт для быстрого развертывания проекта
# Использование: ./deploy.sh

echo "🚀 Начинаем развертывание проекта Analytics на Render..."

# Проверяем наличие необходимых файлов
echo "📋 Проверяем файлы конфигурации..."

required_files=("app.py" "requirements.txt" "Procfile" "runtime.txt")

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Отсутствует файл: $file"
        exit 1
    else
        echo "✅ Найден файл: $file"
    fi
done

# Проверяем .env файл
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден. Создайте его на основе env.example"
    echo "📝 Скопируйте env.example в .env и заполните переменные:"
    echo "   cp env.example .env"
    echo "   nano .env"
    exit 1
fi

echo "✅ Все необходимые файлы найдены"

# Проверяем git статус
echo "📊 Проверяем git статус..."
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Есть несохраненные изменения. Сохраните их перед развертыванием:"
    echo "   git add ."
    echo "   git commit -m 'Prepare for deployment'"
    exit 1
fi

echo "✅ Git репозиторий чист"

# Проверяем ветку
current_branch=$(git branch --show-current)
if [ "$current_branch" != "master" ]; then
    echo "⚠️  Вы не в ветке master. Переключитесь на master:"
    echo "   git checkout master"
    exit 1
fi

echo "✅ Вы в ветке master"

# Инструкции для пользователя
echo ""
echo "🎯 Следующие шаги для развертывания:"
echo ""
echo "1. 📤 Загрузите код в GitHub (если еще не сделано):"
echo "   git remote add origin https://github.com/yourusername/your-repo.git"
echo "   git push -u origin master"
echo ""
echo "2. 🌐 Создайте Web Service на Render:"
echo "   - Перейдите на https://render.com"
echo "   - New + → Web Service"
echo "   - Подключите GitHub репозиторий"
echo "   - Build Command: pip install -r requirements.txt"
echo "   - Start Command: gunicorn app:app"
echo "   - Добавьте переменные окружения из .env"
echo ""
echo "3. 🔄 Запустите деплой:"
echo "   git push origin master"
echo ""
echo "📚 Подробные инструкции в файле DEPLOYMENT.md"
echo ""
echo "🎉 Удачи с развертыванием!"

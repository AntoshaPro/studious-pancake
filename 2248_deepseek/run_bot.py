#!/usr/bin/env python3
# run_bot.py
"""
Скрипт для запуска бота 2248 с проверкой основных компонентов
"""

import sys
import os
from pathlib import Path

def main():
    print("🚀 Запуск бота 2248...")
    
    # Проверяем наличие необходимых файлов
    required_files = [
        "main.py",
        "bot.py",
        "config.json",
        "requirements.txt"
    ]
    
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Файл {file} не найден!")
            return False
    
    print("✅ Все необходимые файлы на месте")
    
    # Проверяем зависимости
    try:
        import cv2
        import numpy as np
        from PIL import Image
        print("✅ Зависимости установлены")
    except ImportError as e:
        print(f"❌ Не установлена зависимость: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        return False
    
    # Запускаем бота
    print("\n🎮 Запуск основного меню бота...")
    try:
        from bot import Auto2248Bot
        bot = Auto2248Bot()
        bot.show_menu()
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
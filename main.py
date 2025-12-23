# main.py
import sys
from bot import Auto2248Bot

if __name__ == "__main__":
    print("🚀 Запуск автоматического бота для игры 2248 с механизмами обучения...")
    print("📚 Версия с самообучением на ошибках и рекламными клетками (adv)")

    try:
        import cv2
        import numpy as np
        from PIL import Image
    except ImportError as e:
        print(f"❌ Не установлена зависимость: {e}")
        print(" Установите: pip install -r requirements.txt")
        sys.exit(1)

    bot = Auto2248Bot()
    bot.show_menu()
#!/usr/bin/env python3
# test_imports.py
# Тестовый файл для проверки импорта всех компонентов бота

def test_imports():
    print("🧪 Проверка импортов компонентов бота 2248...")
    
    try:
        from bot import Auto2248Bot
        print("✅ bot.py - импорт успешен")
    except Exception as e:
        print(f"❌ bot.py - ошибка импорта: {e}")
        return False
    
    try:
        from game_logic import GameLogic
        print("✅ game_logic.py - импорт успешен")
    except Exception as e:
        print(f"❌ game_logic.py - ошибка импорта: {e}")
        return False
    
    try:
        from heuristics_2248 import Heuristics2248
        print("✅ heuristics_2248.py - импорт успешен")
    except Exception as e:
        print(f"❌ heuristics_2248.py - ошибка импорта: {e}")
        return False
    
    try:
        from game_runner import GameRunner
        print("✅ game_runner.py - импорт успешен")
    except Exception as e:
        print(f"❌ game_runner.py - ошибка импорта: {e}")
        return False
    
    try:
        from ui import UI
        print("✅ ui.py - импорт успешен")
    except Exception as e:
        print(f"❌ ui.py - импорт успешен: {e}")
        return False
    
    try:
        from config_manager import ConfigManager
        print("✅ config_manager.py - импорт успешен")
    except Exception as e:
        print(f"❌ config_manager.py - ошибка импорта: {e}")
        return False
    
    try:
        from screen_processor import ScreenProcessor
        print("✅ screen_processor.py - импорт успешен")
    except Exception as e:
        print(f"❌ screen_processor.py - ошибка импорта: {e}")
        return False
    
    try:
        from input_controller import InputController
        print("✅ input_controller.py - импорт успешен")
    except Exception as e:
        print(f"❌ input_controller.py - ошибка импорта: {e}")
        return False
    
    try:
        from ad_detector_2248 import EndGameAdDetector2248
        print("✅ ad_detector_2248.py - импорт успешен")
    except Exception as e:
        print(f"❌ ad_detector_2248.py - ошибка импорта: {e}")
        return False
    
    try:
        from end_game_handler import EndGameHandler
        print("✅ end_game_handler.py - импорт успешен")
    except Exception as e:
        print(f"❌ end_game_handler.py - ошибка импорта: {e}")
        return False
    
    try:
        from color_trainer import ColorTrainer
        print("✅ color_trainer.py - импорт успешен")
    except Exception as e:
        print(f"❌ color_trainer.py - ошибка импорта: {e}")
        return False
    
    print("🎉 Все компоненты успешно импортированы!")
    print("\n📋 Архитектура бота 2248 полностью готова к работе:")
    print("   - main.py → точка входа")
    print("   - bot.py → главный фасад")
    print("   - ui.py → консольное меню")
    print("   - game_logic.py → логика игры + эвристика")
    print("   - heuristics_2248.py → умная оценка ходов")
    print("   - game_runner.py → основной игровой цикл")
    print("   - config_manager.py → управление настройками")
    print("   - screen_processor.py → работа с экраном")
    print("   - input_controller.py → выполнение свайпов")
    print("   - ad_detector_2248.py → детекция рекламы")
    print("   - end_game_handler.py → обработка конца игры")
    print("   - color_trainer.py → обучение распознаванию цветов")
    print("\n✅ Бот готов к запуску!")
    
    return True

if __name__ == "__main__":
    test_imports()
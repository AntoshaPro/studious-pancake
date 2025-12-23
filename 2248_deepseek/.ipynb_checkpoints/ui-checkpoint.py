# ui.py
import cv2
import constants as const
from retrainer_2248 import Retrainer2248
from board_printer import print_board
from calibrator import Calibrator


class UI:
    def __init__(self, bot):
        self.bot = bot
        self.retrainer = Retrainer2248(bot.config_manager, bot.screen_processor)
        self.calibrator = Calibrator(bot.config_manager, bot.screen_processor)

    def show_menu(self):
        while True:
            print("\n" + "=" * 60)
            print("🤖 АВТОМАТИЧЕСКИЙ БОТ ДЛЯ 2248 С ОБУЧЕНИЕМ")
            print("=" * 60)
            print("\nВыберите действие:")
            print(" 1. 🔧 Проверить ADB подключение")
            print(" 2. ⚡ Быстрая калибровка")
            print(" 3. 🧠 Умная калибровка")
            print(" 4. 🎨 Обучить распознаванию цветов")
            print(" 5. 📊 Распознать текущую доску")
            print(" 6. 🤖 Запустить автоматическую игру 2248")
            print(" 7. 📈 Показать статистику обучения")
            print(" 8. 🎓 Дообучить на накопленных ошибках")
            print(" 9. ⚙️ Показать настройки")
            print(" 10. 🗑️ Очистить проблемные клетки")
            print(" 11. 🔄 Сбросить все настройки")
            print(" 12. 🎯 Ручная подгонка сетки")
            print(" 0. 🚪 Выход")

            choice = input("\nВаш выбор: ").strip()

            if choice == "1":
                self.bot.check_adb()

            elif choice == "2":
                if self.bot.check_adb():
                    self.calibrator.calibrate_quick()

            elif choice == "3":
                if self.bot.check_adb():
                    self.calibrator.calibrate_smart()

            elif choice == "4":
                if self.bot.check_adb():
                    self.bot.color_trainer.learn_colors_simple()

            elif choice == "5":
                if self.bot.check_adb():
                    self.bot.take_screenshot("current.png")
                    self.bot.screen_processor.crop_cells_from_screen("current.png")
                    board, confidence = (
                        self.bot.game_logic.recognize_board_with_confidence()
                    )
                    if board is not None:
                        print_board(board, confidence)

            elif choice == "6":
                if self.bot.check_adb():
                    try:
                        moves = int(input("Сколько ходов сделать? (30): ") or "30")
                        self.bot.run_auto_game(moves)
                    except ValueError:
                        print("❌ Введите число!")

            elif choice == "7":
                self.show_learning_stats()

            elif choice == "8":
                self.bot.show_problem_cells()

            elif choice == "9":
                print("\n📋 ТЕКУЩИЕ НАСТРОЙКИ:")
                config = self.bot.config_manager.config
                print(f" Калибровано: {'✅' if config.get('calibrated') else '❌'}")
                print(
                    f" Выученных классов (включая adv): {len(config.get('colors', {}))}"
                )
                print(f" Адаптивный порог: {self.bot.game_logic.adaptive_threshold}")
                print(f" Порог уверенности: {self.bot.game_logic.confidence_threshold}")

            elif choice == "10":
                confirm = input("Удалить проблемные клетки? (y/n): ")
                if confirm.lower() == "y":
                    self.bot.config_manager.problem_cells = []
                    if const.PROBLEMS_FILE.exists():
                        const.PROBLEMS_FILE.unlink()
                    print("✅ Проблемные клетки очищены")

            elif choice == "11":
                confirm = input("Уверены? Это удалит ВСЕ настройки! (y/n): ")
                if confirm.lower() == "y":
                    self.bot.config_manager.reset_all()

            elif choice == "12":
                if self.bot.check_adb():
                    self.calibrator.manual_adjust_grid(step=20)

            elif choice == "0":
                print("\n👋 До свидания!")
                if self.bot.config_manager.problem_cells:
                    self.bot.config_manager.save_problem_cells()
                break

            input("\nНажмите Enter чтобы продолжить...")

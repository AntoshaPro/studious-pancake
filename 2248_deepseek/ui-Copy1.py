# ui.py
import cv2
import constants as const
from retrainer_2248 import Retrainer2248
from board_printer import print_board


class UI:
    def __init__(self, bot):
        self.bot = bot
        self.retrainer = Retrainer2248(bot.config_manager, bot.screen_processor)

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
                    self.calibrate_quick()
            elif choice == "3":
                if self.bot.check_adb():
                    self.calibrate_smart()
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
                self.auto_retrain_from_problems()
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
                    self.manual_adjust_grid(step=20)
            elif choice == "0":
                print("\n👋 До свидания!")
                if self.bot.config_manager.problem_cells:
                    self.bot.config_manager.save_problem_cells()
                break

            input("\nНажмите Enter чтобы продолжить...")

    def calibrate_quick(self):
        print("\n" + "=" * 60)
        print("⚡ БЫСТРАЯ КАЛИБРОВКА")
        print("=" * 60)

        if not self.bot.screen_processor.take_screenshot("quick_calib.png"):
            print("❌ Не удалось сделать скриншот")
            return False

        if self.bot.screen_processor.create_grid_from_preset():
            self.bot.screen_processor.crop_cells_from_screen("quick_calib.png")

            print("\n📸 Проверяем правильность калибровки...")
            img = cv2.imread("quick_calib.png")
            if img is not None:
                grid = self.bot.config_manager.config["grid"]
                for r in range(const.ROWS):
                    for c in range(const.COLS):
                        x, y = grid[r][c]
                        color = (0, 255, 0)
                        cv2.line(img, (x - 20, y), (x + 20, y), color, 3)
                        cv2.line(img, (x, y - 20), (x, y + 20), color, 3)
                        cv2.putText(
                            img,
                            f"{r},{c}",
                            (x - 30, y - 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            color,
                            2,
                        )

                marked_img = "quick_calib_marked.png"
                cv2.imwrite(marked_img, img)

                img_display = cv2.imread(marked_img)
                cv2.imshow("ПРОВЕРКА: Крестики в центрах клеток?", img_display)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

                correct = input(
                    "\n❓ Правильно ли отмечены центры клеток? (y/n): "
                ).lower()
                if correct == "y":
                    print("✅ Быстрая калибровка завершена!")
                    return True
                else:
                    print("❌ Быстрая калибровка не удалась.")
                    return False

        return False

    def calibrate_smart(self):
        print("\n" + "=" * 60)
        print("🧠 УМНАЯ КАЛИБРОВКА")
        print("=" * 60)

        print("\n📸 Анализирую скриншот игры...")

        if not self.bot.screen_processor.take_screenshot("smart_calib.png"):
            return False

        img = cv2.imread("smart_calib.png")
        if img is None:
            print("❌ Не удалось загрузить скриншот")
            return False

        print("🔍 Ищу игровое поле...")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            print("❌ Не удалось найти игровое поле")
            return self.calibrate_quick()

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        print(f"✅ Нашел игровое поле: X={x}, Y={y}, Ширина={w}, Высота={h}")

        cell_width = w // const.COLS
        cell_height = h // const.ROWS

        grid = []
        for r in range(const.ROWS):
            row = []
            for c in range(const.COLS):
                cell_x = x + c * cell_width + cell_width // 2
                cell_y = y + r * cell_height + cell_height // 2
                row.append((cell_x, cell_y))
            grid.append(row)

        marked = img.copy()
        for r in range(const.ROWS):
            for c in range(const.COLS):
                cell_x, cell_y = grid[r][c]
                cv2.circle(marked, (cell_x, cell_y), 15, (0, 255, 0), 3)
                cv2.putText(
                    marked,
                    f"{r},{c}",
                    (cell_x - 20, cell_y - 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

        cv2.imwrite("smart_calib_marked.png", marked)

        img_display = cv2.imread("smart_calib_marked.png")
        cv2.imshow("УМНАЯ КАЛИБРОВКА: Найденные клетки", img_display)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        correct = input("\n❓ Правильно ли найдены клетки? (y/n): ").lower()
        if correct == "y":
            self.bot.config_manager.config["grid"] = grid
            self.bot.screen_processor._init_grid_bounds()
            self.bot.config_manager.save_config()
            print("✅ Умная калибровка завершена!")
            return True
        else:
            print("🔄 Перехожу к быстрой калибровке...")
            return self.calibrate_quick()

    def manual_adjust_grid(self, step=20):
        if not self.bot.config_manager.config.get("grid"):
            print("❌ Сетка пустая, сначала калибровка")
            return

        while True:
            self.bot.screen_processor.take_screenshot("manual_grid.png")
            img = cv2.imread("manual_grid.png")
            grid = self.bot.config_manager.config["grid"]
            for r in range(const.ROWS):
                for c in range(const.COLS):
                    x, y = grid[r][c]
                    color = (0, 255, 0)
                    cv2.line(img, (x - 20, y), (x + 20, y), color, 3)
                    cv2.line(img, (x, y - 20), (x, y + 20), color, 3)
                    cv2.putText(
                        img,
                        f"{r},{c}",
                        (x - 30, y - 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        color,
                        2,
                    )

            cv2.imshow("РУЧНАЯ ПОДГОНКА СЕТКИ (w/a/s/d, q - сохранить)", img)
            print("\nwasd = сдвиг, q = выйти/сохранить  (шаг =", step, ")")
            key = cv2.waitKey(0) & 0xFF

            if key == ord("q"):
                cv2.destroyAllWindows()
                self.bot.screen_processor._init_grid_bounds()
                self.bot.config_manager.save_config()
                print("✅ Сетка сохранена после ручной подгонки")
                break

            dx, dy = 0, 0
            if key == ord("w"):
                dy = -step
            elif key == ord("s"):
                dy = step
            elif key == ord("a"):
                dx = -step
            elif key == ord("d"):
                dx = step
            else:
                print("⌨️ Используй только w/a/s/d/q")
                continue

            new_grid = []
            for row in self.bot.config_manager.config["grid"]:
                new_row = []
                for x, y in row:
                    new_row.append((x + dx, y + dy))
                new_grid.append(new_row)
            self.bot.config_manager.config["grid"] = new_grid
            print(f"➡️ Сдвинул на dx={dx}, dy={dy}")

    def show_learning_stats(self):
        print("\n📊 СТАТИСТИКА ОБУЧЕНИЯ:")
        print("-" * 40)

        if "colors" in self.bot.config_manager.config:
            print("📚 Выученные классы (примеров на класс):")
            for key in sorted(
                self.bot.config_manager.config["colors"].keys(),
                key=lambda x: (x != "adv", int(x) if str(x).isdigit() else 0),
            ):
                count = len(self.bot.config_manager.config["colors"][key])
                if count > 0:
                    label = "ADV" if key == "adv" else key
                    print(f" {label}: {count} пример(ов)")

        print(f"\n⚠️ Проблемных клеток: {len(self.bot.config_manager.problem_cells)}")

        if self.bot.config_manager.recognition_history:
            errors = sum(self.bot.config_manager.recognition_history)
            total = len(self.bot.config_manager.recognition_history)
            print(f"📈 История ошибок: {errors}/{total} ({errors/total:.1%})")

        print(f"🎯 Текущий порог: {self.bot.game_logic.adaptive_threshold}")
        print(f"🎯 Порог уверенности: {self.bot.game_logic.confidence_threshold}")

    # def auto_retrain_from_problems(self):
    #    print("⚠️ Функция дообучения пока не реализована в модульной версии")
    #    print("Используйте старую версию или подождите обновления")
    def auto_retrain_from_problems(self):
        self.retrainer.interactive_retrain()

    def print_board(self, board, confidence_board=None):
        print("\n" + "=" * 50)
        print("🎮 ДОСКА 2248:")
        print("=" * 50)

        max_len = 6

        for r in range(const.ROWS):
            row_str = ""
            conf_str = ""
            for c in range(const.COLS):
                val = board[r][c]
                if val <= 0:
                    row_str += " " * max_len + " "
                    conf_str += " " * max_len + " "
                else:
                    row_str += f"{val:^{max_len}} "

                    if confidence_board and confidence_board[r][c] > 0:
                        conf = confidence_board[r][c]
                        if conf > 0.8:
                            conf_mark = "✓"
                        elif conf > 0.6:
                            conf_mark = "~"
                        else:
                            conf_mark = "?"
                        conf_str += f"{conf_mark:^{max_len}} "
                    else:
                        conf_str += " " * max_len + " "

            print(row_str)
            if confidence_board:
                print(conf_str)

        print("=" * 50)

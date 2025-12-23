# color_trainer.py
import cv2
import numpy as np
import constants as const


class ColorTrainer:
    def __init__(self, config_manager, screen_processor):
        self.config_manager = config_manager
        self.config = config_manager.config
        self.screen_processor = screen_processor

    def learn_colors_simple(self):
        self.screen_processor.take_screenshot("learn_colors.png")
        self.screen_processor.crop_cells_from_screen("learn_colors.png")

        print("\n📝 Введите числа на доске построчно:")
        print(" Формат: 4 числа через пробел")
        print(" 0 - рекламная/лишняя клетка")

        board_numbers = []
        for r in range(const.ROWS):
            while True:
                row_input = input(f" Ряд {r}: ").strip()
                if not row_input:
                    print(" ❌ Введите 4 числа!")
                    continue

                try:
                    numbers = list(map(int, row_input.split()))
                    if len(numbers) != const.COLS:
                        print(f" ❌ Нужно {const.COLS} числа!")
                        continue
                    board_numbers.append(numbers)

                    try:
                        cv2.destroyAllWindows()
                    except Exception:
                        pass

                    break
                except ValueError:
                    print(" ❌ Используйте только числа!")

        colors_by_number = {}

        for r in range(const.ROWS):
            for c in range(const.COLS):
                number = board_numbers[r][c]
                cell_path = const.CELLS_DIR / f"cell_{r}_{c}.png"
                color = self.screen_processor.extract_color_from_cell(cell_path)
                if not color:
                    continue

                key = "adv" if number == 0 else str(number)

                if key not in colors_by_number:
                    colors_by_number[key] = []
                colors_by_number[key].append(color)

        self.config["colors"] = colors_by_number
        self.config["calibrated"] = True

        try:
            self.config_manager.save_config()
            print("\n✅ Обучение завершено!")
            for key in sorted(
                colors_by_number.keys(),
                key=lambda x: (x != "adv", int(x) if x.isdigit() else 0),
            ):
                examples = colors_by_number[key]
                label = "ADV" if key == "adv" else key
                print(f" Класс {label}: {len(examples)} пример(ов)")
            return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

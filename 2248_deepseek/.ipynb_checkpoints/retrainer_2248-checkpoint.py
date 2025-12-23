# retrainer_2248.py
import cv2
import numpy as np
import constants as const


class Retrainer2248:
    def __init__(self, config_manager, screen_processor):
        self.config_manager = config_manager
        self.config = config_manager.config
        self.screen_processor = screen_processor

    def interactive_retrain(self):
        """
        Проходит по накопленным problem_cells и даёт тебе
        руками поправить класс/цвет, потом обновляет config["colors"].
        """
        problems = self.config_manager.problem_cells
        if not problems:
            print("ℹ️ Нет накопленных проблемных клеток для дообучения.")
            return

        print(f"🧠 Найдено {len(problems)} проблемных клеток для дообучения.")

        updated_colors = self.config.get("colors", {})

        for idx, p in enumerate(problems, start=1):
            path = p["cell"]
            guessed = p["guessed_label"]
            conf = p["confidence"]

            img = cv2.imread(path)
            if img is None:
                continue

            cv2.imshow(f"Problem #{idx} (guess={guessed}, conf={conf:.2f})", img)
            cv2.waitKey(1)

            raw = input(
                f"[{idx}/{len(problems)}] Правильный класс (Enter = пропустить, 0 = adv): "
            ).strip()

            cv2.destroyAllWindows()

            if raw == "":
                continue
            if raw == "0":
                label = "adv"
            else:
                label = raw

            color = self.screen_processor.extract_color_from_cell(path)
            if color is None:
                continue

            if label not in updated_colors:
                updated_colors[label] = []
            updated_colors[label].append([int(c) for c in color])

        # сохранить обновлённые цвета
        self.config["colors"] = updated_colors
        self.config["calibrated"] = True
        self.config_manager.save_config()

        # можно очистить проблемные клетки, чтобы не гонять их вечно
        self.config_manager.problem_cells = []
        self.config_manager.save_problem_cells()

        print("✅ Дообучение завершено, конфиг обновлён.")

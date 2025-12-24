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
        Можно прервать по 'q' и продолжить позже.
        """
        problems = self.config_manager.problem_cells
        if not problems:
            print("ℹ️ Нет накопленных проблемных клеток для дообучения.")
            return

        print(f"🧠 Найдено {len(problems)} проблемных клеток для дообучения.")
        print("   Введите 'q' чтобы прервать дообучение и продолжить позже.\n")

        updated_colors = self.config.get("colors", {})

        processed_indices = []  # индексы реально обработанных проблем

        try:
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
                    f"[{idx}/{len(problems)}] Правильный класс "
                    "(Enter = пропустить, 0 = adv, q = выйти): "
                ).strip()

                if raw.lower() == "q":
                    print("⏹ Прерываю дообучение, сохраню уже исправленные клетки.")
                    break

                if raw == "":
                    # пропускаем, но оставляем в списке проблем
                    cv2.destroyAllWindows()
                    continue

                if raw == "0":
                    label = "adv"
                else:
                    label = raw

                color = self.screen_processor.extract_color_from_cell(path)
                if color is None:
                    cv2.destroyAllWindows()
                    continue

                if label not in updated_colors:
                    updated_colors[label] = []
                updated_colors[label].append([int(c) for c in color])

                processed_indices.append(idx - 1)
                cv2.destroyAllWindows()
        finally:
            # На всякий случай закрываем все окна OpenCV
            cv2.destroyAllWindows()

        # сохранить обновлённые цвета
        self.config["colors"] = updated_colors
        self.config["calibrated"] = True
        self.config_manager.save_config()

        # удаляем только обработанные problem_cells, остальные оставляем
        remaining = [p for i, p in enumerate(problems) if i not in processed_indices]
        self.config_manager.problem_cells = remaining
        self.config_manager.save_problem_cells()

        print(
            f"✅ Дообучение завершено: обработано {len(processed_indices)}, "
            f"осталось {len(remaining)} проблемных клеток."
        )

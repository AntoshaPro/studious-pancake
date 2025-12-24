# recognize_board_with_confidence.py
import numpy as np
import constants as const


def recognize_board_with_confidence(self):
    if not self.config.get("calibrated", False):
        print("❌ Бот не обучен!")
        return None, None

    self.board = [[-1 for _ in range(const.COLS)] for _ in range(const.ROWS)]
    confidence_board = [[0.0 for _ in range(const.COLS)] for _ in range(const.ROWS)]

    colors_map = self.config.setdefault("colors", {})

    for r in range(const.ROWS):
        for c in range(const.COLS):
            cell_path = const.CELLS_DIR / f"cell_{r}_{c}.png"
            if not cell_path.exists():
                continue

            color = self.screen_processor.extract_color_from_cell(cell_path)
            if color is None:
                continue

            best_label = None
            best_distance = float("inf")
            second_best_distance = float("inf")

            for label, learned_colors in self.config["colors"].items():
                if not learned_colors:
                    continue

                distances = []
                for sample_color in learned_colors:
                    color_arr = np.array(color, dtype=np.float32)
                    sample_arr = np.array(sample_color, dtype=np.float32)
                    distance = np.sqrt(np.sum((color_arr - sample_arr) ** 2))
                    distances.append(distance)

                min_dist = min(distances) if distances else float("inf")

                if min_dist < best_distance:
                    second_best_distance = best_distance
                    best_distance = min_dist
                    best_label = label
                elif min_dist < second_best_distance:
                    second_best_distance = min_dist

            if best_distance < float("inf") and second_best_distance < float("inf"):
                if best_distance + second_best_distance > 0:
                    confidence = 1.0 - (
                        best_distance / (best_distance + second_best_distance)
                    )
                else:
                    confidence = 1.0
            else:
                confidence = 0.0

            threshold = self.adaptive_threshold

            if (
                best_distance < threshold
                and confidence > self.confidence_threshold
                and best_label
            ):
                if best_label == "adv":
                    self.board[r][c] = -1
                    continue
                else:
                    value = int(best_label)
                    self.board[r][c] = value
                    confidence_board[r][c] = confidence

                    # авто-добавление цвета для крупных/новых чисел
                    if value > 512:
                        key = str(value)
                        if key not in colors_map:
                            colors_map[key] = []

                        auto_color = self.screen_processor.extract_color_from_cell(
                            cell_path
                        )
                        if auto_color is not None:
                            samples = colors_map[key]
                            samples.append
    return self.board, confidence_board

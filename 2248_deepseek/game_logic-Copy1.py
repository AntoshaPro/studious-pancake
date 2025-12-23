# game_logic.py
import time
import random
from collections import deque
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
import constants as const


class GameLogic:
    def __init__(self, config_manager, screen_processor):
        self.config_manager = config_manager
        self.config = config_manager.config
        self.screen_processor = screen_processor
        self.board = [[-1 for _ in range(const.COLS)] for _ in range(const.ROWS)]
        self.confidence_threshold = 0.7
        self.adaptive_threshold = self.config.get("threshold", 8000)
        self.current_move_attempts = 0
        self.last_move_hash = None
        self.last_move_type = None
        self.last_move_direction = None
        self.ad_end_detector = None

    def set_ad_detector(self, detector):
        self.ad_end_detector = detector

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

                if number == 0:
                    key = "adv"
                else:
                    key = str(number)

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

    def recognize_board_with_confidence(self):
        if not self.config.get("calibrated", False):
            print("❌ Бот не обучен!")
            return None, None

        self.board = [[-1 for _ in range(const.COLS)] for _ in range(const.ROWS)]
        confidence_board = [[0.0 for _ in range(const.COLS)] for _ in range(const.ROWS)]

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
                    else:
                        self.board[r][c] = int(best_label)
                    confidence_board[r][c] = confidence
                else:
                    self.board[r][c] = -1
                    confidence_board[r][c] = confidence

                    if best_label not in (None, "adv"):
                        self.remember_problem_cell(
                            cell_path, color, best_label, best_distance, confidence
                        )

        return self.board, confidence_board

    def remember_problem_cell(
        self, cell_path, color, guessed_label, distance, confidence
    ):
        color_list = [int(c) for c in color]

        problem = {
            "cell": str(cell_path),
            "color": color_list,
            "guessed_label": str(guessed_label),
            "distance": float(distance),
            "confidence": float(confidence),
            "timestamp": datetime.now().isoformat(),
        }

        self.config_manager.problem_cells.append(problem)
        if len(self.config_manager.problem_cells) > 50:
            self.config_manager.problem_cells = self.config_manager.problem_cells[-50:]

        if len(self.config_manager.problem_cells) % 5 == 0:
            self.config_manager.save_problem_cells()

    def get_board_hash(self):
        return hash(str(self.board))

    def find_all_chains(self):
        directions = [
            (0, 1),
            (1, 0),
            (0, -1),
            (-1, 0),
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1),
        ]

        all_chains = []

        for r in range(const.ROWS):
            for c in range(const.COLS):
                start_val = self.board[r][c]
                if start_val <= 0:
                    continue

                stack = [([(r, c)], start_val, {(r, c)})]

                while stack:
                    current_path, current_val, visited = stack.pop()

                    if len(current_path) >= 2:
                        if self.is_valid_chain(current_path):
                            all_chains.append(current_path.copy())

                    last_r, last_c = current_path[-1]

                    for dr, dc in directions:
                        nr, nc = last_r + dr, last_c + dc

                        if not (0 <= nr < const.ROWS and 0 <= nc < const.COLS):
                            continue
                        if (nr, nc) in visited:
                            continue

                        next_val = self.board[nr][nc]
                        if next_val <= 0:
                            continue

                        if next_val == current_val or next_val == current_val * 2:
                            new_path = current_path + [(nr, nc)]
                            new_visited = visited.copy()
                            new_visited.add((nr, nc))
                            stack.append((new_path, next_val, new_visited))

        return self._filter_chains(all_chains)

    def is_valid_chain(self, chain):
        if len(chain) < 2:
            return False

        (r1, c1), (r2, c2) = chain[0], chain[1]
        if self.board[r1][c1] != self.board[r2][c2]:
            return False

        current_val = self.board[r1][c1]
        for i in range(2, len(chain)):
            r, c = chain[i]
            val = self.board[r][c]
            if val not in (current_val, current_val * 2):
                return False
            current_val = val

        return True

    def _filter_chains(self, chains):
        if not chains:
            return []

        chains.sort(key=len, reverse=True)
        filtered = []
        seen_cells = set()

        for chain in chains:
            chain_cells = frozenset(chain)
            if chain_cells not in seen_cells:
                is_maximal = True
                for other_chain in filtered:
                    if set(chain).issubset(set(other_chain)):
                        is_maximal = False
                        break

                if is_maximal:
                    filtered.append(chain)
                    seen_cells.add(chain_cells)

        return filtered

    def is_straight_chain(self, chain):
        if len(chain) < 2:
            return False

        r1, c1 = chain[0]
        r2, c2 = chain[1]
        dr, dc = r2 - r1, c2 - c1

        for i in range(2, len(chain)):
            r_prev, c_prev = chain[i - 1]
            r_curr, c_curr = chain[i]
            if (r_curr - r_prev != dr) or (c_curr - c_prev != dc):
                return False

        return True

    def evaluate_chain_smart(self, chain):
        """
        Умная оценка цепочки с учётом стратегических последствий.
        """
        if not chain:
            return -999999

        # 1. Базовые показатели
        base_value = sum(self.board[r][c] for r, c in chain)
        length_bonus = len(chain) * 100

        # 2. Штраф за слишком длинные цепочки (они оставляют мало вариантов)
        if len(chain) > 5:
            length_penalty = (len(chain) - 5) * 40  # Жёсткий штраф за длинные цепочки
        else:
            length_penalty = 0

        # 3. Вес позиций (центр важнее)
        position_weight = 0
        center_r, center_c = const.ROWS // 2, const.COLS // 2
        for r, c in chain:
            distance = abs(r - center_r) + abs(c - center_c)
            position_weight += max(0, 10 - distance * 2)
        position_bonus = position_weight * 3

        # 4. Штраф за разрушение "мостов" (пар соседей вне цепочки)
        bridge_penalty = 0
        for r, c in chain:
            cell_value = self.board[r][c]
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < const.ROWS and 0 <= nc < const.COLS:
                    if (nr, nc) not in chain:
                        neighbor_value = self.board[nr][nc]
                        if neighbor_value > 0 and self.is_potential_pair(
                            cell_value, neighbor_value
                        ):
                            # Штраф зависит от значения клетки и важности пары
                            penalty = 20 * (cell_value // 64)
                            # Дополнительный штраф, если это единственная пара для клетки
                            if self.count_potential_pairs(nr, nc) == 1:
                                penalty *= 2
                            bridge_penalty += penalty

        # 5. Бонус за очистку рекламных/пустых клеток вокруг
        cleanup_bonus = 0
        for r, c in chain:
            for dr, dc in [
                (0, 1),
                (1, 0),
                (0, -1),
                (-1, 0),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < const.ROWS and 0 <= nc < const.COLS:
                    if self.board[nr][nc] == -1:
                        cleanup_bonus += 5

        # 6. Штраф за изоляцию крупных чисел
        isolation_penalty = 0
        if len(chain) >= 2:
            chain_values = [self.board[r][c] for r, c in chain]
            for value in chain_values:
                if value >= 128:  # Средние и крупные числа
                    # Проверяем, останутся ли на доске такие же числа после хода
                    same_values_left = False
                    for r in range(const.ROWS):
                        for c in range(const.COLS):
                            if (r, c) not in chain and self.board[r][c] == value:
                                same_values_left = True
                                break
                        if same_values_left:
                            break
                    if not same_values_left:
                        # Чем больше число и чем меньше осталось других чисел, тем больше штраф
                        isolation_penalty += 30 * (value // 128)

        # 7. Бонус за создание новых потенциальных пар после хода
        future_pair_bonus = 0
        simulated = [row[:] for row in self.board]
        for r, c in chain:
            simulated[r][c] = -1

        # Проверяем, появляются ли новые пары после удаления цепочки
        for r in range(const.ROWS):
            for c in range(const.COLS):
                if simulated[r][c] > 0:
                    for dr, dc in [(0, 1), (1, 0)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < const.ROWS and 0 <= nc < const.COLS:
                            if (
                                simulated[nr][nc] > 0
                                and simulated[r][c] == simulated[nr][nc]
                            ):
                                future_pair_bonus += 25 * (simulated[r][c] // 64)

        # 8. Штраф за удаление клеток с большим количеством соседей
        connectivity_penalty = 0
        for r, c in chain:
            neighbor_count = 0
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < const.ROWS and 0 <= nc < const.COLS:
                    if self.board[nr][nc] > 0:
                        neighbor_count += 1
            if neighbor_count >= 3:
                connectivity_penalty += 15

        # Итоговая оценка
        total_score = (
            base_value
            + length_bonus
            - length_penalty
            + position_bonus
            + cleanup_bonus
            + future_pair_bonus
            - bridge_penalty
            - isolation_penalty
            - connectivity_penalty
        )

        return total_score

    def is_potential_pair(self, val1, val2):
        """Проверяет, могут ли два значения образовать пару (равны или одно вдвое больше другого)."""
        return val1 == val2 or val1 * 2 == val2 or val2 * 2 == val1

    def count_potential_pairs(self, r, c):
        """Считает количество потенциальных пар для клетки."""
        count = 0
        cell_value = self.board[r][c]
        if cell_value <= 0:
            return 0

        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < const.ROWS and 0 <= nc < const.COLS:
                if self.is_potential_pair(cell_value, self.board[nr][nc]):
                    count += 1
        return count

    def find_best_chain_smart(self, board_hash):
        """
        Улучшенный поиск цепочки с учётом стратегических последствий.
        """
        chains = self.find_all_chains()

        if not chains:
            return None

        # Группируем цепочки по длине
        chains_by_length = {}
        for chain in chains:
            length = len(chain)
            if length not in chains_by_length:
                chains_by_length[length] = []
            chains_by_length[length].append(chain)

        # Сначала рассматриваем цепочки средней длины (3-5 клеток)
        optimal_lengths = [4, 5, 3, 6, 2, 7, 8, 9]

        for length in optimal_lengths:
            if length in chains_by_length:
                valid_chains = []
                for chain in chains_by_length[length]:
                    move_key = f"chain_{len(chain)}_{chain[0][0]}_{chain[0][1]}_{chain[-1][0]}_{chain[-1][1]}"
                    if not self.is_move_blacklisted(board_hash, move_key):
                        valid_chains.append(chain)

                if valid_chains:
                    # Выбираем лучшую цепочку этой длины по умной оценке
                    best_chain = max(
                        valid_chains, key=lambda c: self.evaluate_chain_smart(c)
                    )
                    chain_score = self.evaluate_chain_smart(best_chain)

                    # Если оценка хорошая, возвращаем её
                    if chain_score > 100 or length <= 5:
                        return best_chain

        # Если не нашли подходящей, возвращаем лучшую из всех по оценке
        all_valid_chains = []
        for chain in chains:
            move_key = f"chain_{len(chain)}_{chain[0][0]}_{chain[0][1]}_{chain[-1][0]}_{chain[-1][1]}"
            if not self.is_move_blacklisted(board_hash, move_key):
                all_valid_chains.append(chain)

        if all_valid_chains:
            return max(all_valid_chains, key=lambda c: self.evaluate_chain_smart(c))

        return None

    def simulate_board_after_move(self, chain):
        """
        Простая симуляция доски после хода.
        Возвращает количество полезных клеток и количество пар.
        """
        # Создаём копию доски
        simulated = [row[:] for row in self.board]

        # Удаляем клетки цепочки (помечаем как -1)
        for r, c in chain:
            simulated[r][c] = -1

        # Подсчитываем полезные клетки (не рекламные)
        useful_cells = 0
        for r in range(const.ROWS):
            for c in range(const.COLS):
                if simulated[r][c] > 0:
                    useful_cells += 1

        # Подсчитываем пары соседей (потенциальные будущие цепочки)
        neighbor_pairs = 0
        for r in range(const.ROWS):
            for c in range(const.COLS):
                if simulated[r][c] > 0:
                    if c + 1 < const.COLS and simulated[r][c] == simulated[r][c + 1]:
                        neighbor_pairs += 1
                    if r + 1 < const.ROWS and simulated[r][c] == simulated[r + 1][c]:
                        neighbor_pairs += 1

        return useful_cells, neighbor_pairs

    def is_move_blacklisted(self, board_hash, move_key):
        return move_key in self.config_manager.bad_moves.get(board_hash, [])

    def remember_bad_move(self, move_context):
        board_hash = move_context.get("board_state", "")
        move_key = f"{move_context.get('move_type', 'unknown')}_{move_context.get('direction', 'unknown')}"

        if board_hash:
            self.config_manager.bad_moves[board_hash].append(move_key)
            if len(self.config_manager.bad_moves[board_hash]) > 5:
                self.config_manager.bad_moves[board_hash] = (
                    self.config_manager.bad_moves[board_hash][-5:]
                )

            self.config_manager.save_bad_moves()
            print(f"📝 Запомнил плохой ход: {move_key}")

    def to_abs_coords(self, x_px, y_px):
        if not self.config.get("grid"):
            return x_px, y_px

        if self.screen_processor.gx_min is None:
            self.screen_processor._init_grid_bounds()

        gx_min, gx_max = self.screen_processor.gx_min, self.screen_processor.gx_max
        gy_min, gy_max = self.screen_processor.gy_min, self.screen_processor.gy_max

        if gx_max == gx_min:
            x_norm = 0.5
        else:
            x_norm = (x_px - gx_min) / (gx_max - gx_min)

        if gy_max == gy_min:
            y_norm = 0.5
        else:
            y_norm = (y_px - gy_min) / (gy_max - gy_min)

        x_norm = min(max(x_norm, 0.0), 1.0)
        y_norm = min(max(y_norm, 0.0), 1.0)

        x_abs = int(const.X_MIN + x_norm * (const.X_MAX - const.X_MIN))
        y_abs = int(const.Y_MIN + y_norm * (const.Y_MAX - const.Y_MIN))
        return x_abs, y_abs

    def perform_chain_swipe_mt(self, chain, steps=1, pressure=1024):
        if not chain or len(chain) < 2:
            print("❌ Неверная цепочка для свайпа")
            return False

        print(f"🔗 [MT] Цепочка из {len(chain)} клеток:")
        for i, (r, c) in enumerate(chain):
            print(f" {i+1}: [{r},{c}] = {self.board[r][c]}")

        all_points = []
        for i in range(len(chain) - 1):
            start_r, start_c = chain[i]
            end_r, end_c = chain[i + 1]

            sx_px, sy_px = self.config["grid"][start_r][start_c]
            ex_px, ey_px = self.config["grid"][end_r][end_c]

            start_x, start_y = self.to_abs_coords(sx_px, sy_px)
            end_x, end_y = self.to_abs_coords(ex_px, ey_px)

            for s in range(steps + 1):
                t = s / steps
                x = int(start_x + (end_x - start_x) * t)
                y = int(start_y + (end_y - start_y) * t)
                if not all_points or (x, y) != all_points[-1]:
                    all_points.append((x, y))

        if not all_points:
            return False

        script_lines = []
        x0, y0 = all_points[0]
        script_lines += [
            f"sendevent {const.EVENT_DEV} 3 57 0",
            f"sendevent {const.EVENT_DEV} 3 53 {x0}",
            f"sendevent {const.EVENT_DEV} 3 54 {y0}",
            f"sendevent {const.EVENT_DEV} 3 58 {pressure}",
            f"sendevent {const.EVENT_DEV} 1 330 1",
            f"sendevent {const.EVENT_DEV} 0 0 0",
        ]

        for x, y in all_points[1:]:
            script_lines += [
                f"sendevent {const.EVENT_DEV} 3 53 {x}",
                f"sendevent {const.EVENT_DEV} 3 54 {y}",
                f"sendevent {const.EVENT_DEV} 3 58 {pressure}",
                f"sendevent {const.EVENT_DEV} 0 0 0",
            ]

        script_lines += [
            f"sendevent {const.EVENT_DEV} 3 58 0",
            f"sendevent {const.EVENT_DEV} 3 57 -1",
            f"sendevent {const.EVENT_DEV} 1 330 0",
            f"sendevent {const.EVENT_DEV} 0 0 0",
        ]

        script = "; ".join(script_lines)
        cmd = f'adb shell "{script}"'
        return self.screen_processor.adb_command(cmd) is not None

    def run_auto_game(self, max_moves=100):
        print("\n" + "=" * 60)
        print("🤖 ЗАПУСК АВТОМАТИЧЕСКОЙ ИГРЫ 2248 С ОБУЧЕНИЕМ")
        print("=" * 60)

        if not self.config.get("calibrated", False):
            print("❌ Бот не готов к игре!")
            return

        for move in range(1, max_moves + 1):
            print(f"\n🎯 Ход #{move}/{max_moves}")

            # 1. Скриншот и проверка рекламы
            self.screen_processor.take_screenshot("current.png")
            if self.screen_processor.detect_advertisement("current.png"):
                if not self.screen_processor.wait_for_advertisement():
                    print("❌ Не удалось продолжить после рекламы")
                    break
                self.screen_processor.take_screenshot(f"move_{move}.png")
            else:
                self.screen_processor.take_screenshot(f"move_{move}.png")

            # 2. Обрезка клеток и распознавание
            self.screen_processor.crop_cells_from_screen(f"move_{move}.png")
            board, confidence_board = self.recognize_board_with_confidence()
            if board is None:
                print("❌ Не удалось распознать доску")
                break

            # 3. Логика хода
            board_before = self.get_board_hash()

            if self.last_move_hash == board_before:
                self.current_move_attempts += 1
                print(
                    f"⚠️ Повторная попытка того же хода ({self.current_move_attempts}/2)"
                )
            else:
                self.current_move_attempts = 1
                self.last_move_hash = board_before

            if self.current_move_attempts >= 2:
                print("🚫 Две неудачные попытки! Выбираю другой ход...")
                if self.last_move_type:
                    self.remember_bad_move(
                        {
                            "board_state": board_before,
                            "move_type": self.last_move_type,
                            "direction": self.last_move_direction,
                        }
                    )
                self.current_move_attempts = 0

            # 4. УМНЫЙ поиск цепочки
            best_chain = self.find_best_chain_smart(board_before)

            if best_chain:
                useful_cells, neighbor_pairs = self.simulate_board_after_move(
                    best_chain
                )
                chain_score = self.evaluate_chain_smart(best_chain)

                print(
                    f"🔗 Умная цепочка из {len(best_chain)} клеток (оценка: {chain_score})"
                )
                print(
                    f"   Прогноз: останется {useful_cells} полезных клеток, {neighbor_pairs} потенциальных пар"
                )

                self.last_move_type = "chain"
                self.last_move_direction = f"{best_chain[0][0]}_{best_chain[0][1]}_{best_chain[-1][0]}_{best_chain[-1][1]}"

                # Свайп через ABS_MT (sendevent)
                if self.perform_chain_swipe_mt(best_chain, steps=1):
                    print("✅ Ход выполнен (MT)")
                else:
                    print("❌ Ошибка выполнения хода (MT)")
                    break

            else:
                # 5. Резервный вариант...
                print("⚠️ Цепочки не найдены! Делаю случайный свайп...")
                self.last_move_type = "random"
                directions = ["up", "down", "left", "right"]
                random.shuffle(directions)

                direction_chosen = None
                center_x, center_y = self.config["grid"][const.ROWS // 2][
                    const.COLS // 2
                ]

                for direction in directions:
                    move_key = f"random_{direction}"
                    if self.is_move_blacklisted(board_before, move_key):
                        continue
                    if (
                        self.last_move_type == "random"
                        and self.last_move_direction == direction
                    ):
                        continue
                    direction_chosen = direction
                    break

                if not direction_chosen:
                    direction_chosen = random.choice(directions)

                self.last_move_direction = direction_chosen

                if direction_chosen == "up":
                    x1_px, y1_px = center_x, center_y + 1500
                    x2_px, y2_px = center_x, center_y - 300
                elif direction_chosen == "down":
                    x1_px, y1_px = center_x, center_y - 200
                    x2_px, y2_px = center_x, center_y + 1500
                elif direction_chosen == "left":
                    x1_px, y1_px = center_x + 1200, center_y
                    x2_px, y2_px = center_x - 300, center_y
                else:  # right
                    x1_px, y1_px = center_x - 200, center_y
                    x2_px, y2_px = center_x + 1300, center_y

                x1_abs, y1_abs = self.to_abs_coords(x1_px, y1_px)
                x2_abs, y2_abs = self.to_abs_coords(x2_px, y2_px)

                script_lines = [
                    f"sendevent {const.EVENT_DEV} 3 57 0",
                    f"sendevent {const.EVENT_DEV} 3 53 {x1_abs}",
                    f"sendevent {const.EVENT_DEV} 3 54 {y1_abs}",
                    f"sendevent {const.EVENT_DEV} 3 58 1024",
                    f"sendevent {const.EVENT_DEV} 1 330 1",
                    f"sendevent {const.EVENT_DEV} 0 0 0",
                    f"sendevent {const.EVENT_DEV} 3 53 {x2_abs}",
                    f"sendevent {const.EVENT_DEV} 3 54 {y2_abs}",
                    f"sendevent {const.EVENT_DEV} 0 0 0",
                    f"sendevent {const.EVENT_DEV} 3 58 0",
                    f"sendevent {const.EVENT_DEV} 3 57 -1",
                    f"sendevent {const.EVENT_DEV} 1 330 0",
                    f"sendevent {const.EVENT_DEV} 0 0 0",
                ]

                script = "; ".join(script_lines)
                cmd = f'adb shell "{script}"'
                if not self.screen_processor.adb_command(cmd):
                    print("🎮 ИГРА ОКОНЧЕНА!")
                    break

            time.sleep(0.5)

        print("\n" + "=" * 60)
        print("🏁 АВТОМАТИЧЕСКАЯ ИГРА ЗАВЕРШЕНА!")
        print("=" * 60)

    # Вспомогательный метод для отладки
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
                        conf_mark = "✓" if conf > 0.8 else "~" if conf > 0.6 else "?"
                        conf_str += f"{conf_mark:^{max_len}} "
                    else:
                        conf_str += " " * max_len + " "
            print(row_str)
            if confidence_board:
                print(conf_str)
        print("=" * 50)

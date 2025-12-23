# game_logic.py
import time
import random
from collections import deque
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path

import constants as const
from constants import AD_BTN_X, AD_BTN_Y, AD_CLOSE_POINTS
from ad_detector_2248 import EndGameAdDetector2248, send_tap_like_mouse
from end_game_handler import EndGameHandler
from heuristics_2248 import Heuristics2248


class GameLogic:
    def __init__(self, config_manager, screen_processor, input_controller):
        self.config_manager = config_manager
        self.config = config_manager.config
        self.screen_processor = screen_processor
        self.input = input_controller  # контроллер ввода

        self.board = [[-1 for _ in range(const.COLS)] for _ in range(const.ROWS)]
        self.confidence_threshold = 0.7
        self.adaptive_threshold = self.config.get("threshold", 8000)

        self.current_move_attempts = 0
        self.last_move_hash = None
        self.last_move_type = None
        self.last_move_direction = None

        self.ad_end_detector = None
        self.show_board_each_move = False

        self.ad_detector = EndGameAdDetector2248()
        self.end_handler = EndGameHandler(self.screen_processor)
        
        # Initialize heuristics engine
        self.heuristics = Heuristics2248(self)

    def set_ad_detector(self, detector):
        self.ad_end_detector = detector

    # ===== РАСПОЗНАВАНИЕ ДОСКИ =====

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

    # ===== ПОИСК ЦЕПОЧЕК =====

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
        # Delegate to the heuristics engine
        return self.heuristics.evaluate_chain(chain)

    def is_potential_pair(self, val1, val2):
        return val1 == val2 or val1 * 2 == val2 or val2 * 2 == val1

    def count_potential_pairs(self, r, c):
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
        chains = self.find_all_chains()

        if not chains:
            return None

        chains_by_length = {}
        for chain in chains:
            length = len(chain)
            if length not in chains_by_length:
                chains_by_length[length] = []
            chains_by_length[length].append(chain)

        optimal_lengths = [4, 5, 3, 6, 2, 7, 8, 9]

        for length in optimal_lengths:
            if length in chains_by_length:
                valid_chains = []
                for chain in chains_by_length[length]:
                    move_key = (
                        f"chain_{len(chain)}_{chain[0][0]}_{chain[0][1]}_"
                        f"{chain[-1][0]}_{chain[-1][1]}"
                    )
                    if not self.is_move_blacklisted(board_hash, move_key):
                        valid_chains.append(chain)

                if valid_chains:
                    best_chain = max(
                        valid_chains, key=lambda c: self.evaluate_chain_smart(c)
                    )
                    chain_score = self.evaluate_chain_smart(best_chain)

                    if chain_score > 100 or length <= 5:
                        return best_chain

        all_valid_chains = []
        for chain in chains:
            move_key = (
                f"chain_{len(chain)}_{chain[0][0]}_{chain[0][1]}_"
                f"{chain[-1][0]}_{chain[-1][1]}"
            )
            if not self.is_move_blacklisted(board_hash, move_key):
                all_valid_chains.append(chain)

        if all_valid_chains:
            return max(all_valid_chains, key=lambda c: self.evaluate_chain_smart(c))

        return None

    def simulate_board_after_move(self, chain):
        simulated = [row[:] for row in self.board]

        for r, c in chain:
            simulated[r][c] = -1

        useful_cells = 0
        for r in range(const.ROWS):
            for c in range(const.COLS):
                if simulated[r][c] > 0:
                    useful_cells += 1

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


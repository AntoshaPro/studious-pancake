import time
import random
from collections import deque
import json  # для optimal_orders.json
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path

import constants as const
from constants import AD_BTN_X, AD_BTN_Y, AD_CLOSE_POINTS, ORDER_FILE
from ad_detector_2248 import EndGameAdDetector2248, send_tap_like_mouse
from end_game_handler import EndGameHandler
from heuristics_2248 import Heuristics2248
from find_best_chain_smart import find_best_chain_smart as find_best_chain_smart_fn
from remember_problem_cell import remember_problem_cell as remember_problem_cell_fn
from find_all_chains import find_all_chains as find_all_chains_fn
from evaluate_chain_smart import evaluate_chain_smart as evaluate_chain_smart_fn
from recognize_board_with_confidence import (
    recognize_board_with_confidence as recognize_board_with_confidence_fn,
)
from good_moves_manager import GoodMovesManager
from position_memory import PositionMemory


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
        self.position_memory = PositionMemory()

        # сохраняем хорошие ходы
        self.good_moves = GoodMovesManager()
        # подключение конца рекламы
        self.ad_end_detector = None
        self.show_board_each_move = True
        self.ad_detector = EndGameAdDetector2248()
        self.end_handler = None

        # кэш цепочек по хешу доски
        self.chain_cache: dict[int, list[tuple[int, int]]] = {}

        # ==== Порядки длин цепочек (для перебора стратегий) ====
        self.current_order_index: int = 0
        self.optimal_lengths: list[int] = [
            4,
            5,
            3,
            6,
            2,
            7,
            8,
            9,
        ]  # [8, 4, 2, 3, 6, 5, 7, 9]
        self.load_current_order()

    def load_current_order(self):
        """
        Загружает из ORDER_FILE (optimal_orders.json) текущий порядок длин.
        """
        if not ORDER_FILE.exists():
            print(
                "[ORDER] Файл с порядками не найден, использую дефолт:",
                self.optimal_lengths,
            )
            return

        try:
            data = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("[ORDER] Ошибка чтения JSON, использую дефолтный порядок.")
            return

        orders = data.get("orders", [])
        idx = data.get("current_index", 0)  # Default to 0 instead of 1 to match array indexing
        if not orders:
            print("[ORDER] В JSON нет orders, использую дефолтный порядок.")
            return

        self.current_order_index = idx % len(orders)
        self.optimal_lengths = orders[self.current_order_index]
        print(f"[ORDER] Порядок #{self.current_order_index}: {self.optimal_lengths}")
        
        # Store stats reference for later use
        self.order_stats = data.get("stats", {})

    def set_ad_detector(self, detector):
        self.ad_end_detector = detector

    # ===== РАСПОЗНАВАНИЕ ДОСКИ / ПАМЯТЬ ПОЗИЦИЙ =====

    def on_new_board(self):
        board_hash = self.get_board_hash()  # Zobrist
        if self.position_memory.was_seen(board_hash):
            print("[POSITION] Уже видел такую конфигурацию (в т.ч. в прошлых играх)")
        else:
            print("[POSITION] Новая конфигурация доски")
            self.position_memory.mark_seen(board_hash)

    def recognize_board_with_confidence(self):
        return recognize_board_with_confidence_fn(self)

    def remember_problem_cell(
        self, cell_path, color, guessed_label, distance, confidence
    ):
        return remember_problem_cell_fn(
            self, cell_path, color, guessed_label, distance, confidence
        )

    # ===== ХЕШ ДОСКИ =====

    def get_board_hash(self):
        h = 0
        for r in range(const.ROWS):
            for c in range(const.COLS):
                v = self.board[r][c]
                if v < 0:
                    v = 0
                if v > const.MAX_VALUE:
                    v = const.MAX_VALUE
                h ^= const.ZOBRIST_TABLE[(r, c, v)]
        return h

    # ===== ПОИСК ЦЕПОЧЕК =====

    def find_all_chains(self):
        return find_all_chains_fn(self)

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
        return evaluate_chain_smart_fn(self, chain)

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

    def find_best_chain_smart(self, board_hash: int):
        # пробуем достать из кэша

        if board_hash in self.chain_cache:
            print("[CACHE HIT]", board_hash)
            return self.chain_cache[board_hash]

        print("[CACHE MISS]", board_hash)
        print("[ORDER-RUN] current optimal_lengths:", self.optimal_lengths)
        # вызываем вынесенную функцию с порядком из JSON
        best_chain = find_best_chain_smart_fn(
            self.board,
            board_hash,
            self.is_move_blacklisted,
            self.evaluate_chain_smart,
            self.find_all_chains,
            optimal_lengths=self.optimal_lengths,
        )

        # кладём в кэш, если нашли цепочку
        if best_chain is not None:
            self.chain_cache[board_hash] = best_chain

        return best_chain

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

    def remember_good_move(self, board_hash, move_type, direction, score):
        move_key = f"{move_type}_{direction}"
        self.good_moves.remember_good_move(board_hash, move_key, score)

    def get_known_good_moves(self, board_hash):
        return self.good_moves.get_good_moves(board_hash)

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

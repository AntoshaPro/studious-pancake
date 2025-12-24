"""
Enhanced GameLogic with adaptive chain evaluation, profile selection,
and learning integration for the 2248 bot project
"""
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
from learning_engine import LearningEngine
from game_state_recognition import GameStateRecognizer


class EnhancedGameLogic:
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
        
        # Initialize learning engine for adaptive evaluation
        self.learning_engine = LearningEngine()
        
        # Initialize game state recognizer
        self.game_state_recognizer = GameStateRecognizer()
        
        # History of move success for adaptive evaluation
        self.move_success_history = {}
        
        # Adaptive weights for chain evaluation
        self.evaluation_weights = {
            'length': 0.3,
            'potential_merges': 0.25,
            'board_entropy': 0.2,
            'max_tile_position': 0.15,
            'empty_cells': 0.1
        }

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
        """Enhanced evaluation with adaptive weights from learning engine"""
        # Get base evaluation
        base_score = evaluate_chain_smart_fn(self, chain)
        
        # Enhance with learned features
        features = self._analyze_chain_features(chain)
        learned_score = 0.0
        
        for feature_name, feature_value in features.items():
            weight = self.evaluation_weights.get(feature_name, 0.1)
            learned_score += weight * feature_value
        
        # Combine base and learned scores
        final_score = base_score + learned_score * 10  # Scale learned score appropriately
        
        # Update move success history for learning
        chain_key = str(sorted(chain))
        if chain_key not in self.move_success_history:
            self.move_success_history[chain_key] = {'attempts': 0, 'successes': 0, 'total_score': 0}
        self.move_success_history[chain_key]['attempts'] += 1
        self.move_success_history[chain_key]['total_score'] += final_score
        
        return final_score

    def _analyze_chain_features(self, chain):
        """Analyze features of a chain for adaptive evaluation"""
        features = {}
        
        # Chain length feature
        features['length'] = len(chain) / 9  # Normalize by max possible length
        
        # Potential merges after this move
        simulated_board = self._simulate_board_after_chain(chain)
        potential_merges = self._count_potential_merges(simulated_board)
        features['potential_merges'] = potential_merges / 20  # Normalize
        
        # Board entropy after move (measure of randomness)
        entropy = self._calculate_board_entropy(simulated_board)
        features['board_entropy'] = entropy / 5  # Normalize
        
        # Position of max tile after move (prefer corner positions)
        max_val = max(max(row) for row in simulated_board if any(cell > 0 for cell in row))
        max_positions = [(r, c) for r, row in enumerate(simulated_board) 
                        for c, val in enumerate(row) if val == max_val]
        if max_positions:
            corner_positions = [(0, 0), (0, 3), (3, 0), (3, 3)]
            is_corner = any(pos in corner_positions for pos in max_positions)
            features['max_tile_position'] = 1.0 if is_corner else 0.3
        else:
            features['max_tile_position'] = 0.1
        
        # Empty cells after move
        empty_cells = sum(1 for row in simulated_board for cell in row if cell == 0)
        features['empty_cells'] = empty_cells / (const.ROWS * const.COLS)
        
        return features

    def _simulate_board_after_chain(self, chain):
        """Simulate the board state after a chain move"""
        simulated = [row[:] for row in self.board]
        
        # Apply the chain (remove cells and let tiles fall)
        for r, c in chain:
            simulated[r][c] = -1  # Mark as empty
        
        # Simple simulation: fill empty spaces with -1
        # In a more complex implementation, this would handle gravity and merging
        return simulated

    def _count_potential_merges(self, board):
        """Count potential merges on the board"""
        potential_merges = 0
        for r in range(const.ROWS):
            for c in range(const.COLS):
                if board[r][c] > 0:
                    # Check right neighbor
                    if c + 1 < const.COLS and board[r][c] == board[r][c + 1]:
                        potential_merges += 1
                    # Check bottom neighbor
                    if r + 1 < const.ROWS and board[r][c] == board[r + 1][c]:
                        potential_merges += 1
        return potential_merges

    def _calculate_board_entropy(self, board):
        """Calculate entropy of the board (measure of randomness)"""
        values = [cell for row in board for cell in row if cell > 0]
        if not values:
            return 0
        
        unique_values = set(values)
        entropy = -sum((values.count(v) / len(values)) * 
                      np.log2(values.count(v) / len(values)) 
                      for v in unique_values if values.count(v) > 0)
        return entropy

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
        
        # Dynamic profile selection based on current board state and learning
        try:
            import json
            from constants import ORDERS_FILE
            if ORDERS_FILE.exists():
                data = json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
                orders = data.get("orders", [])
                if orders:
                    # Adapt strategy based on current board and historical performance
                    new_profile = self.learning_engine.adapt_strategy(self.board, orders)
                    if new_profile != self.optimal_lengths:
                        self.optimal_lengths = new_profile
                        print(f"[STRATEGY] Profile updated to: {new_profile}")
        except Exception as e:
            print(f"[STRATEGY] Error adapting strategy: {e}")
        
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
        
        # Update learning engine about successful move
        chain_key = f"{board_hash}_{move_key}"
        if chain_key in self.move_success_history:
            self.move_success_history[chain_key]['successes'] += 1
            self.learning_engine.update_move_success(board_hash, (0, 0), True)  # Simplified

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
            
            # Update learning engine about unsuccessful move
            chain_key = f"{board_hash}_{move_key}"
            if chain_key in self.move_success_history:
                self.learning_engine.update_move_success(board_hash, (0, 0), False)  # Simplified
    
    def detect_game_over(self, screen_image):
        """
        Detect if the game is over (win or loss)
        
        Args:
            screen_image: Current game screen image
            
        Returns:
            Tuple of (is_game_over, result_type) where result_type is 'win', 'loss', or None
        """
        return self.game_state_recognizer.detect_game_over(screen_image)
    
    def detect_win_condition(self, target_tile=2248):
        """
        Detect win by checking if target tile exists on board
        
        Args:
            target_tile: Target tile value to win (default 2248)
            
        Returns:
            True if win condition is met
        """
        return self.game_state_recognizer.detect_win_condition(self.board, target_tile)
    
    def is_game_lost(self):
        """
        Check if the game is lost by checking if board is full and no moves are possible
        
        Returns:
            True if no moves are possible
        """
        # Check if board is full
        is_full = all(self.board[r][c] != -1 for r in range(const.ROWS) for c in range(const.COLS))
        
        if not is_full:
            return False
        
        # Check if any adjacent cells have the same value or can merge
        for r in range(const.ROWS):
            for c in range(const.COLS):
                current_val = self.board[r][c]
                if current_val <= 0:
                    continue
                
                # Check right neighbor
                if c + 1 < const.COLS:
                    right_val = self.board[r][c + 1]
                    if (right_val == current_val or 
                        right_val == current_val * 2 or 
                        current_val == right_val * 2):
                        return False  # Found a possible move
                
                # Check bottom neighbor
                if r + 1 < const.ROWS:
                    bottom_val = self.board[r + 1][c]
                    if (bottom_val == current_val or 
                        bottom_val == current_val * 2 or 
                        current_val == bottom_val * 2):
                        return False  # Found a possible move
        
        return True  # No moves possible
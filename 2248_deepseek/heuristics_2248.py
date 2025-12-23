# heuristics_2248.py
import json
from pathlib import Path
import constants as const


class Heuristics2248:
    def __init__(self, game_logic, weights_path="heuristics_weights.json"):
        # game_logic нужен, чтобы читать board и вызывать его методы
        self.gl = game_logic
        self.weights_path = Path(weights_path)
        self.weights = self._load_weights()

    def _load_weights(self):
        if self.weights_path.exists():
            with open(self.weights_path, "r", encoding="utf-8") as f:
                return json.load(f)
        # дефолты, если файла нет
        return {
            "length_bonus": 80,
            "small_bonus": 100,
            "straight_bonus": 20,
            "open_cell_coef": 8,
            "pair_coef": 40,
            "bridge_penalty_base": 20,
            "isolation_penalty_base": 30,
            "center_penalty_base": 40,
        }

    def _save_weights(self):
        with open(self.weights_path, "w", encoding="utf-8") as f:
            json.dump(self.weights, f, ensure_ascii=False, indent=2)

    def evaluate_chain(self, chain):
        """
        Основная оценка цепочки. Здесь вся эвристика.
        """
        if not chain:
            return -999999

        w = self.weights  # все коэффициенты берём из конфига
        board = self.gl.board

        # 1. Базовая ценность
        base_value = sum(board[r][c] for r, c in chain)
        length_bonus = len(chain) * w["length_bonus"]

        # 1.1 Бонус за очистку мелких чисел (2,4,8,16)
        small_bonus = 0
        for r, c in chain:
            val = board[r][c]
            if val in (2, 4, 8, 16):
                small_bonus += w["small_bonus"]

        # 2. Штраф за слишком длинные цепочки
        if len(chain) > 5:
            length_penalty = (len(chain) - 5) * w.get("length_penalty_step", 40)
        else:
            length_penalty = 0

        # 3. Бонус за центр
        center_r, center_c = const.ROWS // 2, const.COLS // 2
        position_weight = 0
        for r, c in chain:
            distance = abs(r - center_r) + abs(c - center_c)
            position_weight += max(0, 10 - distance * 2)
        position_bonus = position_weight * 3

        # 4. Штраф за разрушение мостов
        bridge_penalty = 0
        for r, c in chain:
            cell_value = board[r][c]
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < const.ROWS and 0 <= nc < const.COLS:
                    if (nr, nc) not in chain:
                        neighbor_value = board[nr][nc]
                        if neighbor_value > 0 and self.gl.is_potential_pair(
                            cell_value, neighbor_value
                        ):
                            penalty = w["bridge_penalty_base"] * max(
                                1, cell_value // 64
                            )
                            if self.gl.count_potential_pairs(nr, nc) == 1:
                                penalty *= 2
                            bridge_penalty += penalty

        # 5. Бонус за очистку мусора вокруг
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
                    if board[nr][nc] == -1:
                        cleanup_bonus += 5

        # 6. Изоляция крупных чисел
        isolation_penalty = 0
        chain_values = [board[r][c] for r, c in chain]
        for value in chain_values:
            if value >= 128:
                same_values_left = False
                for r in range(const.ROWS):
                    for c in range(const.COLS):
                        if (r, c) not in chain and board[r][c] == value:
                            same_values_left = True
                            break
                    if same_values_left:
                        break
                if not same_values_left:
                    isolation_penalty += w["isolation_penalty_base"] * max(
                        1, value // 128
                    )

        # 7. Мелкий бонус за прямую цепочку
        straight_bonus = (
            w["straight_bonus"] if self.gl.is_straight_chain(chain) else 0
        )

        # 8. Взгляд вперёд: используем симуляцию
        useful_cells, neighbor_pairs = self.gl.simulate_board_after_move(chain)
        open_cells_bonus = useful_cells * w["open_cell_coef"]
        pair_bonus = neighbor_pairs * w["pair_coef"]

        # 9. Штраф за очень крупные числа в центре
        center_penalty = 0
        for r in range(const.ROWS):
            for c in range(const.COLS):
                val = board[r][c]
                if val >= 256:
                    dist = abs(r - center_r) + abs(c - center_c)
                    if dist <= 1:
                        center_penalty += w["center_penalty_base"] * max(
                            1, val // 256
                        )

        total_score = (
            base_value
            + length_bonus
            + position_bonus
            + cleanup_bonus
            + straight_bonus
            + open_cells_bonus
            + pair_bonus
            + small_bonus
            - length_penalty
            - bridge_penalty
            - isolation_penalty
            - center_penalty
        )

        print(f"HEUR: len={len(chain)} base={base_value} score={total_score}")

        return total_score

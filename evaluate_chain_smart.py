# evaluate_chain_smart.py
import constants as const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_logic import GameLogic


def evaluate_chain_smart(self: 'GameLogic', chain):
    print("[EVAL_FN] called, len(chain) =", len(chain))
    if not chain:
        return -999999

    # --- базовая эвристика как было ---
    base_value = sum(self.board[r][c] for r, c in chain)
    length_bonus = len(chain) * 100

    if len(chain) > 5:
        length_penalty = (len(chain) - 5) * 40
    else:
        length_penalty = 0

    # позиционный бонус
    position_weight = 0
    center_r, center_c = const.ROWS // 2, const.COLS // 2
    for r, c in chain:
        distance = abs(r - center_r) + abs(c - center_c)
        position_weight += max(0, 10 - distance * 2)
    position_bonus = position_weight * 3

    # штраф за разрушение потенциальных пар
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
                        penalty = 20 * (cell_value // 64)
                        if self.count_potential_pairs(nr, nc) == 1:
                            penalty *= 2
                        bridge_penalty += penalty

    # бонус за "зачистку" вокруг
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

    # штраф за изоляцию крупных чисел
    isolation_penalty = 0
    if len(chain) >= 2:
        chain_values = [self.board[r][c] for r, c in chain]
        for value in chain_values:
            if value >= 128:
                same_values_left = False
                for rr in range(const.ROWS):
                    for cc in range(const.COLS):
                        if (rr, cc) not in chain and self.board[rr][cc] == value:
                            same_values_left = True
                            break
                    if same_values_left:
                        break
                if not same_values_left:
                    isolation_penalty += 30 * (value // 128)

    # --- ЛОКАЛЬНАЯ СИМУЛЯЦИЯ ПОСЛЕ ХОДА ---
    simulated = [row[:] for row in self.board]
    for r, c in chain:
        simulated[r][c] = -1

    empty_after = 0
    for r in range(const.ROWS):
        for c in range(const.COLS):
            if simulated[r][c] <= 0:
                empty_after += 1

    max_before = 0
    for r in range(const.ROWS):
        for c in range(const.COLS):
            if self.board[r][c] > max_before:
                max_before = self.board[r][c]

    max_after = 0
    for r in range(const.ROWS):
        for c in range(const.COLS):
            if simulated[r][c] > max_after:
                max_after = simulated[r][c]

    # --- 1) Бонус/штраф за пустые клетки ---
    empty_bonus = 0
    if empty_after < 3:
        empty_bonus -= 150
    elif empty_after < 5:
        empty_bonus -= 50
    else:
        empty_bonus += min(empty_after * 5, 100)

    # --- 2) Контроль "угла силы" ---
    corner_r, corner_c = const.ROWS - 1, 0

    corner_bonus = 0
    max_pos_before = None
    for r in range(const.ROWS):
        for c in range(const.COLS):
            if self.board[r][c] == max_before:
                max_pos_before = (r, c)
                break
        if max_pos_before:
            break

    max_pos_after = None
    for r in range(const.ROWS):
        for c in range(const.COLS):
            if simulated[r][c] == max_after:
                max_pos_after = (r, c)
                break
        if max_pos_after:
            break

    def manhattan(p, q):
        return abs(p[0] - q[0]) + abs(p[1] - q[1])

    if max_pos_before and max_pos_after:
        dist_before = manhattan(max_pos_before, (corner_r, corner_c))
        dist_after = manhattan(max_pos_after, (corner_r, corner_c))

        if dist_after < dist_before:
            corner_bonus += 100 * (max_after // 1024)
        elif dist_after > dist_before:
            corner_bonus -= 120 * (max_after // 1024)

    # --- 3) Бонус за рост максимального тайла ---
    growth_bonus = 0
    if max_after > max_before:
        growth_bonus += 200 * (max_after // 1024)

    # бонус пар будущих
    future_pair_bonus = 0
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

    total_score = (
        base_value
        + length_bonus
        - length_penalty
        + position_bonus
        + cleanup_bonus
        + future_pair_bonus
        + empty_bonus
        + corner_bonus
        + growth_bonus
        - bridge_penalty
        - isolation_penalty
        - connectivity_penalty
    )

    return total_score

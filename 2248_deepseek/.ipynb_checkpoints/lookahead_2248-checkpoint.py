# lookahead_2248.py
import copy
import constants as const


class Lookahead2248:
    def __init__(self, game_logic, heuristics):
        """
        game_logic — чтобы уметь находить цепочки и симулировать ходы.
        heuristics — чтобы оценивать цепочки.
        """
        self.gl = game_logic
        self.heur = heuristics

    def clone_board(self, board):
        return [row[:] for row in board]

    def simulate_chain_on_board(self, board, chain):
        """
        Простейшая симуляция: удаляем клетки цепочки.
        (Можно доработать, если у тебя есть более точная модель падения/спавна.)
        """
        new_board = self.clone_board(board)
        for r, c in chain:
            new_board[r][c] = -1
        return new_board

    def find_all_chains_on_board(self, board_state):
        """
        Используем существующий find_all_chains, но подсовываем свою доску.
        """
        original = self.gl.board
        self.gl.board = self.clone_board(board_state)
        chains = self.gl.find_all_chains()
        self.gl.board = original
        return chains

    def evaluate_with_lookahead(self, chain, depth=2):
        """
        Оценка цепочки с простым lookahead до depth ходов.
        depth=1  — как обычная эвристика.
        depth=2+ — смотрим лучший ответ на следующем ходе.
        """
        if not chain:
            return -999999

        # текущая доска
        board_now = self.clone_board(self.gl.board)

        # шаг 1: применяем цепочку к доске
        board_after = self.simulate_chain_on_board(board_now, chain)

        # базовая оценка первого хода
        base_score = self.heur.evaluate_chain(chain)

        if depth <= 1:
            return base_score

        # шаг 2: ищем цепочки на следующем ходе
        next_chains = self.find_all_chains_on_board(board_after)
        if not next_chains:
            # если после хода вообще нет цепочек, это почти тупик — штрафуем
            return base_score - 500

        # считаем максимальную оценку лучшего следующего хода
        best_next = -999999
        for ch2 in next_chains:
            # подменяем board в game_logic временно
            original = self.gl.board
            self.gl.board = self.clone_board(board_after)
            s2 = self.heur.evaluate_chain(ch2)
            self.gl.board = original

            if s2 > best_next:
                best_next = s2

        # комбинируем: текущий ход + доля следующего
        # 0.5 — вес влияния следующего хода, можно крутить
        total = base_score + 0.5 * best_next
        print(
            f"LA: len={len(chain)} base={base_score} "
            f"next_best={best_next} total={total}"
        )

        return total

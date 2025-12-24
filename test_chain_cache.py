# test_chain_cache.py
from game_logic import GameLogic
from config_manager import ConfigManager
from screen_processor import ScreenProcessor
from input_controller import InputController
from constants import ROWS, COLS
import time


def make_dummy_logic():
    cm = ConfigManager()
    sp = ScreenProcessor(cm)
    ic = InputController(sp)
    gl = GameLogic(cm, sp, ic)
    return gl


def main():
    gl = make_dummy_logic()

    # создаём пустую доску нужного размера
    gl.board = [[-1 for _ in range(COLS)] for _ in range(ROWS)]

    # захардкодим тестовую позицию (5x4)
    gl.board[0] = [2, 4, 8, 16]
    gl.board[1] = [32, 64, 128, 256]
    gl.board[2] = [512, 512, 1024, 2048]
    gl.board[3] = [0, 0, 4096, 8192]
    # gl.board[4] оставляем как [-1, -1, -1, -1]

    h = gl.get_board_hash()

    # первый вызов — без кэша
    t0 = time.time()
    best1 = gl.find_best_chain_smart(h)
    t1 = time.time()
    print("Первый вызов:", best1, "время:", t1 - t0)

    # второй вызов — должен попасть в кэш
    t2 = time.time()
    best2 = gl.find_best_chain_smart(h)
    t3 = time.time()
    print("Второй вызов (кэш):", best2, "время:", t3 - t2)

def find_best_chain_smart(self, board_hash):
    if board_hash in self.chain_cache:
        print("[CACHE HIT]", board_hash)
        return self.chain_cache[board_hash]

    print("[CACHE MISS]", board_hash)
    chains = self.find_all_chains()
    best_chain, best_score = self.evaluate_chains(chains)
    self.chain_cache[board_hash] = best_chain
    return best_chain

if __name__ == "__main__":
    main()

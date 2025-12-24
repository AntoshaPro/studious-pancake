# board_test.py
from position_memory import PositionMemory
import constants as const

def main():
    pm = PositionMemory()

    board = [
        [128,  64, 128, 512],
        [256, 512, 256, 256],
        [  2,   2,   2, 256],
        [ 64,  16,   8, 256],
        [1024, 64,  16, 2048],
    ]

    # считаем тот же Zobrist-хэш, что в GameLogic.get_board_hash
    h = 0
    for r in range(const.ROWS):
        for c in range(const.COLS):
            v = board[r][c]
            if v < 0:
                v = 0
            if v > const.MAX_VALUE:
                v = const.MAX_VALUE
            h ^= const.ZOBRIST_TABLE[(r, c, v)]

    print(f"hash = {h:016x}")

    print("=== Первый вызов ===")
    if pm.was_seen(h):
        print("Уже видел (ОШИБКА, не должен)")
    else:
        print("Новая конфигурация (ОК)")
        pm.mark_seen(h)

    print("=== Второй вызов ===")
    if pm.was_seen(h):
        print("Уже видел такую конфигурацию (ОК)")
    else:
        print("Новая конфигурация (ОШИБКА)")

if __name__ == "__main__":
    main()

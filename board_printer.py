# board_printer.py
import constants as const


def print_board(board, confidence_board=None):
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

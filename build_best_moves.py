# build_best_moves.py
import json
from pathlib import Path

from position_memory import SEEN_BOARDS_FILE  # seen_boards.json
from find_best_chain_smart import find_best_chain_smart as find_best_chain_smart_fn
from game_logic import GameLogic
from config_manager import ConfigManager
from screen_processor import ScreenProcessor
from input_controller import InputController

BEST_MOVES_FILE = Path("best_moves.json")


def load_seen_hashes():
    if not SEEN_BOARDS_FILE.exists():
        return []
    data = json.loads(SEEN_BOARDS_FILE.read_text(encoding="utf-8"))
    hashes = data.get("seen_hashes", [])
    return [int(h, 16) for h in hashes]


def main():
    # Инициализируем окружение, как в боте
    cfg = ConfigManager()
    sp = ScreenProcessor(cfg)
    ic = InputController(cfg)
    gl = GameLogic(cfg, sp, ic)

    seen_hashes = load_seen_hashes()
    print(f"[BUILD] Найдено {len(seen_hashes)} уникальных позиций")

    best_moves: dict[str, dict] = {}

    for h in seen_hashes:
        h_hex = f"{h:016x}"
        print(f"\n[BUILD] Обработка позиции {h_hex}")

        # ТУТ ВОПРОС: откуда взять board по этому хэшу?
        # В тестовом варианте можно:
        # - либо уже иметь сохранённые board-ы где-то в файлах;
        # - либо пропустить этот шаг и просто показать структуру.

        board = gl.board  # заглушка: нужно заменить на реальную загрузку доски

        best_chain = find_best_chain_smart_fn(
            board,
            h,
            gl.is_move_blacklisted,
            gl.evaluate_chain_smart,
            gl.find_all_chains,
        )

        if not best_chain:
            print("[BUILD] Нет допустимых цепочек")
            continue

        score = gl.evaluate_chain_smart(best_chain)
        print(f"[BUILD] Лучшая цепочка: {best_chain}, score={score:.1f}")

        best_moves[h_hex] = {
            "chain": best_chain,
            "score": score,
            "length": len(best_chain),
        }

    BEST_MOVES_FILE.write_text(
        json.dumps(best_moves, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[BUILD] best_moves.json сохранён ({len(best_moves)} позиций)")


if __name__ == "__main__":
    main()

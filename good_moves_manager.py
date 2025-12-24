# good_moves_manager.py
import json
from collections import defaultdict
from pathlib import Path

from constants import GOOD_MOVES_FILE


class GoodMovesManager:
    def __init__(self):
        self._moves = defaultdict(list)
        self._loaded = False

    # ===== ВНУТРЕННЕЕ =====

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True

        if GOOD_MOVES_FILE.exists():
            try:
                with open(GOOD_MOVES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # ключи в json строковые → приводим к int
                self._moves = defaultdict(list, {int(k): v for k, v in data.items()})
                print(
                    f"📖 [GOOD] Загружено "
                    f"{sum(len(v) for v in self._moves.values())} хороших ходов"
                )
            except Exception as e:
                print(f"⚠️ Не удалось загрузить good_moves: {e}")
                self._moves = defaultdict(list)

    def _save(self):
        GOOD_MOVES_FILE.parent.mkdir(exist_ok=True, parents=True)
        data = {str(k): v for k, v in self._moves.items()}
        with open(GOOD_MOVES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        # можно без принта, чтобы не заспамить

    # ===== ПУБЛИЧНОЕ API =====

    def remember_good_move(self, board_hash: int, move_key: str, score: float):
        """Сохранить/обновить хороший ход для данного состояния."""
        self._ensure_loaded()

        entry = {"move_key": move_key, "score": float(score)}
        moves = self._moves[board_hash]

        # если уже есть такой move_key — обновим score, если стал лучше
        for m in moves:
            if m["move_key"] == move_key:
                if score > m.get("score", 0.0):
                    m["score"] = float(score)
                break
        else:
            moves.append(entry)

        # держим топ-N по score
        moves.sort(key=lambda x: x["score"], reverse=True)
        self._moves[board_hash] = moves[:5]

        self._save()
        print(f"⭐ [GOOD] Запомнил хороший ход: {move_key} (score={score})")

    def get_good_moves(self, board_hash: int):
        """Получить список известных хороших ходов для состояния."""
        self._ensure_loaded()
        return list(self._moves.get(board_hash, []))

    def clear_all(self):
        """Полностью очистить все хорошие ходы (по желанию)."""
        self._moves.clear()
        if GOOD_MOVES_FILE.exists():
            GOOD_MOVES_FILE.unlink(missing_ok=True)
        print("🧹 [GOOD] Все хорошие ходы очищены")

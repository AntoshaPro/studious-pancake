# position_memory.py
from typing import Set
from pathlib import Path
import json

SEEN_BOARDS_FILE = Path("seen_boards.json")


class PositionMemory:
    """
    Память позиций по Zobrist-хэшу в JSON.
    Формат файла:
    {
      "seen_hashes": ["0000ab12...", "00ff34..."]
    }
    """

    def __init__(self) -> None:
        self.seen_hashes: Set[int] = set()
        self._load_from_file()

    # ====== Работа с файлом ======

    def _load_from_file(self) -> None:
        if not SEEN_BOARDS_FILE.exists():
            return
        try:
            data = json.loads(SEEN_BOARDS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return

        hashes = data.get("seen_hashes", [])
        for h_str in hashes:
            try:
                h = int(h_str, 16)
                self.seen_hashes.add(h)
            except ValueError:
                continue

    def _save_to_file(self) -> None:
        data = {
            "seen_hashes": [f"{h:016x}" for h in self.seen_hashes],
        }
        SEEN_BOARDS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ====== Публичный API ======

    def was_seen(self, board_hash: int) -> bool:
        """
        Проверить, видели ли уже такую доску.
        """
        return board_hash in self.seen_hashes

    def mark_seen(self, board_hash: int) -> None:
        """
        Отметить доску как виденную и сохранить в JSON.
        """
        if board_hash in self.seen_hashes:
            return
        self.seen_hashes.add(board_hash)
        self._save_to_file()

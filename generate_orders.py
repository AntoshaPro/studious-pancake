# generate_orders.py
from itertools import permutations
import json
from pathlib import Path

from constants import ORDERS_FILE  # optimal_orders.json

BASE_LENGTHS = [8, 4, 5, 3, 6, 2, 7, 9]


def main():
    all_orders = [list(p) for p in permutations(BASE_LENGTHS)]
    print(f"Всего порядков: {len(all_orders)}")  # 40320

    # для каждого порядка заводим статистику: ключи "0", "1", ...
    stats = {
        str(i): {"games": 0, "total_score": 0.0}
        for i in range(len(all_orders))
    }

    data = {
        "base": BASE_LENGTHS,
        "orders": all_orders,
        "current_index": 0,
        "stats": stats,
    }

    ORDERS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Сохранено в {ORDERS_FILE}")


if __name__ == "__main__":
    main()

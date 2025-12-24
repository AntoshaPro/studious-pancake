import json
from pathlib import Path

ORDER_FILE = Path("optimal_orders.json")

def main():
    if not ORDER_FILE.exists():
        print(f"❌ Файл {ORDER_FILE} не найден")
        return

    data = json.loads(ORDER_FILE.read_text(encoding="utf-8"))

    orders = data.get("orders", [])
    if not orders:
        print("❌ В JSON нет поля 'orders'")
        return

    # ПЕРЕЗАПИСЫВАЕМ stats полностью как dict "index" -> {...}
    stats = {}
    for i in range(len(orders)):
        stats[str(i)] = {"games": 0, "total_score": 0}

    data["stats"] = stats

    # Если нет current_index — ставим 0
    if "current_index" not in data:
        data["current_index"] = 0

    ORDER_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ Проиндексировано профилей: {len(orders)}")
    print(f"   current_index = {data['current_index']}")
    print(f"   stats keys = {list(data['stats'].keys())}")

if __name__ == "__main__":
    main()

# learning_stats.py
from collections import Counter


class LearningStats:
    def __init__(self, config_manager):
        self.cm = config_manager

    def print_stats(self):
        cfg = self.cm.config
        colors = cfg.get("colors", {})

        print("\n" + "=" * 60)
        print("📈 СТАТИСТИКА ОБУЧЕНИЯ РАСПОЗНАВАНИЮ")
        print("=" * 60)

        if not colors:
            print("❌ В конфиге нет цветов.")
            return

        # 1. Сколько образцов на каждый label
        print("\n🎨 Образцы цветов по значениям:")
        counts = []
        for label, samples in sorted(colors.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999999):
            counts.append((label, len(samples)))
        for label, cnt in counts:
            print(f"  {label:>6}: {cnt:3d} образцов")

        # 2. Мини/макси по выборкам
        nums = [int(l) for l, _ in counts if l.isdigit()]
        if nums:
            print("\n🏷 Диапазон численных тайлов в цветах:")
            print(f"  min: {min(nums)}, max: {max(nums)}")

        # 3. Служебные параметры обучения
        print("\n⚙️ Параметры обучения:")
        print(f"  min_samples: {cfg.get('min_samples')}")
        print(f"  max_samples: {cfg.get('max_samples')}")
        print(f"  learning_rate: {cfg.get('learning_rate')}")
        print(f"  threshold (цвет): {cfg.get('threshold')}")
        print(f"  last_updated: {cfg.get('last_updated')}")
        print("\n" + "=" * 60)

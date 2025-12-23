# config_manager.py
import json
from pathlib import Path
from collections import defaultdict, deque
import constants as const


class ConfigManager:
    def __init__(self):
        self.config = self.load_config()
        self.problem_cells = []
        self.bad_moves = defaultdict(list)
        self.recognition_history = deque(maxlen=50)
        self.load_problem_cells()
        self.load_bad_moves()

    def load_config(self):
        if const.CONFIG_FILE.exists():
            try:
                with open(const.CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    print("✅ Конфигурация загружена")
                    if "colors" in config and config["colors"]:
                        first_key = next(iter(config["colors"]))
                        if not isinstance(config["colors"][first_key], list):
                            print("🔄 Конвертирую формат цветов...")
                            new_colors = {}
                            for num, color in config["colors"].items():
                                new_colors[num] = [color]
                            config["colors"] = new_colors
                    return config
            except json.JSONDecodeError:
                print("⚠️ Файл конфигурации поврежден, создаю новый...")
                return const.DEFAULT_CONFIG.copy()
        else:
            print("🆕 Создана новая конфигурация")
            config = const.DEFAULT_CONFIG.copy()
            use_preset = input(
                "\n🎯 Использовать предустановленные координаты сетки? (y/n): "
            ).lower()
            config["use_preset"] = use_preset == "y"
            return config

    def save_config(self):
        from datetime import datetime
        self.config["last_updated"] = datetime.now().isoformat()
        if "colors" in self.config:
            cleaned_colors = {}
            for num, color_list in self.config["colors"].items():
                cleaned_list = []
                for color in color_list:
                    if isinstance(color, (list, tuple)):
                        cleaned_list.append([int(c) for c in color])
                    else:
                        cleaned_list.append(
                            [int(color[0]), int(color[1]), int(color[2])]
                        )
                cleaned_colors[num] = cleaned_list
            self.config["colors"] = cleaned_colors

        with open(const.CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2, default=const.json_serializer)
        print("💾 Конфигурация сохранена")

    def load_problem_cells(self):
        if const.PROBLEMS_FILE.exists():
            try:
                with open(const.PROBLEMS_FILE, "r") as f:
                    self.problem_cells = json.load(f).get("problems", [])
                    print(f"📖 Загружено {len(self.problem_cells)} проблемных клеток")
            except:
                self.problem_cells = []

    def save_problem_cells(self):
        data = {"problems": self.problem_cells[-50:]}
        for problem in data["problems"]:
            if "color" in problem and isinstance(problem["color"], (list, tuple)):
                problem["color"] = [int(c) for c in problem["color"]]

        with open(const.PROBLEMS_FILE, "w") as f:
            json.dump(data, f, indent=2, default=const.json_serializer)

    def load_bad_moves(self):
        if const.BAD_MOVES_FILE.exists():
            try:
                with open(const.BAD_MOVES_FILE, "r") as f:
                    self.bad_moves = defaultdict(list, json.load(f))
                    print(
                        f"📖 Загружено {sum(len(v) for v in self.bad_moves.values())} плохих ходов"
                    )
            except:
                self.bad_moves = defaultdict(list)

    def save_bad_moves(self):
        with open(const.BAD_MOVES_FILE, "w") as f:
            json.dump(dict(self.bad_moves), f, indent=2)

    def reset_all(self):
        """Сбросить все настройки"""
        self.config = const.DEFAULT_CONFIG.copy()
        self.problem_cells = []
        self.recognition_history.clear()
        self.bad_moves.clear()

        for file in [const.CONFIG_FILE, const.PROBLEMS_FILE, const.BAD_MOVES_FILE]:
            if file.exists():
                file.unlink(missing_ok=True)

        print("✅ Все настройки сброшены")

    def show_problem_cells(self):
        """Показать накопленные проблемные клетки с деталями."""
        if not self.problem_cells:
            print("📦 Нет проблемных клеток для отображения")
            return
        
        print(f"\n📋 Найдено {len(self.problem_cells)} проблемных клеток:")
        print("-" * 80)
        
        for i, problem in enumerate(self.problem_cells, 1):
            path = problem.get("path", "N/A")
            color = problem.get("color", [0, 0, 0])
            confidence = problem.get("confidence", 0)
            recognized_as = problem.get("recognized_as", "N/A")
            timestamp = problem.get("timestamp", "N/A")
            
            print(f"{i:2d}. Файл: {path}")
            print(f"    Цвет: RGB{color} | Распознано как: {recognized_as} | Уверенность: {confidence:.2f}")
            print(f"    Время: {timestamp}")
            print()
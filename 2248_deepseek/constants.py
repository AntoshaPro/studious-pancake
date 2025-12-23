# constants.py
from pathlib import Path
from datetime import datetime
import json

# Размеры доски
ROWS, COLS = 5, 4

# Папки и файлы
CELLS_DIR = Path("cells")
CELLS_DIR.mkdir(exist_ok=True)

MOVES_DIR = Path("moves")
MOVES_DIR.mkdir(exist_ok=True)

CONFIG_FILE = Path("config.json")
PROBLEMS_FILE = Path("problem_cells.json")
BAD_MOVES_FILE = Path("bad_moves.json")

# Предустановленные координаты сетки
PRESET_LINES = {
    "L0_LEFT": (250, 1000),
    "L0_RIGHT": (1100, 1000),
    "L1_LEFT": (250, 1400),
    "L1_RIGHT": (1100, 1400),
    "L2_LEFT": (250, 1570),
    "L2_RIGHT": (1100, 1570),
    "L3_LEFT": (250, 2000),
    "L3_RIGHT": (1100, 2000),
    "L4_LEFT": (250, 2150),
    "L4_RIGHT": (1100, 2150),
    "L5_LEFT": (250, 2550),
    "L5_RIGHT": (1100, 2550),
}

# Конфигурация по умолчанию
DEFAULT_CONFIG = {
    "calibrated": False,
    "grid": [],
    "colors": {},
    "threshold": 8000,
    "last_updated": None,
    "use_preset": False,
    "learning_rate": 0.1,
    "min_samples": 3,
    "max_samples": 20,
    "ad_timeout": 60,
    "max_same_move_attempts": 2,
}

# ABS_MT границы поля (из getevent)
X_MIN = 6021
X_MAX = 27404
Y_MIN = 12495
Y_MAX = 24980

EVENT_DEV = "/dev/input/event1"

# Координаты кнопки рекламы
AD_BTN_X = 10483
AD_BTN_Y = 30007
AD_CLOSE_POINTS = [
    (30475, 4227),
    (27500, 3690),
    # добавишь свои варианты
]

RESTART_BTN_X = 23941
RESTART_BTN_Y = 30412

# Папка и порог детектора конца игры
END_SCREENS_DIR = Path("end_screens")
END_MSE_THRESHOLD = 200.0

# JSON сериализатор для numpy и дат
def json_serializer(obj):
    import numpy as np

    if isinstance(obj, (np.integer, np.floating)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (datetime,)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

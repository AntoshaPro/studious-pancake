# end_game_handler.py
from pathlib import Path
import time
import cv2
import numpy as np
import constants as const


class EndGameHandler:
    def __init__(self, screen_processor):
        self.sp = screen_processor
        self.threshold = const.END_MSE_THRESHOLD
        folder=const.END_SCREENS_DIR,
        self.restart_xy = (const.RESTART_BTN_X, const.RESTART_BTN_Y)
        self.win_templates, self.lose_templates = self._load_templates(
            const.END_SCREENS_DIR
        )

    def _mse(self, a, b):
        a = a.astype("float32")
        b = b.astype("float32")
        return np.mean((a - b) ** 2)

    def _load_templates(self, folder):
        win_dir = Path(folder) / "win"
        lose_dir = Path(folder) / "lose"

        win_tmpls, lose_tmpls = [], []

        for path in sorted(list(win_dir.glob("*.png")) + list(win_dir.glob("*.jpg"))):
            img = cv2.imread(str(path))
            if img is not None:
                win_tmpls.append(img)
                print(f"✅ Загружен win-шаблон: {path}")

        for path in sorted(list(lose_dir.glob("*.png")) + list(lose_dir.glob("*.jpg"))):
            img = cv2.imread(str(path))
            if img is not None:
                lose_tmpls.append(img)
                print(f"✅ Загружен lose-шаблон: {path}")

        return win_tmpls, lose_tmpls

    def classify_image(self, screen_bgr):
        """
        Вернёт 'win', 'lose' или None по cv2-кадру экрана.
        """
        if screen_bgr is None:
            return None

        h, w = screen_bgr.shape[:2]

        def resize_to_screen(tmpl):
            return cv2.resize(tmpl, (w, h))

        best_win = None
        for t in self.win_templates:
            t_res = resize_to_screen(t)
            val = self._mse(screen_bgr, t_res)
            best_win = val if best_win is None or val < best_win else best_win

        best_lose = None
        for t in self.lose_templates:
            t_res = resize_to_screen(t)
            val = self._mse(screen_bgr, t_res)
            best_lose = val if best_lose is None or val < best_lose else best_lose

        label = None
        if best_win is not None and best_win < self.threshold:
            label = "win"
        if best_lose is not None and best_lose < self.threshold:
            if label is None or best_lose < best_win:
                label = "lose"

        return label

    def check_and_restart(self):
        """
        Делает скрин, проверяет конец игры и при необходимости жмёт рестарт.
        Возвращает ('win' | 'lose' | None).
        """
        img = self.sp.grab_screen_cv2()
        label = self.classify_image(img)
        if label in ("win", "lose"):
            print(f"🏁 Обнаружен конец игры: {label}, перезапускаю...")
            self._tap_restart()
        return label

    def _tap_restart(self):
        x, y = self.restart_xy
        cmd = f"adb shell input tap {x} {y}"
        print(f"🔁 Тап по кнопке рестарта ({x}, {y})")
        self.sp.adb_command(cmd)
        time.sleep(2.0)

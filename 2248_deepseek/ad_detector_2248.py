# ad_detector_2248.py
import cv2
import numpy as np
import constants as const
from constants import EVENT_DEV, AD_BTN_X, AD_BTN_Y


def send_tap_like_mouse(adb_cmd, x, y, pressure=1024):
    """
    Tap в формате, как даёт эмулятор:
    TRACKING_ID -> POSITION_X/Y -> PRESSURE -> SYN
    потом PRESSURE=0 -> TRACKING_ID=-1 -> SYN
    """
    script_lines = [
        # палец вниз
        f"sendevent {EVENT_DEV} 3 57 0",
        f"sendevent {EVENT_DEV} 3 53 {x}",
        f"sendevent {EVENT_DEV} 3 54 {y}",
        f"sendevent {EVENT_DEV} 3 58 {pressure}",
        f"sendevent {EVENT_DEV} 0 0 0",
        # палец вверх
        f"sendevent {EVENT_DEV} 3 58 0",
        f"sendevent {EVENT_DEV} 3 57 -1",
        f"sendevent {EVENT_DEV} 0 0 0",
    ]

    cmd = 'adb shell "' + "; ".join(script_lines) + '"'
    return adb_cmd(cmd)


class EndGameAdDetector2248:
    """
    Детектор попапа 'нет ходов / посмотреть рекламу' в 2248.

    Работает по скриншоту (BGR-изображение OpenCV) и:
      - ищет шаблон кнопки в области интереса;
      - если не находит, использует fallback-координаты из констант.
    """

    def __init__(self):
        # шаблон кнопки
        self.button_template = None
        self.button_threshold = 0.75

        # область интереса (x1, y1, x2, y2), где обычно всплывает попап
        self.roi = None  # (x1, y1, x2, y2)

        # fallback-координаты (по умолчанию из констант)
        if hasattr(const, "AD_BTN_X") and hasattr(const, "AD_BTN_Y"):
            self.fallback_btn = (int(const.AD_BTN_X), int(const.AD_BTN_Y))
        else:
            self.fallback_btn = None

        self.use_fallback_if_not_found = True

    def set_roi(self, img_shape, roi_rel=(0.1, 0.2, 0.9, 0.8)):
        """
        Настроить область интереса относительно размера экрана.
        roi_rel = (left, top, right, bottom) в долях.
        """
        h, w = img_shape[:2]
        x1 = int(w * roi_rel[0])
        y1 = int(h * roi_rel[1])
        x2 = int(w * roi_rel[2])
        y2 = int(h * roi_rel[3])
        self.roi = (x1, y1, x2, y2)

    def load_button_template(self, path):
        """
        Загрузить шаблон кнопки 'Watch ad / Continue' из файла.
        Нужен заранее вырезанный фрагмент кнопки.
        """
        tmpl = cv2.imread(path)
        if tmpl is None:
            print(f"❌ Не удалось загрузить шаблон кнопки: {path}")
            return False
        self.button_template = tmpl
        print(f"✅ Шаблон кнопки загружен: {path}")
        return True

    def set_fallback_button(self, x, y):
        """
        Задать fallback-координаты кнопки для клика, если шаблон не найден.
        Координаты в пикселях экрана (raw-скрин).
        """
        self.fallback_btn = (int(x), int(y))
        print(f"🧷 Fallback-кнопка установлена: {self.fallback_btn}")

    def detect_endgame_popup(self, img):
        """
        Вернёт (is_popup, btn_x, btn_y) или (False, None, None).

        is_popup = True:
          – либо шаблон уверенно найден,
          – либо сработал fallback (когда мы уверены, что сейчас конец игры).
        """
        if img is None:
            return False, None, None

        if self.roi is None:
            self.set_roi(img.shape)  # дефолтная широкая область

        x1, y1, x2, y2 = self.roi
        roi = img[y1:y2, x1:x2]

        # 1. Если нет шаблона — сразу fallback, если он задан
        if self.button_template is None:
            if self.use_fallback_if_not_found and self.fallback_btn:
                fx, fy = self.fallback_btn
                return True, fx, fy
            return False, None, None

        # 2. Ищем кнопку по шаблону
        tmpl = self.button_template
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        tmpl_gray = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)

        res = cv2.matchTemplate(roi_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= self.button_threshold:
            # Центр найденной кнопки в координатах ROI
            th, tw = tmpl_gray.shape[:2]
            bx = max_loc[0] + tw // 2
            by = max_loc[1] + th // 2

            # Переводим в глобальные координаты экрана
            btn_x = x1 + bx
            btn_y = y1 + by
            return True, btn_x, btn_y

        # 3. Шаблон не дотянул до порога — используем fallback, если он есть
        if self.use_fallback_if_not_found and self.fallback_btn:
            fx, fy = self.fallback_btn
            return True, fx, fy

        # Ничего не нашли
        return False, None, None

    def tap_ad_button(self, adb_cmd, bx=None, by=None):
        """
        Нажать кнопку рекламы:
          - если переданы bx/by → жмём туда;
          - иначе берём fallback (константы / set_fallback_button).

        adb_cmd — функция вида screen_processor.adb_command.
        Вернёт True/False по факту успеха.
        """
        if adb_cmd is None:
            print("❌ adb_cmd не передан в tap_ad_button")
            return False

        # координаты кнопки
        if bx is None or by is None:
            if self.fallback_btn:
                bx, by = self.fallback_btn
            else:
                bx, by = AD_BTN_X, AD_BTN_Y

        x = int(bx)
        y = int(by)

        res = send_tap_like_mouse(adb_cmd, x, y)
        if not res:
            print("❌ Команда tap не выполнилась")
            return False

        print(f"✅ Нажал кнопку рекламы в точке ({bx}, {by})")
        return True

# screen_processor.py
import subprocess
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
import time
import constants as const
from ad_detector_2248 import EndGameAdDetector2248


class ScreenProcessor:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.config
        self.gx_min = None
        self.gx_max = None
        self.gy_min = None
        self.gy_max = None
        self.last_screen_hash = None
        self.static_frame_count = 0
        self._init_grid_bounds()

        # детектор попапа конца игры / рекламы (можно использовать здесь при желании)
        self.ad_detector = EndGameAdDetector2248()
        if hasattr(const, "AD_BTN_X") and hasattr(const, "AD_BTN_Y"):
            self.ad_detector.fallback_btn = (const.AD_BTN_X, const.AD_BTN_Y)

    def _init_grid_bounds(self):
        """Границы поля в пикселях по текущей grid."""
        if self.config.get("grid"):
            self.gx_min, self.gy_min = self.config["grid"][0][0]
            self.gx_max, _ = self.config["grid"][0][const.COLS - 1]
            _, self.gy_max = self.config["grid"][const.ROWS - 1][0]

    def create_grid_from_preset(self):
        lines_lr = [
            (const.PRESET_LINES["L0_LEFT"], const.PRESET_LINES["L0_RIGHT"]),
            (const.PRESET_LINES["L1_LEFT"], const.PRESET_LINES["L1_RIGHT"]),
            (const.PRESET_LINES["L2_LEFT"], const.PRESET_LINES["L2_RIGHT"]),
            (const.PRESET_LINES["L3_LEFT"], const.PRESET_LINES["L3_RIGHT"]),
            (const.PRESET_LINES["L4_LEFT"], const.PRESET_LINES["L4_RIGHT"]),
            (const.PRESET_LINES["L5_LEFT"], const.PRESET_LINES["L5_RIGHT"]),
        ]

        grid = []
        for r in range(const.ROWS):
            row = []
            (xL_top, yL_top), (xR_top, yR_top) = lines_lr[r]
            (xL_bot, yL_bot), (xR_bot, yR_bot) = lines_lr[r + 1]

            for c in range(const.COLS):
                t = c / (const.COLS - 1)
                x_top = xL_top + (xR_top - xL_top) * t
                y_top = yL_top + (yR_top - yL_top) * t
                x_bot = xL_bot + (xR_bot - xL_bot) * t
                y_bot = yL_bot + (yR_bot - yL_bot) * t
                x = int((x_top + x_bot) / 2)
                y = int((y_top + y_bot) / 2)
                row.append((x, y))
            grid.append(row)

        self.config["grid"] = grid
        self._init_grid_bounds()
        self.config_manager.save_config()
        return True

    def adb_command(self, cmd, capture_output=False):
        try:
            if capture_output:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return result.stdout.strip()
            else:
                subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
                return True
        except Exception:
            return None

    def check_adb(self):
        devices = self.adb_command("adb devices", capture_output=True)
        if devices and "device" in devices and "offline" not in devices:
            device_count = (
                len([line for line in devices.split("\n") if "device" in line]) - 1
            )
            print(f"✅ ADB подключен, устройств: {device_count}")
            return True
        else:
            print("❌ ADB не доступен. Проверьте подключение.")
            return False

    # Медленный вариант через файл — оставляем для отладки
    def take_screenshot(self, filename="screen.png"):
        return self.adb_command(f"adb exec-out screencap -p > {filename}")

    # Быстрый скриншот сразу в память
    def grab_screen_cv2(self):
        """
        Возвращает BGR-изображение экрана как cv2-матрицу без записи PNG на диск.
        """
        try:
            raw = subprocess.check_output(
                "adb exec-out screencap -p",
                shell=True,
            )
        except subprocess.CalledProcessError:
            return None

        img_array = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img

    def show_image(self, image_path, title="Изображение"):
        img = cv2.imread(str(image_path))
        if img is None:
            print(f"❌ Не удалось загрузить изображение: {image_path}")
            return

        h, w = img.shape[:2]
        scale = min(800 / w, 600 / h)
        if scale < 1:
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))

        cv2.imshow(title, img)
        print(f"👀 Смотрите изображение: {title}")
        print(" Нажмите любую клавишу в окне изображения чтобы продолжить...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # Старый вариант для совместимости (из файла)
    def crop_cells_from_screen(self, screen_path="screen.png", pad=150):
        if not Path(screen_path).exists():
            print(f"❌ Файл не найден: {screen_path}")
            return False

        if "grid" not in self.config or not self.config["grid"]:
            print("❌ Сетка не откалибрована!")
            return False

        img = Image.open(screen_path).convert("RGB")

        for r in range(const.ROWS):
            for c in range(const.COLS):
                x, y = self.config["grid"][r][c]
                box = (x - pad, y - pad, x + pad, y + pad)
                tile = img.crop(box)
                tile.save(const.CELLS_DIR / f"cell_{r}_{c}.png")

        print(f"✅ Клетки вырезаны в папку: {const.CELLS_DIR}")
        return True

    # Новый быстрый вариант — обрезка сразу из cv2-изображения
    def crop_cells_from_image(self, img_bgr, pad=150):
        if img_bgr is None:
            print("❌ Пустое изображение для crop_cells_from_image")
            return False

        if "grid" not in self.config or not self.config["grid"]:
            print("❌ Сетка не откалибрована!")
            return False

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        for r in range(const.ROWS):
            for c in range(const.COLS):
                x, y = self.config["grid"][r][c]
                box = (x - pad, y - pad, x + pad, y + pad)
                tile = pil_img.crop(box)
                tile.save(const.CELLS_DIR / f"cell_{r}_{c}.png")

        return True

    def extract_color_from_cell(self, cell_image):
        img = cv2.imread(str(cell_image))
        if img is None:
            return None

        img_small = cv2.resize(img, (50, 50))
        img_rgb = cv2.cvtColor(img_small, cv2.COLOR_BGR2RGB)
        pixels = img_rgb.reshape(-1, 3)
        pixels_float = np.float32(pixels)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels_float, 3, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )
        centers = np.uint8(centers)
        unique, counts = np.unique(labels, return_counts=True)
        dominant_idx = np.argmax(counts)
        dominant_color = centers[dominant_idx]
        return [int(dominant_color[0]), int(dominant_color[1]), int(dominant_color[2])]

    # Старый детектор — по файлу (можно уже не использовать)
    def detect_advertisement(self, screenshot_path="screen.png"):
        img = cv2.imread(screenshot_path)
        if img is None:
            return False
        return self.detect_advertisement_img(img)

    # Новый быстрый детектор — по cv2-изображению (эвристики, можно выкинуть)
    def detect_advertisement_img(self, img):
        return False
        if img is None:
            return False

        h, w = img.shape[:2]

        top_band = img[0:50, :]
        bottom_band = img[h - 50 : h, :]

        if np.mean(top_band) < 30 and np.mean(bottom_band) < 30:
            return False

        current_hash = self.image_hash(img)
        if self.last_screen_hash is not None:
            if current_hash == self.last_screen_hash:
                self.static_frame_count += 1
                if self.static_frame_count > 5:
                    return False
            else:
                self.static_frame_count = 0
        else:
            self.static_frame_count = 0

        self.last_screen_hash = current_hash
        return False

    def image_hash(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (8, 8))
        return hash(resized.tobytes())

    def wait_for_advertisement(self, ad_timeout=35):
        print("🎬 Обнаружена реклама. Ожидаю...")
        ad_start_time = time.time()
        max_wait = self.config.get("ad_timeout", ad_timeout)

        while time.time() - ad_start_time < max_wait:
            time.sleep(3)
            self.take_screenshot("check_ad.png")
            img = cv2.imread("check_ad.png")

            # если реклама исчезла — выходим
            if not self.detect_advertisement_img(img):
                print("✅ Реклама закончилась, продолжаем.")
                return True

            # периодически пытаемся нажать кнопку
            if int(time.time() - ad_start_time) % 15 == 0:
                print("⚠️ Пытаюсь нажать кнопку рекламы...")

                is_popup, bx, by = self.ad_detector.detect_endgame_popup(img)
                if is_popup and bx is not None and by is not None:
                    self.adb_command(f"adb shell input tap {bx} {by}")
                else:
                    if hasattr(const, "AD_BTN_X") and hasattr(const, "AD_BTN_Y"):
                        self.adb_command(
                            f"adb shell input tap {const.AD_BTN_X} {const.AD_BTN_Y}"
                        )
                time.sleep(2)

        print("❌ Реклама не исчезла, перезапускаю игру...")
        return False

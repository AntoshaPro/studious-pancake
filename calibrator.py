# calibrator.py
import cv2
import constants as const


class Calibrator:
    def __init__(self, config_manager, screen_processor):
        self.config_manager = config_manager
        self.sp = screen_processor

    def calibrate_quick(self):
        print("\n" + "=" * 60)
        print("⚡ БЫСТРАЯ КАЛИБРОВКА")
        print("=" * 60)

        if not self.sp.take_screenshot("quick_calib.png"):
            print("❌ Не удалось сделать скриншот")
            return False

        if self.sp.create_grid_from_preset():
            self.sp.crop_cells_from_screen("quick_calib.png")

            print("\n📸 Проверяем правильность калибровки...")
            img = cv2.imread("quick_calib.png")
            if img is not None:
                grid = self.config_manager.config["grid"]
                for r in range(const.ROWS):
                    for c in range(const.COLS):
                        x, y = grid[r][c]
                        color = (0, 255, 0)
                        cv2.line(img, (x - 20, y), (x + 20, y), color, 3)
                        cv2.line(img, (x, y - 20), (x, y + 20), color, 3)
                        cv2.putText(
                            img,
                            f"{r},{c}",
                            (x - 30, y - 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            color,
                            2,
                        )

                marked_img = "quick_calib_marked.png"
                cv2.imwrite(marked_img, img)

                img_display = cv2.imread(marked_img)
                cv2.imshow("ПРОВЕРКА: Крестики в центрах клеток?", img_display)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

                correct = input(
                    "\n❓ Правильно ли отмечены центры клеток? (y/n): "
                ).lower()
                if correct == "y":
                    print("✅ Быстрая калибровка завершена!")
                    return True
                else:
                    print("❌ Быстрая калибровка не удалась.")
                    return False

        return False

    def calibrate_smart(self):
        print("\n" + "=" * 60)
        print("🧠 УМНАЯ КАЛИБРОВКА")
        print("=" * 60)

        print("\n📸 Анализирую скриншот игры...")

        if not self.sp.take_screenshot("smart_calib.png"):
            return False

        img = cv2.imread("smart_calib.png")
        if img is None:
            print("❌ Не удалось загрузить скриншот")
            return False

        print("🔍 Ищу игровое поле...")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            print("❌ Не удалось найти игровое поле")
            return self.calibrate_quick()

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        print(f"✅ Нашел игровое поле: X={x}, Y={y}, Ширина={w}, Высота={h}")

        cell_width = w // const.COLS
        cell_height = h // const.ROWS

        grid = []
        for r in range(const.ROWS):
            row = []
            for c in range(const.COLS):
                cell_x = x + c * cell_width + cell_width // 2
                cell_y = y + r * cell_height + cell_height // 2
                row.append((cell_x, cell_y))
            grid.append(row)

        marked = img.copy()
        for r in range(const.ROWS):
            for c in range(const.COLS):
                cell_x, cell_y = grid[r][c]
                cv2.circle(marked, (cell_x, cell_y), 15, (0, 255, 0), 3)
                cv2.putText(
                    marked,
                    f"{r},{c}",
                    (cell_x - 20, cell_y - 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

        cv2.imwrite("smart_calib_marked.png", marked)

        img_display = cv2.imread("smart_calib_marked.png")
        cv2.imshow("УМНАЯ КАЛИБРОВКА: Найденные клетки", img_display)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        correct = input("\n❓ Правильно ли найдены клетки? (y/n): ").lower()
        if correct == "y":
            self.config_manager.config["grid"] = grid
            self.sp._init_grid_bounds()
            self.config_manager.save_config()
            print("✅ Умная калибровка завершена!")
            return True
        else:
            print("🔄 Перехожу к быстрой калибровке...")
            return self.calibrate_quick()

    def manual_adjust_grid(self, step=20):
        if not self.config_manager.config.get("grid"):
            print("❌ Сетка пустая, сначала калибровка")
            return

        while True:
            self.sp.take_screenshot("manual_grid.png")
            img = cv2.imread("manual_grid.png")
            grid = self.config_manager.config["grid"]
            for r in range(const.ROWS):
                for c in range(const.COLS):
                    x, y = grid[r][c]
                    color = (0, 255, 0)
                    cv2.line(img, (x - 20, y), (x + 20, y), color, 3)
                    cv2.line(img, (x, y - 20), (x, y + 20), color, 3)
                    cv2.putText(
                        img,
                        f"{r},{c}",
                        (x - 30, y - 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        color,
                        2,
                    )

            cv2.imshow("РУЧНАЯ ПОДГОНКА СЕТКИ (w/a/s/d, q - сохранить)", img)
            print("\nwasd = сдвиг, q = выйти/сохранить  (шаг =", step, ")")
            key = cv2.waitKey(0) & 0xFF

            if key == ord("q"):
                cv2.destroyAllWindows()
                self.sp._init_grid_bounds()
                self.config_manager.save_config()
                print("✅ Сетка сохранена после ручной подгонки")
                break

            dx, dy = 0, 0
            if key == ord("w"):
                dy = -step
            elif key == ord("s"):
                dy = step
            elif key == ord("a"):
                dx = -step
            elif key == ord("d"):
                dx = step
            else:
                print("⌨️ Используй только w/a/s/d/q")
                continue

            new_grid = []
            for row in self.config_manager.config["grid"]:
                new_row = []
                for x, y in row:
                    new_row.append((x + dx, y + dy))
                new_grid.append(new_row)
            self.config_manager.config["grid"] = new_grid
            print(f"➡️ Сдвинул на dx={dx}, dy={dy}")

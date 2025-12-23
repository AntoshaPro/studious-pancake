# input_controller.py
import constants as const


class InputController:
    def __init__(self, screen_processor):
        self.sp = screen_processor

    def to_abs_coords(self, config, x_px, y_px):
        if not config.get("grid"):
            return x_px, y_px

        if self.sp.gx_min is None:
            self.sp._init_grid_bounds()

        gx_min, gx_max = self.sp.gx_min, self.sp.gx_max
        gy_min, gy_max = self.sp.gy_min, self.sp.gy_max

        x_norm = 0.5 if gx_max == gx_min else (x_px - gx_min) / (gx_max - gx_min)
        y_norm = 0.5 if gy_max == gy_min else (y_px - gy_min) / (gy_max - gy_min)

        x_norm = min(max(x_norm, 0.0), 1.0)
        y_norm = min(max(y_norm, 0.0), 1.0)

        x_abs = int(const.X_MIN + x_norm * (const.X_MAX - const.X_MIN))
        y_abs = int(const.Y_MIN + y_norm * (const.Y_MAX - const.Y_MIN))
        return x_abs, y_abs

    def perform_chain_swipe_mt(self, config, chain, board, steps=1, pressure=1024):
        if not chain or len(chain) < 2:
            print("❌ Неверная цепочка для свайпа")
            return False

        print(f"🔗 [MT] Цепочка из {len(chain)} клеток:")
        for i, (r, c) in enumerate(chain):
            print(f" {i+1}: [{r},{c}] = {board[r][c]}")

        all_points = []
        for i in range(len(chain) - 1):
            start_r, start_c = chain[i]
            end_r, end_c = chain[i + 1]

            sx_px, sy_px = config["grid"][start_r][start_c]
            ex_px, ey_px = config["grid"][end_r][end_c]

            start_x, start_y = self.to_abs_coords(config, sx_px, sy_px)
            end_x, end_y = self.to_abs_coords(config, ex_px, ey_px)

            for s in range(steps + 1):
                t = s / steps
                x = int(start_x + (end_x - start_x) * t)
                y = int(start_y + (end_y - start_y) * t)
                if not all_points or (x, y) != all_points[-1]:
                    all_points.append((x, y))

        if not all_points:
            return False

        script_lines = []
        x0, y0 = all_points[0]
        script_lines += [
            f"sendevent {const.EVENT_DEV} 3 57 0",
            f"sendevent {const.EVENT_DEV} 3 53 {x0}",
            f"sendevent {const.EVENT_DEV} 3 54 {y0}",
            f"sendevent {const.EVENT_DEV} 3 58 {pressure}",
            f"sendevent {const.EVENT_DEV} 1 330 1",
            f"sendevent {const.EVENT_DEV} 0 0 0",
        ]

        for x, y in all_points[1:]:
            script_lines += [
                f"sendevent {const.EVENT_DEV} 3 53 {x}",
                f"sendevent {const.EVENT_DEV} 3 54 {y}",
                f"sendevent {const.EVENT_DEV} 3 58 {pressure}",
                f"sendevent {const.EVENT_DEV} 0 0 0",
            ]

        script_lines += [
            f"sendevent {const.EVENT_DEV} 3 58 0",
            f"sendevent {const.EVENT_DEV} 3 57 -1",
            f"sendevent {const.EVENT_DEV} 1 330 0",
            f"sendevent {const.EVENT_DEV} 0 0 0",
        ]

        script = "; ".join(script_lines)
        cmd = f'adb shell "{script}"'
        return self.sp.adb_command(cmd) is not None

# tap_tester.py
import time
from constants import EVENT_DEV  # /dev/input/event1, уже есть в constants.py
from screen_processor import ScreenProcessor
from config_manager import ConfigManager


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
    print("CMD:", cmd)
    return adb_cmd(cmd)


def main():
    cfg = ConfigManager()
    sp = ScreenProcessor(cfg)

    if not sp.check_adb():
        return

    print("=== TAP TESTER ===")
    print(f"EVENT_DEV: {EVENT_DEV}")
    print("Перед запуском включи в другой консоли:")
    print(f"  adb shell getevent -lt {EVENT_DEV}")
    print()

    while True:
        try:
            x = int(input("X (Enter для выхода): ") or "0")
            y = int(input("Y: "))
        except ValueError:
            print("Выход.")
            break

        print(f"→ Тап по ({x}, {y})")
        res = send_tap_like_mouse(sp.adb_command, x, y)
        print("Результат:", res)
        time.sleep(0.3)


if __name__ == "__main__":
    main()

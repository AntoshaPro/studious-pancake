# bot.py - координатор
from pathlib import Path

from config_manager import ConfigManager
from screen_processor import ScreenProcessor
from game_logic import GameLogic
from ui import UI
from ad_detector_2248 import EndGameAdDetector2248
from color_trainer import ColorTrainer
from input_controller import InputController
from end_game_handler import EndGameHandler
from game_runner import GameRunner
from board_printer import print_board

class Auto2248Bot:
    """
    Главный фасад бота 2248.

    Здесь собираются все компоненты:
    - конфиг и работа с файлами,
    - обработка экрана (скрины/кропы),
    - логика игры (поиск цепочек, оценка ходов),
    - контроллер ввода (тапы/свайпы),
    - обработчик экранов конца игры,
    - детектор рекламы/кнопки продолжения,
    - игровой раннер (основной цикл),
    - консольный UI.
    """

    def __init__(self):
        # Конфиг и настройки бота (JSON, пути, параметры)
        self.config_manager = ConfigManager()

        # Захват экрана и работа со скриншотами / ADB
        self.screen_processor = ScreenProcessor(self.config_manager)

        # Контроллер ввода (тапы/свайпы через ADB)
        self.input = InputController(self.screen_processor)

        # Логика игры: работает с доской, считает цепочки и оценку ходов
        self.game_logic = GameLogic(
            self.config_manager,
            self.screen_processor,
            self.input,
        )

        # Обучение цветам / шаблонам цифр
        self.color_trainer = ColorTrainer(
            self.config_manager,
            self.screen_processor,
        )

        # Обработчик экранов конца игры (win / lose / continue)
        self.end_handler = EndGameHandler(self.screen_processor)

        # Детектор кнопки рекламы / продолжения (по шаблону)
        self.ad_end_detector = EndGameAdDetector2248()
        if Path("end_button_template.png").exists():
            self.ad_end_detector.load_button_template("end_button_template.png")

        # Прокидываем детектор рекламы в логику, чтобы она могла его использовать
        self.game_logic.set_ad_detector(self.ad_end_detector)

        # Игровой раннер: крутит основной цикл игры, дергает GameLogic, Input, EndGameHandler
        self.game_runner = GameRunner(
            self.config_manager,
            self.screen_processor,
            self.game_logic,
            self.end_handler,
            self.input,
            self.ad_end_detector,
        )

        # Консольное меню поверх всего этого
        self.ui = UI(self)

    # ===== Публичные методы, которые дергает main/UI =====
    def save_state_and_logs(self):
        """Сохранить статистику и состояние перед выходом."""
        print("[STATE] Сохраняю статистику и логи...")
        # плохие ходы / конфиг
        self.config_manager.save_bad_moves()
        self.config_manager.save_config()
        # если у GameRunner есть статистика — дергаем её
        if hasattr(self.game_runner, "save_stats"):
            self.game_runner.save_stats()
        print("[STATE] Сохранение завершено.")
    
    def save_for_shutdown(self):
        """Save state specifically for shutdown process."""
        print("\n[SHUTDOWN] Сохраняю состояние перед завершением...")
        self.save_state_and_logs()
        print("[SHUTDOWN] Готово, выходим.")
    
    def show_menu(self):
        """Запуск консольного меню."""
        self.ui.show_menu()

    # Делегирующие методы для удобства

    def check_adb(self):
        """Проверить наличие подключённого устройства через ADB."""
        return self.screen_processor.check_adb()

    def take_screenshot(self, filename: str = "screen.png"):
        """Сделать скриншот экрана игры."""
        return self.screen_processor.take_screenshot(filename)

    @property
    def config(self):
        """Короткий доступ к текущему конфигу."""
        return self.config_manager.config

    @property
    def board(self):
        """Текущая доска, которую держит GameLogic."""
        return self.game_logic.board

    def run_auto_game(self, max_moves: int = 100):
        """
        Запустить автоматическую игру.

        Важно: тут уже вызывается не GameLogic напрямую, а GameRunner,
        который рулит:
        - скринами,
        - опросом GameLogic,
        - свайпами,
        - проверкой конца игры/рекламы.
        """
        return self.game_runner.run_auto_game(max_moves)

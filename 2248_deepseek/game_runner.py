# game_runner.py
import time
import constants as const
from constants import AD_CLOSE_POINTS, MOVES_DIR
from ad_detector_2248 import send_tap_like_mouse


class GameRunner:
    def __init__(
        self,
        config_manager,
        screen_processor,
        game_logic,
        end_handler,
        input_controller,
        ad_end_detector,
    ):
        self.config_manager = config_manager
        self.screen_processor = screen_processor
        self.game_logic = game_logic
        self.end_handler = end_handler
        self.input = input_controller
        self.ad_end_detector = ad_end_detector
        self.ad_detector = game_logic.ad_detector  # тот же объект

        self.config = config_manager.config
        self.show_board_each_move = False

    def run_auto_game(self, max_moves=100):
        print("\n" + "=" * 60)
        print("🤖 ЗАПУСК АВТОМАТИЧЕСКОЙ ИГРЫ 2248 С ОБУЧЕНИЕМ")
        print("=" * 60)

        if not self.config.get("calibrated", False):
            print("❌ Бот не готов к игре!")
            return

        for move in range(1, max_moves + 1):
            move_path = MOVES_DIR / f"move{move}.png"
            print(f"\n🎯 Ход #{move}/{max_moves}")

            # 1. Скриншот без рекламы-магии (как у тебя)
            self.screen_processor.take_screenshot(str(move_path))

            # 2. Обрезка клеток и распознавание
            self.screen_processor.crop_cells_from_screen(str(move_path))
            board, confidence_board = self.game_logic.recognize_board_with_confidence()
            if board is None:
                print("❌ Не удалось распознать доску")
                break

            # 3. Логика хода
            board_before = self.game_logic.get_board_hash()

            if self.game_logic.last_move_hash == board_before:
                self.game_logic.current_move_attempts += 1
                print(
                    f"⚠️ Повторная попытка того же хода ({self.game_logic.current_move_attempts}/2)"
                )
            else:
                self.game_logic.current_move_attempts = 1
                self.game_logic.last_move_hash = board_before

            if self.game_logic.current_move_attempts >= 2:
                print("🚫 Две неудачные попытки! Выбираю другой ход...")
                if self.game_logic.last_move_type:
                    self.game_logic.remember_bad_move(
                        {
                            "board_state": board_before,
                            "move_type": self.game_logic.last_move_type,
                            "direction": self.game_logic.last_move_direction,
                        }
                    )
                self.game_logic.current_move_attempts = 0

            # 4. УМНЫЙ поиск цепочки
            best_chain = self.game_logic.find_best_chain_smart(board_before)

            if best_chain:
                useful_cells, neighbor_pairs = (
                    self.game_logic.simulate_board_after_move(best_chain)
                )
                chain_score = self.game_logic.evaluate_chain_smart(best_chain)

                print(
                    f"🔗 Умная цепочка из {len(best_chain)} клеток (оценка: {chain_score})"
                )
                print(
                    f"   Прогноз: останется {useful_cells} полезных клеток, {neighbor_pairs} потенциальных пар"
                )

                self.game_logic.last_move_type = "chain"
                self.game_logic.last_move_direction = (
                    f"{best_chain[0][0]}_{best_chain[0][1]}_"
                    f"{best_chain[-1][0]}_{best_chain[-1][1]}"
                )

                if self.input.perform_chain_swipe_mt(
                    self.config, best_chain, self.game_logic.board, steps=1
                ):
                    print("✅ Ход выполнен (MT)")
                else:
                    print("❌ Ошибка выполнения хода (MT)")
                    break

            else:
                print("⚠️ Цепочки не найдены! Пробую короткий осмысленный ход...")

                candidate_pairs = []
                for r in range(const.ROWS):
                    for c in range(const.COLS):
                        if self.game_logic.board[r][c] <= 0:
                            continue
                        for dr, dc in [(0, 1), (1, 0), (-1, 0), (0, -1)]:
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < const.ROWS and 0 <= nc < const.COLS:
                                if self.game_logic.board[nr][nc] > 0:
                                    chain = [(r, c), (nr, nc)]
                                    candidate_pairs.append(chain)

                if not candidate_pairs:
                    print(
                        "⚠️ Вообще нет валидных ходов. Похоже, реклама или конец раунда."
                    )

                    state = self.end_handler.check_and_restart()
                    if state in ("win", "lose"):
                        self.game_logic.current_move_attempts = 0
                        self.game_logic.last_move_hash = None
                        # уже перезапустили игру – переходим к следующему ходу
                        continue

                    # 👉 ТУТ ЖМЁМ КНОПКУ РЕКЛАМЫ ЧЕРЕЗ ad_end_detector
                    if self.ad_end_detector:
                        print("▶️ Жму кнопку просмотра рекламы через ad_end_detector...")
                        try:
                            ok = self.ad_end_detector.tap_ad_button(
                                self.screen_processor.adb_command
                            )

                        except Exception as e:
                            print(f"❌ Ошибка при попытке нажать рекламу: {e}")
                            ok = False

                        if ok:
                            print("⏳ Жду окончания рекламы...")
                            time.sleep(15.0)  # подстрой под свою игру
                            print("▶️ Пытаюсь закрыть рекламу (крестик)...")
                            res_close = False
                            for cx, cy in AD_CLOSE_POINTS:
                                print(f"  → Тап по возможному крестику ({cx}, {cy})")
                                res_close = send_tap_like_mouse(
                                    self.screen_processor.adb_command,
                                    cx,
                                    cy,
                                )
                                time.sleep(1.0)
                            # если хоть один крестик сработал — продолжаем
                            if res_close:
                                time.sleep(2.0)
                                continue
                        else:
                            print(
                                "❌ Не удалось нажать кнопку рекламы, останавливаю бота."
                            )
                            break
                    else:
                        print(
                            "ℹ️ Детектор рекламы не настроен, просто останавливаю бота."
                        )
                        break

                # если candidate_pairs есть — обычный резервный ход
                best_pair = max(
                    candidate_pairs,
                    key=lambda ch: self.game_logic.evaluate_chain_smart(ch),
                )

                self.game_logic.last_move_type = "fallback_pair"
                self.game_logic.last_move_direction = (
                    f"{best_pair[0][0]}_{best_pair[0][1]}_"
                    f"{best_pair[1][0]}_{best_pair[1][1]}"
                )

                if self.input.perform_chain_swipe_mt(
                    self.config, best_pair, self.game_logic.board, steps=1
                ):
                    print("✅ Выполнен резервный короткий ход вместо рандома")
                else:
                    print("❌ Ошибка выполнения резервного хода")
                    break

            # двойной вызов как в оригинале у тебя
            state = self.end_handler.check_and_restart()
            state = self.end_handler.check_and_restart()
            if state in ("win", "lose"):
                self.game_logic.current_move_attempts = 0
                self.game_logic.last_move_hash = None
                continue

            if self.show_board_each_move:
                from board_printer import print_board

                print_board(self.game_logic.board, confidence_board)

            time.sleep(0.3)

        print("\n" + "=" * 60)
        print("🏁 АВТОМАТИЧЕСКАЯ ИГРА ЗАВЕРШЕНА!")
        print("=" * 60)

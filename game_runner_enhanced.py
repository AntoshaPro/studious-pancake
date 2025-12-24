"""
Enhanced GameRunner with episode-based learning, dynamic profile selection,
and event system integration for the 2248 bot project
"""
import time
import signal
import sys
from typing import Optional, Tuple
import constants as const
from constants import AD_CLOSE_POINTS, MOVES_DIR, GOOD_MOVE_MIN_SCORE, WAIT
from ad_detector_2248 import send_tap_like_mouse
from board_printer import print_board
from event_system import EventSystem, EventType
from learning_engine import LearningEngine, GameEpisode
from game_state_tracker import GameStateTracker


class EnhancedGameRunner:
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
        self.ad_detector = game_logic.ad_detector
        self.ad_end_detector = ad_end_detector
        self.ads_this_game = 0

        self.config = config_manager.config
        self.show_board_each_move = False
        self._stop_requested = False
        
        # Initialize new components
        self.event_system = EventSystem()
        self.learning_engine = LearningEngine()
        self.game_state_tracker = GameStateTracker()
        
        # Episode tracking
        self.current_episode_moves = []
        self.current_episode_boards = []
        self.current_episode_scores = []
        
        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully with event system integration."""
        print("\n[SHUTDOWN] Получен сигнал остановки (Ctrl+C), завершаю работу...")
        self.event_system.emit_simple(EventType.STOP_REQUESTED, 
                                   {'signal': signum, 'timestamp': time.time()})
        self._stop_requested = True
        self.save_stats()
        sys.exit(0)

    def save_stats(self):
        """Save game statistics before exit."""
        print("[STATS] Сохраняю статистику игры...")
        self.learning_engine.save_model()
        self.learning_engine.save_episodes()
        self.game_state_tracker.save_stats()
        self.event_system.save_history()
        print("[STATS] Статистика сохранена.")
        
    def update_order_stats(self, game_result: dict):
        """
        Update statistics for the current order profile in optimal_orders.json.
        This prepares the system for future optimization based on performance.
        """
        try:
            import json
            from constants import ORDERS_FILE
            
            if not ORDERS_FILE.exists():
                return
                
            data = json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
            
            # Get current order index from GameLogic if available
            current_index = getattr(self.game_logic, 'current_order_index', 0)
            
            # Initialize stats if not exists
            if "stats" not in data:
                data["stats"] = {}
                
            # Initialize current profile stats if not exists
            profile_key = str(current_index)
            if profile_key not in data["stats"]:
                data["stats"][profile_key] = {"games": 0, "total_score": 0.0}
            
            # Update stats
            data["stats"][profile_key]["games"] += 1
            data["stats"][profile_key]["total_score"] += game_result.get("score", 0)
            
            # Save back to file
            ORDERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            
        except Exception as e:
            print(f"[STATS] Ошибка обновления статистики: {e}")

    def _handle_advertisement(self) -> bool:
        """Handle advertisement display with event system integration."""
        print("▶️ Жму кнопку просмотра рекламы через ad_end_detector...")
        
        # Emit event for ad detection
        self.event_system.emit_simple(EventType.AD_DETECTED, 
                                   {'timestamp': time.time()})
        
        try:
            ok = self.ad_detector.tap_ad_button(
                self.screen_processor.adb_command
            )
        except Exception as e:
            print(f"❌ Ошибка при попытке нажать рекламу: {e}")
            ok = False

        if ok:
            print(f"⏳ Жду окончания рекламы {WAIT} секунд...")
            remaining = WAIT
            while remaining > 0 and not self._stop_requested:
                print(f"   Ожидание: {remaining} сек... ", end="\r")
                time.sleep(1)
                remaining -= 1
                if self._stop_requested:
                    break
            print("\n⏱ Ожидание рекламы завершено.")
            
            print("▶️ Пытаюсь закрыть рекламу (крестик)...")
            res_close = False
            for cx, cy in AD_CLOSE_POINTS:
                print(f"  → Тап по возможному крестику ({cx}, {cy})")
                res_close = send_tap_like_mouse(
                    self.screen_processor.adb_command,
                    cx,
                    cy,
                )
                time.sleep(0.05)
                if res_close:
                    break
            
            if res_close:
                time.sleep(0.05)
                
                # Emit event for ad handling
                self.event_system.emit_simple(EventType.AD_HANDLED, 
                                           {'success': True, 'timestamp': time.time()})
                return True
        else:
            print("❌ Не удалось нажать кнопку рекламы.")
        
        # Emit event for failed ad handling
        self.event_system.emit_simple(EventType.AD_HANDLED, 
                                   {'success': False, 'timestamp': time.time()})
        return False

    def _handle_no_valid_moves(self) -> bool:
        """Handle situation when no valid moves are available."""
        print("⚠️ Вообще нет валидных ходов. Похоже, реклама или конец раунда.")

        # Single check_and_restart call instead of double
        state = self.end_handler.check_and_restart()
        if state in ("win", "lose"):
            self.game_logic.current_move_attempts = 0
            self.game_logic.last_move_hash = None
            return True  # Continue game

        if self.ad_end_detector:
            success = self._handle_advertisement()
            if not success:
                print("❌ Не удалось обработать рекламу, останавливаю бота.")
                return False  # Stop game
        else:
            print("ℹ️ Детектор рекламы не настроен, просто останавливаю бота.")
            return False  # Stop game
        
        return True  # Continue game

    def _execute_fallback_move(self, board_before: int) -> bool:
        """Execute fallback move when no chains are found."""
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
            return self._handle_no_valid_moves()

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
            pair_score = self.game_logic.evaluate_chain_smart(best_pair)
            if pair_score >= GOOD_MOVE_MIN_SCORE:
                self.game_logic.remember_good_move(
                    board_before,
                    move_type="fallback_pair",
                    direction=self.game_logic.last_move_direction,
                    score=pair_score,
                )
            else:
                print(
                    f"ℹ️ Резервный ход с оценкой {pair_score:.1f} не сохраняю как хороший."
                )
            self.game_logic.current_move_attempts = 0
            self.game_logic.last_move_hash = None
            return True
        else:
            print("❌ Ошибка выполнения резервного хода")
            return False

    def run_auto_game(self, max_moves=100):
        print("\n" + "=" * 60)
        print("🤖 ЗАПУСК АВТОМАТИЧЕСКОЙ ИГРЫ 2248 С ОБУЧЕНИЕМ")
        print("=" * 60)

        if not self.config.get("calibrated", False):
            print("❌ Бот не готов к игре!")
            return

        # Start tracking the game
        initial_board = [row[:] for row in self.game_logic.board]
        profile_idx = getattr(self.game_logic, 'current_order_index', 0)
        self.game_state_tracker.start_new_game(initial_board, profile_idx)
        
        # Emit game start event
        self.event_system.emit_simple(EventType.GAME_START, 
                                   {'profile_idx': profile_idx, 'timestamp': time.time()})

        # Initialize episode data
        self.current_episode_moves = []
        self.current_episode_boards = [initial_board]
        self.current_episode_scores = [self.game_state_tracker._calculate_score_from_board(initial_board)]

        for move in range(1, max_moves + 1):
            if self._stop_requested:
                print("\n[SHUTDOWN] Остановлено пользователем.")
                break
                
            move_path = MOVES_DIR / f"move{move}.png"
            print(f"\n🎯 Ход #{move}/{max_moves}")

            # 1. Скриншот
            self.screen_processor.take_screenshot(str(move_path))

            # 2. Обрезка клеток и распознавание
            self.screen_processor.crop_cells_from_screen(str(move_path))
            board, confidence_board = self.game_logic.recognize_board_with_confidence()
            if board is None:
                print("❌ Не удалось распознать доску")
                break

            if self.game_logic.show_board_each_move:
                print_board(board, confidence_board)
            self.game_logic.on_new_board()
            
            # Update game state tracker
            self.game_state_tracker.update_game_state(board)
            
            # Emit board recognized event
            self.event_system.emit_simple(EventType.BOARD_RECOGNIZED, 
                                       {'board': board, 'move': move, 'timestamp': time.time()})

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
            # Dynamic profile selection based on current board state
            try:
                import json
                from constants import ORDERS_FILE
                if ORDERS_FILE.exists():
                    data = json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
                    orders = data.get("orders", [])
                    if orders:
                        # Adapt strategy based on current board and historical performance
                        new_profile = self.learning_engine.adapt_strategy(board, orders)
                        if new_profile != self.game_logic.optimal_lengths:
                            self.game_logic.optimal_lengths = new_profile
                            # Emit strategy change event
                            self.event_system.emit_simple(EventType.STRATEGY_CHANGED, 
                                                       {'new_profile': new_profile, 'timestamp': time.time()})
            except Exception as e:
                print(f"[STRATEGY] Error adapting strategy: {e}")

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
                
                # Emit chain found event
                self.event_system.emit_simple(EventType.CHAIN_FOUND, 
                                           {'chain': best_chain, 'score': chain_score, 'timestamp': time.time()})

                self.game_logic.last_move_type = "chain"
                self.game_logic.last_move_direction = (
                    f"{best_chain[0][0]}_{best_chain[0][1]}_"
                    f"{best_chain[-1][0]}_{best_chain[-1][1]}"
                )

                if self.input.perform_chain_swipe_mt(
                    self.config, best_chain, self.game_logic.board, steps=1
                ):
                    print("✅ Ход выполнен (MT)")
                    
                    # Emit move executed event
                    self.event_system.emit_simple(EventType.MOVE_EXECUTED, 
                                               {'chain': best_chain, 'timestamp': time.time()})
                    
                    # Update episode data
                    self.current_episode_moves.append(best_chain)
                    self.current_episode_boards.append([row[:] for row in self.game_logic.board])
                    current_score = self.game_state_tracker._calculate_score_from_board(self.game_logic.board)
                    self.current_episode_scores.append(current_score)
                    
                    # сохраняем только реально хорошие ходы
                    if chain_score >= GOOD_MOVE_MIN_SCORE:
                        self.game_logic.remember_good_move(
                            board_before,
                            move_type="chain",
                            direction=self.game_logic.last_move_direction,
                            score=chain_score,
                        )
                    else:
                        print(
                            f"ℹ️ Ход с оценкой {chain_score:.1f} не сохраняю как хороший."
                        )
                    self.game_logic.current_move_attempts = 0
                    self.game_logic.last_move_hash = None
                else:
                    print("❌ Ошибка выполнения хода (MT)")
                    break

            else:
                print("⚠️ Цепочки не найдены! Пробую короткий осмысленный ход...")
                success = self._execute_fallback_move(board_before)
                if not success:
                    break

            # Single check_and_restart call instead of double
            state = self.end_handler.check_and_restart()
            if state in ("win", "lose"):
                # End the current game session
                success = state == "win"
                session = self.game_state_tracker.end_current_session(state, success)
                
                # Create episode for learning
                episode = GameEpisode(
                    board_states=self.current_episode_boards,
                    moves=self.current_episode_moves,
                    scores=self.current_episode_scores,
                    final_score=session.final_state.score,
                    max_tile=session.final_state.max_tile,
                    duration=session.end_time - session.start_time,
                    timestamp=session.start_time,
                    success=success
                )
                episode.profile_used = session.profile_used  # Add profile to episode
                
                # Record the episode
                self.learning_engine.record_episode(episode)
                
                # Update feature weights based on the episode
                self.learning_engine.update_feature_weights(episode)
                
                # Emit game end event
                self.event_system.emit_simple(EventType.GAME_END, 
                                           {'state': state, 'score': session.final_state.score, 'timestamp': time.time()})
                
                self.game_logic.current_move_attempts = 0
                self.game_logic.last_move_hash = None
                continue

            time.sleep(0.01)

        # If we've reached max_moves without ending naturally, end the session
        if self.game_state_tracker.current_session is not None:
            session = self.game_state_tracker.end_current_session("max_moves_reached", False)
            
            # Create episode for learning (even if not completed)
            episode = GameEpisode(
                board_states=self.current_episode_boards,
                moves=self.current_episode_moves,
                scores=self.current_episode_scores,
                final_score=session.final_state.score,
                max_tile=session.final_state.max_tile,
                duration=session.end_time - session.start_time,
                timestamp=session.start_time,
                success=False
            )
            episode.profile_used = session.profile_used  # Add profile to episode
            
            # Record the episode
            self.learning_engine.record_episode(episode)
            
            # Update feature weights based on the episode
            self.learning_engine.update_feature_weights(episode)
            
            # Emit game end event
            self.event_system.emit_simple(EventType.GAME_END, 
                                       {'state': 'max_moves', 'score': session.final_state.score, 'timestamp': time.time()})

        print("\n" + "=" * 60)
        print("🏁 АВТОМАТИЧЕСКАЯ ИГРА ЗАВЕРШЕНА!")
        print("=" * 60)